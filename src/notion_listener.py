"""
Notion API listener for detecting changes and auto-triggering posts.
"""
import os
import yaml
import time
import sqlite3
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from src.notion_client import NotionClient
from src.knowledge_base import KnowledgeBase
from src.agent import BiteRateAgent


class NotionListener:
    """Listens for Notion page changes and triggers post generation."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize Notion listener.
        
        Args:
            config_path: Path to configuration YAML file
        """
        load_dotenv()
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.notion_client = NotionClient()
        self.knowledge_base = KnowledgeBase(config_path)
        self.agent = BiteRateAgent(config_path)
        
        listener_config = self.config.get("notion_listener", {})
        self.enabled = listener_config.get("enabled", False)
        self.poll_interval = listener_config.get("poll_interval", 300)  # 5 minutes default
        self.auto_post = listener_config.get("auto_post", True)
        
        # Initialize state database
        self.state_db_path = "database/notion_listener_state.db"
        self._init_state_db()
    
    def _init_state_db(self):
        """Initialize state database to track last check times."""
        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_states (
                page_id TEXT PRIMARY KEY,
                last_edited_time TEXT,
                last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def _get_last_edited_time(self, page_id: str) -> Optional[str]:
        """Get the last edited time for a page from Notion."""
        try:
            page = self.notion_client.client.pages.retrieve(page_id)
            last_edited = page.get("last_edited_time")
            return last_edited
        except Exception as e:
            print(f"Error fetching last_edited_time for {page_id}: {e}")
            return None
    
    def _get_stored_state(self, page_id: str) -> Optional[str]:
        """Get stored last_edited_time from state database."""
        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT last_edited_time FROM page_states WHERE page_id = ?", (page_id,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    def _update_stored_state(self, page_id: str, last_edited_time: str):
        """Update stored state for a page."""
        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO page_states (page_id, last_edited_time, last_checked)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (page_id, last_edited_time))
        conn.commit()
        conn.close()
    
    def _check_page_changes(self) -> list[str]:
        """
        Check for changed pages and return list of changed page IDs.
        
        Returns:
            List of page IDs that have changed
        """
        page_ids = self.config.get("notion", {}).get("page_ids", [])
        changed_pages = []
        
        for page_id in page_ids:
            try:
                current_edited_time = self._get_last_edited_time(page_id)
                if not current_edited_time:
                    continue
                
                stored_edited_time = self._get_stored_state(page_id)
                
                if stored_edited_time is None:
                    # First time checking this page - store and skip
                    self._update_stored_state(page_id, current_edited_time)
                    print(f"📝 Initialized tracking for page {page_id}")
                elif current_edited_time != stored_edited_time:
                    # Page has changed
                    changed_pages.append(page_id)
                    self._update_stored_state(page_id, current_edited_time)
                    print(f"🔄 Detected change in page {page_id}")
            except Exception as e:
                print(f"⚠️ Error checking page {page_id}: {e}")
        
        return changed_pages
    
    def _handle_page_change(self, page_id: str):
        """Handle a detected page change."""
        print(f"\n📝 Processing change in page {page_id}...")
        
        try:
            # Sync updated content to knowledge base
            print("  → Syncing updated content to knowledge base...")
            # Note: We'll need to clear old chunks for this page and re-add
            # For now, just re-sync the entire knowledge base
            self.knowledge_base.sync_notion_to_kb(force=True)
            print("  ✓ Knowledge base updated")
            
            # Trigger post generation if auto_post is enabled
            if self.auto_post:
                print("  → Generating and posting new content...")
                result = self.agent.run()
                if result:
                    print("  ✓ Post generated and published")
                else:
                    print("  ⚠️ Post generation failed")
            else:
                print("  → Auto-post disabled, skipping post generation")
        except Exception as e:
            print(f"  ❌ Error handling page change: {e}")
    
    def start(self):
        """Start the listener loop."""
        if not self.enabled:
            print("Notion listener is disabled in config.yaml")
            return
        
        print(f"🔔 Starting Notion listener (polling every {self.poll_interval} seconds)...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                changed_pages = self._check_page_changes()
                
                if changed_pages:
                    for page_id in changed_pages:
                        self._handle_page_change(page_id)
                
                # Wait before next check
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n\n👋 Notion listener stopped")
        except Exception as e:
            print(f"\n❌ Error in listener loop: {e}")


if __name__ == "__main__":
    listener = NotionListener()
    listener.start()
