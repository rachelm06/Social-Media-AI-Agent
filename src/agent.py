"""
Main orchestration script for BiteRate Social Media AI Agent.
"""
import os
import yaml
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from src.notion_client import NotionClient
from src.llm_client import LLMClient
from src.mastodon_client import MastodonClient
from src.image_client import ImageClient
from src.telegram_client import TelegramClient
from src.models import Review


class BiteRateAgent:
    """Main agent for generating and posting social media content."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the BiteRate agent.
        
        Args:
            config_path: Path to configuration YAML file
        """
        # Load environment variables
        load_dotenv()
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize clients
        self.notion_client = NotionClient()
        self.llm_client = LLMClient(
            model=self.config.get("llm", {}).get("model", "z-ai/glm-4.5-air:free"),
            temperature=self.config.get("llm", {}).get("temperature", 0.7),
            provider=self.config.get("llm", {}).get("provider", "openrouter"),
            max_tokens=self.config.get("llm", {}).get("max_tokens", 500)
        )
        self.image_client = ImageClient()
        self.mastodon_client = MastodonClient(
            visibility=self.config.get("mastodon", {}).get("visibility", "public")
        )
        
        # Initialize Telegram client if enabled
        telegram_enabled = self.config.get("telegram", {}).get("enabled", False)
        self.telegram_client = None
        if telegram_enabled:
            try:
                self.telegram_client = TelegramClient()
                print("✓ Telegram HITL enabled")
            except ValueError as e:
                print(f"⚠️ Telegram client not initialized: {e}")
                print("   Continuing without HITL approval...")
    
    def run(self):
        """Execute the main workflow: fetch content, generate post, and post to Mastodon."""
        print("🍽️  BiteRate Social Media AI Agent Starting...\n")
        
        # Step 1: Fetch content from Notion
        print("Step 1: Fetching content from Notion...")
        company_info = self._fetch_company_info()
        reviews = self._fetch_reviews()
        
        if not company_info and not reviews:
            print("⚠️  Warning: No content fetched from Notion.")
            print("  - Check that your API keys are correct in .env file")
            print("  - Verify page/database IDs are correct in config.yaml")
            print("  - Ensure pages/databases are shared with your Notion integration")
            print("  - Note: Empty pages or pages with only child pages may return no text")
            return
        
        print(f"✓ Fetched company info ({len(company_info)} chars)")
        print(f"✓ Fetched {len(reviews)} reviews\n")
        
        # Step 2: Generate social media post
        print("Step 2: Generating social media post with LLM...")
        post = self._generate_post(company_info, reviews)
        
        if not post:
            print("❌ Failed to generate post.")
            return
        
        print(f"✓ Generated post ({len(post)} characters)\n")
        print("Generated Post:")
        print("-" * 60)
        print(post)
        print("-" * 60 + "\n")
        
        # Step 2.5: Generate AI image
        print("Step 2.5: Generating AI image...")
        image_config = self.config.get("image_generation", {})
        trigger_word = image_config.get("trigger_word", "P3@NUT")
        model = image_config.get("model", "sundai-club/rachel_frenchie_mode:b07cb658fe2949e3fa1fa6f1f593f22e6cc62d6190eae8896fdc76ade752765b")
        image_prompt = f"{trigger_word} is in a restaurant"
        image_url = self.image_client.generate_image(image_prompt, model=model)
        
        media_files = None
        image_url_for_approval = None
        if image_url:
            print(f"✓ Generated image: {image_url}")
            image_url_for_approval = image_url  # Store for approval message
            # Download the image for Mastodon upload
            image_data = self.image_client.download_image(image_url)
            if image_data:
                media_files = [image_data]
                print(f"✓ Downloaded image for upload\n")
            else:
                print("⚠️ Failed to download image\n")
        else:
            print("⚠️ Failed to generate image\n")
        
        # Step 2.75: Human approval via Telegram (if enabled)
        
        if self.telegram_client:
            print("Step 2.75: Requesting human approval via Telegram...")
            decision, rejection_reason = self.telegram_client.request_approval_sync(
                post,
                image_url=image_url_for_approval
            )
            
            if decision == "approve":
                print("✅ Post approved! Proceeding to publish...\n")
            elif decision == "reject":
                print(f"❌ Post rejected.")
                if rejection_reason:
                    print(f"   Reason: {rejection_reason}")
                print("   Post will NOT be published.\n")
                return {"status": "rejected", "reason": rejection_reason}
            else:
                print(f"⚠️ Unknown decision: {decision}\n")
                return {"status": "error", "decision": decision}
        else:
            print("Step 2.75: Skipping Telegram approval (not enabled)\n")
        
        # Step 3: Post to Mastodon (or print in dry run mode)
        print("Step 3: Posting to Mastodon...")
        dry_run = self.config.get("mastodon", {}).get("dry_run", True)
        result = self.mastodon_client.post(post, media_files=media_files, dry_run=dry_run)
        
        print("✓ Workflow complete!\n")
        return result
    
    def _fetch_company_info(self) -> str:
        """Fetch company information from Notion."""
        page_ids = self.config.get("notion", {}).get("page_ids", [])
        company_info_parts = []
        
        for page_id in page_ids:
            content = self.notion_client.get_page_content(page_id)
            if content:
                company_info_parts.append(content)
        
        return "\n\n".join(company_info_parts)
    
    def _fetch_reviews(self) -> list:
        """Fetch reviews from Notion databases and pages."""
        max_reviews = self.config.get("notion", {}).get("max_reviews", 10)
        all_reviews = []
        
        # First, try databases (if any)
        database_ids = self.config.get("notion", {}).get("database_ids", [])
        for database_id in database_ids:
            reviews = self.notion_client.get_reviews(database_id, max_reviews)
            all_reviews.extend(reviews)
        
        # Also fetch from pages (for individual review pages)
        page_ids = self.config.get("notion", {}).get("page_ids", [])
        for page_id in page_ids:
            content = self.notion_client.get_page_content(page_id)
            if content:
                # Parse the page content as a review
                review = self._parse_page_as_review(page_id, content)
                if review:
                    all_reviews.append(review)
        
        return all_reviews[:max_reviews]
    
    def _parse_page_as_review(self, page_id: str, content: str) -> Optional[Review]:
        """Parse page content into a Review object."""
        try:
            lines = content.split('\n')
            review_data = {
                "id": page_id,
                "restaurant": "Unknown Restaurant",
                "rating": None,
                "review": "",
                "cuisine": None,
                "location": None
            }
            
            # Parse structured fields
            current_section = None
            review_text_parts = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check for field labels
                if line.startswith("Location:"):
                    review_data["location"] = line.replace("Location:", "").strip()
                elif line.startswith("Cuisine:"):
                    review_data["cuisine"] = line.replace("Cuisine:", "").strip()
                elif line.startswith("Rating:"):
                    rating_str = line.replace("Rating:", "").strip()
                    # Handle formats like "4/5" or "4.5/5"
                    try:
                        rating_value = rating_str.split("/")[0].strip()
                        review_data["rating"] = float(rating_value)
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("Review:"):
                    # Start collecting review text
                    review_text = line.replace("Review:", "").strip()
                    if review_text:
                        review_text_parts.append(review_text)
                    current_section = "review"
                elif "Restaurant" in line and not line.startswith("Location") and not line.startswith("Cuisine"):
                    # Try to extract restaurant name (might be first line or standalone)
                    restaurant_name = line.replace("Restaurant", "").strip()
                    if restaurant_name and review_data["restaurant"] == "Unknown Restaurant":
                        review_data["restaurant"] = restaurant_name
                elif current_section == "review" or (not any(line.startswith(field) for field in ["Location:", "Cuisine:", "Rating:", "Review:"])):
                    # Collect review text (everything after "Review:" or unstructured content)
                    if not any(line.startswith(field) for field in ["Location:", "Cuisine:", "Rating:"]):
                        review_text_parts.append(line)
            
            # Combine review text
            if review_text_parts:
                review_data["review"] = "\n".join(review_text_parts).strip()
            elif not review_data["review"]:
                # If no "Review:" label, use the content as review
                review_data["review"] = content.strip()
            
            # Try to extract restaurant name from first line if still unknown
            if review_data["restaurant"] == "Unknown Restaurant":
                first_line = lines[0].strip() if lines else ""
                # Common patterns: "Restaurant Name", "Restaurant Name — Type", etc.
                if first_line and not first_line.startswith("Location") and not first_line.startswith("Cuisine"):
                    potential_name = first_line.split("—")[0].split("Restaurant")[0].strip()
                    if potential_name:
                        review_data["restaurant"] = potential_name
            
            return Review(**review_data)
        except Exception as e:
            print(f"Error parsing page {page_id} as review: {e}")
            return None
    
    def _generate_post(self, company_info: str, reviews: list) -> str:
        """Generate a social media post using the LLM."""
        post_config = self.config.get("post_generation", {})
        
        # Get hashtags from config and ensure #AIGenerated is always included
        hashtags = post_config.get("hashtags", ["#BiteRate", "#FoodReview", "#Foodie"])
        # Normalize hashtags (ensure they start with #)
        hashtags = [tag if tag.startswith("#") else f"#{tag}" for tag in hashtags]
        # Ensure #AIGenerated is always included
        if "#AIGenerated" not in hashtags:
            hashtags.append("#AIGenerated")
        
        post = self.llm_client.generate_post(
            company_info=company_info,
            reviews=reviews,
            tone=post_config.get("tone", "friendly and engaging"),
            max_length=post_config.get("max_length", 500),
            include_hashtags=post_config.get("include_hashtags", True),
            hashtags=hashtags,
            guidelines=post_config.get("guidelines", "")
        )
        
        return post


def main():
    """Main entry point."""
    agent = BiteRateAgent()
    agent.run()


if __name__ == "__main__":
    main()
