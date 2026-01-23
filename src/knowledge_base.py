"""
Knowledge base management: sync Notion content to vector database.
"""
import yaml
from typing import List, Dict, Any, Optional
from pathlib import Path

from src.notion_client import NotionClient
from src.chunking import chunk_document
from src.rag_client import RAGClient


class KnowledgeBase:
    """Manages syncing Notion content to vector database."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize knowledge base manager.
        
        Args:
            config_path: Path to configuration YAML file
        """
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.notion_client = NotionClient()
        self.rag_client = RAGClient()
        
        # Get chunking config
        chunking_config = self.config.get("chunking", {})
        self.chunking_strategy = chunking_config.get("strategy", "markdown_header")
        self.chunk_size = chunking_config.get("chunk_size", 500)
        self.chunk_overlap = chunking_config.get("chunk_overlap", 50)
        self.sentences_per_chunk = chunking_config.get("sentences_per_chunk", 3)
    
    def sync_notion_to_kb(self, force: bool = False) -> Dict[str, Any]:
        """
        Sync all Notion pages to knowledge base.
        
        Args:
            force: If True, re-sync even if already synced
            
        Returns:
            Dictionary with sync statistics
        """
        page_ids = self.config.get("notion", {}).get("page_ids", [])
        database_ids = self.config.get("notion", {}).get("database_ids", [])
        
        total_chunks = 0
        pages_synced = 0
        
        # Sync pages
        for page_id in page_ids:
            try:
                content = self.notion_client.get_page_content(page_id)
                if content:
                    chunks = self._process_and_store_content(
                        content=content,
                        source_id=page_id,
                        source_type="notion_page"
                    )
                    total_chunks += len(chunks)
                    pages_synced += 1
                    print(f"✓ Synced page {page_id}: {len(chunks)} chunks")
            except Exception as e:
                print(f"⚠️ Error syncing page {page_id}: {e}")
        
        # Sync databases (if any)
        for db_id in database_ids:
            try:
                entries = self.notion_client.get_database_entries(db_id, max_results=100)
                for entry in entries:
                    entry_id = entry.get("id", "")
                    # Try to get page content if it's a page
                    try:
                        content = self.notion_client.get_page_content(entry_id)
                        if content:
                            chunks = self._process_and_store_content(
                                content=content,
                                source_id=entry_id,
                                source_type="notion_database_entry"
                            )
                            total_chunks += len(chunks)
                    except Exception:
                        pass  # Skip if not a page
                print(f"✓ Synced database {db_id}")
            except Exception as e:
                print(f"⚠️ Error syncing database {db_id}: {e}")
        
        return {
            "pages_synced": pages_synced,
            "total_chunks": total_chunks,
            "status": "success"
        }
    
    def _process_and_store_content(
        self,
        content: str,
        source_id: str,
        source_type: str
    ) -> List[Dict[str, Any]]:
        """
        Process content (chunk, embed, store) and return chunks.
        
        Args:
            content: Content to process
            source_id: Source identifier
            source_type: Type of source
            
        Returns:
            List of chunk dictionaries
        """
        # Chunk the content
        chunks = chunk_document(
            content=content,
            source_id=source_id,
            strategy=self.chunking_strategy,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            sentences_per_chunk=self.sentences_per_chunk
        )
        
        # Generate embeddings in batch
        texts = [chunk["content"] for chunk in chunks]
        embeddings = self.rag_client.generate_embeddings_batch(texts)
        
        # Store each chunk
        for chunk, embedding in zip(chunks, embeddings):
            self.rag_client.save_embedding(
                source_type=source_type,
                content=chunk["content"],
                embedding=embedding,
                source_id=source_id,
                metadata=chunk.get("metadata", {})
            )
        
        return chunks
    
    def is_empty(self) -> bool:
        """Check if knowledge base is empty."""
        conn = self.rag_client._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM embeddings_meta")
        count = cursor.fetchone()["count"]
        conn.close()
        return count == 0
