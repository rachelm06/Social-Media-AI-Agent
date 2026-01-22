"""
Database client for SQLite operations.
"""
import sqlite3
import json
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime


class DatabaseClient:
    """Client for SQLite database operations."""
    
    def __init__(self, db_path: str = "database/biterate.db"):
        """
        Initialize database client.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database with schema if it doesn't exist."""
        schema_path = Path("database/schema.sql")
        if schema_path.exists():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
                cursor.executescript(schema_sql)
            conn.commit()
            conn.close()
    
    def _get_connection(self):
        """Get database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        return conn
    
    def save_review(self, review_id: str, notion_page_id: str, restaurant: str, 
                   rating: Optional[float] = None, review: Optional[str] = None,
                   cuisine: Optional[str] = None, location: Optional[str] = None) -> bool:
        """Save or update a review."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO reviews 
                (id, notion_page_id, restaurant, rating, review, cuisine, location, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (review_id, notion_page_id, restaurant, rating, review, cuisine, location))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving review: {e}")
            return False
        finally:
            conn.close()
    
    def save_post(self, content: str, hashtags: List[str], tone: str,
                 restaurant_mentioned: Optional[str] = None,
                 rating_mentioned: Optional[float] = None,
                 image_url: Optional[str] = None,
                 status: str = "pending") -> Optional[int]:
        """Save a generated post and return its ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO posts 
                (content, hashtags, tone, restaurant_mentioned, rating_mentioned, image_url, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (content, json.dumps(hashtags), tone, restaurant_mentioned, 
                  rating_mentioned, image_url, status))
            post_id = cursor.lastrowid
            conn.commit()
            return post_id
        except Exception as e:
            print(f"Error saving post: {e}")
            return None
        finally:
            conn.close()
    
    def update_post_status(self, post_id: int, status: str, 
                          mastodon_post_id: Optional[str] = None,
                          mastodon_url: Optional[str] = None):
        """Update post status and Mastodon info."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            if status == "published":
                cursor.execute("""
                    UPDATE posts 
                    SET status = ?, mastodon_post_id = ?, mastodon_url = ?, published_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (status, mastodon_post_id, mastodon_url, post_id))
            else:
                cursor.execute("""
                    UPDATE posts 
                    SET status = ?
                    WHERE id = ?
                """, (status, post_id))
            conn.commit()
        except Exception as e:
            print(f"Error updating post status: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
    
    def save_approval(self, post_id: int, decision: str, rejection_reason: Optional[str] = None):
        """Save approval decision."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO approvals (post_id, decision, rejection_reason)
                VALUES (?, ?, ?)
            """, (post_id, decision, rejection_reason))
            conn.commit()
        except Exception as e:
            print(f"Error saving approval: {e}")
        finally:
            conn.close()
    
    def save_feedback(self, post_id: Optional[int], feedback_type: str, feedback_text: str):
        """Save feedback for learning."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO feedback (post_id, feedback_type, feedback_text)
                VALUES (?, ?, ?)
            """, (post_id, feedback_type, feedback_text))
            conn.commit()
        except Exception as e:
            print(f"Error saving feedback: {e}")
        finally:
            conn.close()
    
    def get_recent_posts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent posts."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT * FROM recent_posts LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error getting recent posts: {e}")
            return []
        finally:
            conn.close()
