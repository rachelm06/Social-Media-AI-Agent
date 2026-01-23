"""
Mastodon Client for posting social media content.
Note: Actual posting is commented out - will print what would be posted instead.
"""
import os
from typing import Optional, List, IO
from mastodon import Mastodon


class MastodonClient:
    """Client for interacting with Mastodon API."""
    
    def __init__(
        self,
        instance_url: Optional[str] = None,
        access_token: Optional[str] = None,
        visibility: str = "public"
    ):
        """
        Initialize Mastodon client.
        
        Args:
            instance_url: Mastodon instance URL
            access_token: Mastodon access token
            visibility: Post visibility (public, unlisted, private, direct)
        """
        self.instance_url = (instance_url or os.getenv("MASTODON_INSTANCE_URL", "")).strip()
        self.access_token = (access_token or os.getenv("MASTODON_ACCESS_TOKEN", "")).strip()
        self.visibility = visibility
        
        if not self.instance_url:
            raise ValueError("Mastodon instance URL is required. Set MASTODON_INSTANCE_URL in .env file.")
        if not self.access_token:
            raise ValueError("Mastodon access token is required. Set MASTODON_ACCESS_TOKEN in .env file.")
        
        self.client = Mastodon(
            access_token=self.access_token,
            api_base_url=self.instance_url
        )
    
    def post(self, content: str, media_files: Optional[List[IO]] = None, dry_run: bool = True) -> dict:
        """
        Post content to Mastodon.
        
        Args:
            content: The post content to publish
            media_files: Optional list of file-like objects (BytesIO) containing images to attach
            dry_run: If True, only print what would be posted (don't actually post)
            
        Returns:
            Dictionary with post information or status
        """
        if dry_run:
            print("\n" + "="*60)
            print("DRY RUN MODE - Would post to Mastodon:")
            print("="*60)
            print(f"Instance: {self.instance_url}")
            print(f"Visibility: {self.visibility}")
            print(f"Content:\n{content}")
            if media_files:
                print(f"Attachments: {len(media_files)} image(s)")
            print("="*60 + "\n")
            
            return {
                "status": "dry_run",
                "content": content,
                "visibility": self.visibility,
                "instance": self.instance_url,
                "media_count": len(media_files) if media_files else 0
            }
        else:
            # Actual posting code
            try:
                media_ids = []
                
                # Upload media files first if provided
                if media_files:
                    for media_file in media_files:
                        media = self.client.media_post(media_file, mime_type="image/jpeg")
                        media_ids.append(media["id"])
                
                # Post with media attachments
                status = self.client.status_post(
                    content,
                    media_ids=media_ids if media_ids else None,
                    visibility=self.visibility
                )
                print(f"Successfully posted to Mastodon!")
                print(f"Post ID: {status.get('id')}")
                print(f"URL: {status.get('url')}")
                if media_ids:
                    print(f"Attached {len(media_ids)} image(s)")
                return status
            except Exception as e:
                print(f"Error posting to Mastodon: {e}")
                import traceback
                traceback.print_exc()
                return {"error": str(e)}
    
    def reply(self, post_id: str, content: str, dry_run: bool = True) -> dict:
        """
        Reply to a Mastodon post.
        
        Args:
            post_id: ID of the post to reply to
            content: The reply content
            dry_run: If True, only print what would be posted
            
        Returns:
            Dictionary with reply information or status
        """
        if dry_run:
            print("\n" + "="*60)
            print("DRY RUN MODE - Would reply to Mastodon post:")
            print("="*60)
            print(f"Replying to post ID: {post_id}")
            print(f"Reply content:\n{content}")
            print("="*60 + "\n")
            
            return {
                "status": "dry_run",
                "content": content,
                "in_reply_to_id": post_id
            }
        else:
            try:
                status = self.client.status_post(
                    content,
                    in_reply_to_id=post_id,
                    visibility=self.visibility
                )
                print(f"Successfully replied to Mastodon post!")
                print(f"Reply ID: {status.get('id')}")
                print(f"URL: {status.get('url')}")
                return status
            except Exception as e:
                print(f"Error replying to Mastodon post: {e}")
                import traceback
                traceback.print_exc()
                return {"error": str(e)}