"""
RAG Client for vector database, embeddings, and hybrid search.
"""
import os
import json
import sqlite3
import struct
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None

try:
    from fastembed import TextEmbedding
except ImportError:
    TextEmbedding = None


class RAGClient:
    """Client for RAG operations: embeddings, vector storage, and hybrid search."""
    
    def __init__(self, db_path: str = "database/rag.db"):
        """
        Initialize RAG client with vector database.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        if TextEmbedding is None:
            raise ImportError("fastembed is required. Install with: pip install fastembed")
        
        os.environ.setdefault("HF_HUB_DISABLE_IMPLICIT_TOKEN", "1")
        self.embedding_model = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with sqlite-vec and FTS5."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Load sqlite-vec extension if available
        if sqlite_vec:
            try:
                conn.enable_load_extension(True)
                sqlite_vec.load(conn)
                conn.enable_load_extension(False)
            except Exception as e:
                print(f"Warning: Could not load sqlite-vec extension: {e}")
                print("Falling back to basic vector storage")
        
        cursor = conn.cursor()
        
        # Metadata table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS embeddings_meta (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_type TEXT NOT NULL,
                source_id TEXT,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Vector table using sqlite-vec (384 dimensions for MiniLM-L6-v2)
        if sqlite_vec:
            try:
                cursor.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS vec_embeddings USING vec0(
                        embedding float[384] distance_metric=cosine
                    )
                """)
            except sqlite3.OperationalError as e:
                if "already exists" not in str(e).lower():
                    print(f"Warning: Could not create vec_embeddings table: {e}")
        
        # FTS5 virtual table for BM25 keyword search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS embeddings_fts USING fts5(
                content,
                source_type,
                source_id,
                content='embeddings_meta',
                content_rowid='id'
            )
        """)
        
        # Triggers to keep FTS5 in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS embeddings_ai AFTER INSERT ON embeddings_meta BEGIN
                INSERT INTO embeddings_fts(rowid, content, source_type, source_id)
                VALUES (new.id, new.content, new.source_type, new.source_id);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS embeddings_ad AFTER DELETE ON embeddings_meta BEGIN
                INSERT INTO embeddings_fts(embeddings_fts, rowid, content, source_type, source_id)
                VALUES ('delete', old.id, old.content, old.source_type, old.source_id);
            END
        """)
        
        conn.commit()
        conn.close()
    
    def _get_connection(self):
        """Get database connection with sqlite-vec loaded."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        if sqlite_vec:
            try:
                conn.enable_load_extension(True)
                sqlite_vec.load(conn)
                conn.enable_load_extension(False)
            except Exception:
                pass  # Extension already loaded or not available
        
        return conn
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate a 384-dimensional embedding for the given text."""
        if not text.strip():
            return [0.0] * 384
        embeddings = list(self.embedding_model.embed([text]))
        return embeddings[0].tolist()
    
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in a batch."""
        if not texts:
            return []
        texts = [t for t in texts if t.strip()]
        if not texts:
            return [[0.0] * 384] * len(texts)
        embeddings = list(self.embedding_model.embed(texts))
        return [emb.tolist() for emb in embeddings]
    
    def serialize_embedding(self, embedding: List[float]) -> bytes:
        """Serialize embedding to binary format for sqlite-vec."""
        return struct.pack(f'{len(embedding)}f', *embedding)
    
    def save_embedding(
        self,
        source_type: str,
        content: str,
        embedding: List[float],
        source_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Save an embedding to the database.
        
        Returns:
            Row ID of the inserted embedding
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Insert metadata (FTS5 index updated automatically via trigger)
        cursor.execute("""
            INSERT INTO embeddings_meta (source_type, source_id, content, metadata, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            source_type,
            source_id,
            content,
            json.dumps(metadata) if metadata else None,
            datetime.now().isoformat(),
        ))
        rowid = cursor.lastrowid
        
        # Insert vector with matching rowid (if sqlite-vec is available)
        if sqlite_vec and len(embedding) == 384:
            try:
                cursor.execute("""
                    INSERT INTO vec_embeddings (rowid, embedding)
                    VALUES (?, ?)
                """, (rowid, self.serialize_embedding(embedding)))
            except Exception as e:
                print(f"Warning: Could not insert vector: {e}")
        
        conn.commit()
        conn.close()
        return rowid
    
    def bm25_search(self, query: str, limit: int = 100) -> Dict[int, float]:
        """
        Search using BM25 ranking via FTS5.
        
        Returns dict mapping embedding_id to raw BM25 score.
        Note: FTS5 BM25 scores are NEGATIVE (more negative = better match).
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Escape special FTS5 characters
        safe_query = query.replace('"', '""')
        
        try:
            cursor.execute("""
                SELECT rowid, bm25(embeddings_fts) as score
                FROM embeddings_fts
                WHERE embeddings_fts MATCH ?
                LIMIT ?
            """, (safe_query, limit))
            
            return {row[0]: row[1] for row in cursor.fetchall()}
        except sqlite3.OperationalError:
            # No matches or invalid query
            return {}
        finally:
            conn.close()
    
    def semantic_search(self, query_embedding: List[float], limit: int = 100) -> Dict[int, float]:
        """
        Search using sqlite-vec's native cosine distance.
        
        Returns dict mapping rowid to cosine distance.
        Note: cosine distance is in [0, 2] where 0 = identical, 2 = opposite.
        """
        if not sqlite_vec or len(query_embedding) != 384:
            return {}
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT rowid, distance
                FROM vec_embeddings
                WHERE embedding MATCH ?
                  AND k = ?
                ORDER BY distance
            """, (self.serialize_embedding(query_embedding), limit))
            
            return {row[0]: row[1] for row in cursor.fetchall()}
        except Exception as e:
            print(f"Warning: Semantic search failed: {e}")
            return {}
        finally:
            conn.close()
    
    def normalize_bm25_scores(self, bm25_scores: Dict[int, float]) -> Dict[int, float]:
        """Normalize BM25 scores to [0, 1] range."""
        if not bm25_scores:
            return {}
        
        scores = list(bm25_scores.values())
        min_score = min(scores)  # Most negative = best
        max_score = max(scores)  # Least negative = worst
        
        if min_score == max_score:
            return {id: 1.0 for id in bm25_scores}
        
        score_range = max_score - min_score
        return {
            id: (max_score - score) / score_range
            for id, score in bm25_scores.items()
        }
    
    def normalize_distances(self, distances: Dict[int, float]) -> Dict[int, float]:
        """Normalize cosine distances to similarity scores in [0, 1]."""
        if not distances:
            return {}
        
        # Convert distances to similarities
        similarities = {id: 1 - (dist / 2) for id, dist in distances.items()}
        
        # Normalize to [0, 1] range
        min_sim = min(similarities.values())
        max_sim = max(similarities.values())
        
        if min_sim == max_sim:
            return {id: 1.0 for id in similarities}
        
        sim_range = max_sim - min_sim
        return {
            id: (sim - min_sim) / sim_range
            for id, sim in similarities.items()
        }
    
    def get_metadata_by_ids(self, ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """Retrieve metadata for given IDs from embeddings_meta table."""
        if not ids:
            return {}
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        placeholders = ",".join("?" * len(ids))
        cursor.execute(f"""
            SELECT id, source_type, source_id, content, metadata
            FROM embeddings_meta
            WHERE id IN ({placeholders})
        """, ids)
        
        results = {}
        for row in cursor.fetchall():
            results[row[0]] = {
                "source_type": row[1],
                "source_id": row[2],
                "content": row[3],
                "metadata": json.loads(row[4]) if row[4] else {},
            }
        
        conn.close()
        return results
    
    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        keyword_weight: float = 0.5,
        semantic_weight: float = 0.5,
        top_k: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining BM25 and sqlite-vec cosine similarity.
        
        Formula: final_score = keyword_weight * bm25 + semantic_weight * cosine_sim
        """
        # Step 1: Get BM25 scores from FTS5
        bm25_raw = self.bm25_search(query)
        bm25_normalized = self.normalize_bm25_scores(bm25_raw)
        
        # Step 2: Get semantic distances from sqlite-vec
        semantic_raw = self.semantic_search(query_embedding, limit=100)
        semantic_normalized = self.normalize_distances(semantic_raw)
        
        # Step 3: Get all unique IDs from both searches
        all_ids = set(bm25_normalized.keys()) | set(semantic_normalized.keys())
        
        if not all_ids:
            return []
        
        # Step 4: Get metadata for all candidates
        metadata = self.get_metadata_by_ids(list(all_ids))
        
        # Step 5: Compute combined scores
        scored_results = []
        
        for id in all_ids:
            # BM25 score (0 if no keyword match)
            bm25_score = bm25_normalized.get(id, 0.0)
            
            # Semantic score (0 if not in top semantic results)
            semantic_score = semantic_normalized.get(id, 0.0)
            
            # Combined score
            final_score = (keyword_weight * bm25_score) + (semantic_weight * semantic_score)
            
            meta = metadata.get(id, {})
            scored_results.append({
                "id": id,
                "content": meta.get("content", ""),
                "source_type": meta.get("source_type", ""),
                "source_id": meta.get("source_id", ""),
                "metadata": meta.get("metadata", {}),
                "bm25_score": bm25_score,
                "semantic_score": semantic_score,
                "final_score": final_score,
            })
        
        # Sort by final score (descending)
        scored_results.sort(key=lambda x: x["final_score"], reverse=True)
        
        return scored_results[:top_k]
    
    def retrieve_context(self, query: str, top_k: int = 10) -> tuple[str, List[Dict[str, Any]]]:
        """
        High-level function to retrieve and format context for RAG.
        
        Returns:
            Tuple of (formatted_context_string, results_list)
        """
        query_embedding = self.generate_embedding(query)
        results = self.hybrid_search(query, query_embedding, top_k=top_k)
        
        # Format context for prompt
        context_parts = []
        for i, result in enumerate(results, 1):
            header = f"[{i}. {result['source_type']}] (score: {result['final_score']:.2f})"
            content = result["content"]
            entry = f"{header}\n{content}\n"
            context_parts.append(entry)
        
        formatted = "\n".join(context_parts) if context_parts else "No relevant context found."
        return formatted, results
