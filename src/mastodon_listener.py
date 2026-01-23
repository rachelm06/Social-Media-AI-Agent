"""
Mastodon listener for monitoring comments and auto-replying.
"""
import os
import yaml
import time
import sqlite3
from typing import Dict, Any, Optional, List
from datetime import datetime
from dotenv import load_dotenv

from src.mastodon_client import MastodonClient
from src.llm_client import LLMClient
from src.rag_client import RAGClient
from src.telegram_client import TelegramClient


class MastodonListener:
    """Listens for Mastodon comments and generates replies using RAG."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize Mastodon listener.
        
        Args:
            config_path: Path to configuration YAML file
        """
        load_dotenv()
        
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.mastodon_client = MastodonClient(
            visibility=self.config.get("mastodon", {}).get("visibility", "public")
        )
        self.llm_client = LLMClient(
            model=self.config.get("llm", {}).get("model", "z-ai/glm-4.5-air:free"),
            temperature=self.config.get("llm", {}).get("temperature", 0.7),
            provider=self.config.get("llm", {}).get("provider", "openrouter"),
            max_tokens=self.config.get("llm", {}).get("max_tokens", 500)
        )
        
        # Initialize RAG client
        try:
            self.rag_client = RAGClient()
        except Exception as e:
            print(f"⚠️ RAG client not initialized: {e}")
            self.rag_client = None
        
        # Initialize Telegram client if enabled
        telegram_enabled = self.config.get("telegram", {}).get("enabled", False)
        self.telegram_client = None
        if telegram_enabled:
            try:
                self.telegram_client = TelegramClient()
            except ValueError:
                pass  # Telegram not configured
        
        listener_config = self.config.get("mastodon_listener", {})
        self.enabled = listener_config.get("enabled", False)
        self.poll_interval = listener_config.get("poll_interval", 60)  # 1 minute default
        self.auto_reply = listener_config.get("auto_reply", True)
        
        # Get current user ID
        try:
            self.current_user_id = self.mastodon_client.client.me()["id"]
        except Exception as e:
            print(f"⚠️ Could not get current user ID: {e}")
            self.current_user_id = None
        
        # Initialize state database
        self.state_db_path = "database/mastodon_listener_state.db"
        self._init_state_db()
    
    def _init_state_db(self):
        """Initialize state database to track replied-to notifications."""
        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS replied_notifications (
                notification_id TEXT PRIMARY KEY,
                replied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def _is_already_replied(self, notification_id: str) -> bool:
        """Check if we've already replied to this notification."""
        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM replied_notifications WHERE notification_id = ?", (notification_id,))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    def _mark_as_replied(self, notification_id: str):
        """Mark a notification as replied to."""
        conn = sqlite3.connect(self.state_db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO replied_notifications (notification_id) VALUES (?)", (notification_id,))
        conn.commit()
        conn.close()
    
    def _get_notifications(self) -> List[Dict[str, Any]]:
        """Get recent notifications from Mastodon."""
        try:
            notifications = self.mastodon_client.client.notifications(limit=20)
            return notifications
        except Exception as e:
            print(f"⚠️ Error fetching notifications: {e}")
            return []
    
    def _filter_relevant_notifications(self, notifications: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter notifications to only include mentions/replies to our posts.
        
        Returns:
            List of relevant notifications
        """
        relevant = []
        
        for notif in notifications:
            notif_type = notif.get("type")
            notif_id = str(notif.get("id", ""))
            
            # Only process mentions and replies
            if notif_type not in ["mention", "reply"]:
                continue
            
            # Skip if already replied
            if self._is_already_replied(notif_id):
                continue
            
            # Check if it's a reply to one of our posts
            status = notif.get("status")
            if status:
                in_reply_to_id = status.get("in_reply_to_id")
                if in_reply_to_id:
                    # Check if the parent post is ours
                    try:
                        parent_status = self.mastodon_client.client.status(in_reply_to_id)
                        if parent_status.get("account", {}).get("id") == self.current_user_id:
                            relevant.append(notif)
                    except Exception:
                        pass  # Parent post might not exist anymore
            
            # Also include direct mentions
            elif notif_type == "mention":
                relevant.append(notif)
        
        return relevant
    
    def _generate_reply(self, original_post: str, comment: str) -> str:
        """
        Generate a reply using RAG context.
        
        Args:
            original_post: The original post content
            comment: The comment/reply content
            
        Returns:
            Generated reply text
        """
        # Retrieve relevant context using RAG
        rag_context = ""
        if self.rag_client:
            query = comment[:100]  # Use comment as query
            rag_context, _ = self.rag_client.retrieve_context(query, top_k=3)
        
        # Create prompt for reply generation
        prompt = f"""You are a social media manager for BiteRate, a food review company. Generate a friendly, helpful reply to a comment on your post.

Original Post:
{original_post}

Comment to Reply To:
{comment}"""

        if rag_context:
            prompt += f"""

Relevant Context from Knowledge Base:
{rag_context}"""

        prompt += """

Requirements:
- Be friendly and conversational
- Address the comment directly
- Keep it concise (under 200 characters)
- Sound authentic and human
- Do NOT include hashtags

Generate the reply now:"""

        try:
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful social media manager for BiteRate. Generate friendly, concise replies to comments."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.llm_client.temperature,
                max_tokens=200
            )
            
            reply = response.choices[0].message.content.strip()
            return reply
        except Exception as e:
            print(f"Error generating reply: {e}")
            return None
    
    def _handle_notification(self, notification: Dict[str, Any]):
        """Handle a notification by generating and posting a reply."""
        notif_id = str(notification.get("id", ""))
        status = notification.get("status", {})
        comment_content = status.get("content", "")
        
        # Extract original post
        in_reply_to_id = status.get("in_reply_to_id")
        original_post_content = ""
        if in_reply_to_id:
            try:
                original_status = self.mastodon_client.client.status(in_reply_to_id)
                original_post_content = original_status.get("content", "")
            except Exception:
                pass
        
        print(f"\n💬 Processing notification {notif_id}...")
        print(f"   Comment: {comment_content[:100]}...")
        
        # Generate reply
        reply = self._generate_reply(original_post_content, comment_content)
        if not reply:
            print("   ⚠️ Failed to generate reply")
            return
        
        print(f"   Generated reply: {reply[:100]}...")
        
        # Send for approval if Telegram is enabled
        if self.telegram_client and self.auto_reply:
            decision, rejection_reason = self.telegram_client.send_for_approval_sync(
                f"Reply to comment:\n\n{comment_content[:200]}\n\nReply:\n{reply}"
            )
            
            if decision == "reject":
                print(f"   ❌ Reply rejected: {rejection_reason}")
                return
            elif decision != "approve":
                print(f"   ⚠️ Unknown decision: {decision}")
                return
        
        # Post reply
        if self.auto_reply:
            try:
                # Use the reply method from mastodon_client
                result = self.mastodon_client.reply(
                    post_id=str(status.get("id")),
                    content=reply,
                    dry_run=False
                )
                if result and result.get("status") != "error":
                    self._mark_as_replied(notif_id)
                    print(f"   ✓ Reply posted successfully")
                else:
                    print(f"   ⚠️ Failed to post reply")
            except Exception as e:
                print(f"   ❌ Error posting reply: {e}")
        else:
            print(f"   → Auto-reply disabled, skipping")
    
    def start(self):
        """Start the listener loop."""
        if not self.enabled:
            print("Mastodon listener is disabled in config.yaml")
            return
        
        if not self.current_user_id:
            print("❌ Cannot start listener: Could not get current user ID")
            return
        
        print(f"🔔 Starting Mastodon listener (polling every {self.poll_interval} seconds)...")
        print("Press Ctrl+C to stop\n")
        
        try:
            while True:
                notifications = self._get_notifications()
                relevant = self._filter_relevant_notifications(notifications)
                
                if relevant:
                    print(f"📬 Found {len(relevant)} new comment(s) to reply to")
                    for notif in relevant:
                        self._handle_notification(notif)
                
                # Wait before next check
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n\n👋 Mastodon listener stopped")
        except Exception as e:
            print(f"\n❌ Error in listener loop: {e}")


if __name__ == "__main__":
    listener = MastodonListener()
    listener.start()
