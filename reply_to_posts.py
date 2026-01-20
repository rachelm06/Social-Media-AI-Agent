#!/usr/bin/env python3
"""
Script to search for Mastodon posts and generate replies (dry run mode).
"""
import os
import yaml
from dotenv import load_dotenv
from src.mastodon_client import MastodonClient
from src.llm_client import LLMClient
from src.notion_client import NotionClient


def main():
    """Search for posts and generate replies."""
    # Load environment variables
    load_dotenv()
    
    # Load config
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    print("🔍 BiteRate Reply Generator Starting...\n")
    
    # Initialize clients
    mastodon_client = MastodonClient(
        visibility=config.get("mastodon", {}).get("visibility", "public")
    )
    
    notion_client = NotionClient()
    llm_client = LLMClient(
        model=config.get("llm", {}).get("model", "z-ai/glm-4.5-air:free"),
        temperature=config.get("llm", {}).get("temperature", 0.7),
        provider=config.get("llm", {}).get("provider", "openrouter"),
        max_tokens=config.get("llm", {}).get("max_tokens", 500)
    )
    
    # Fetch company info for context
    print("Step 1: Fetching company info from Notion...")
    page_ids = config.get("notion", {}).get("page_ids", [])
    company_info_parts = []
    for page_id in page_ids:
        content = notion_client.get_page_content(page_id)
        if content:
            company_info_parts.append(content)
    company_info = "\n\n".join(company_info_parts) or "BiteRate is a food review company."
    print(f"✓ Company info loaded ({len(company_info)} chars)\n")
    
    # Search for posts
    print("Step 2: Searching Mastodon for food/restaurant related posts...")
    search_queries = ["restaurant", "food review", "dining", "foodie", "restaurant review"]
    
    all_posts = []
    for query in search_queries:
        posts = mastodon_client.search_posts(query, limit=2)  # Get 2 per query
        all_posts.extend(posts)
        if len(all_posts) >= 1:
            break
    
    # Get top 5 unique posts
    seen_ids = set()
    unique_posts = []
    for post in all_posts:
        if post["id"] not in seen_ids:
            seen_ids.add(post["id"])
            unique_posts.append(post)
        if len(unique_posts) >= 1:
            break
    
    if not unique_posts:
        print("❌ No posts found. Try different search keywords.")
        return
    
    print(f"✓ Found {len(unique_posts)} posts to reply to\n")
    
    # Display found posts
    print("Found Posts:")
    print("=" * 80)
    for i, post in enumerate(unique_posts, 1):
        print(f"\nPost {i}:")
        print(f"  ID: {post['id']}")
        print(f"  URL: {post.get('url', 'N/A')}")
        print(f"  User: @{post.get('username', 'unknown')}")
        print(f"  Content: {post['content'][:200]}{'...' if len(post['content']) > 200 else ''}")
    print("=" * 80 + "\n")
    
    # Generate replies
    print("Step 3: Generating replies using LLM...")
    post_config = config.get("post_generation", {})
    
    reply_batch = llm_client.generate_replies(
        posts=unique_posts,
        company_info=company_info,
        tone=post_config.get("tone", "friendly and helpful"),
        max_length=post_config.get("max_length", 500),
        guidelines=post_config.get("guidelines", "")
    )
    
    if not reply_batch.replies:
        print("❌ Failed to generate replies.")
        return
    
    print(f"✓ Generated {len(reply_batch.replies)} replies\n")
    
    # Display replies (dry run mode)
    print("=" * 80)
    print("DRY RUN MODE - Replies that would be posted:")
    print("=" * 80)
    
    for i, reply in enumerate(reply_batch.replies, 1):
        print(f"\n{'='*80}")
        print(f"Reply {i}:")
        print(f"{'='*80}")
        print(f"Original Post ID: {reply.post_id}")
        if reply.post_url:
            print(f"Original Post URL: {reply.post_url}")
        print(f"\nOriginal Post Content:")
        print("-" * 80)
        print(reply.original_content[:300] + ("..." if len(reply.original_content) > 300 else ""))
        print("-" * 80)
        print(f"\nGenerated Reply:")
        print("-" * 80)
        print(reply.reply_content)
        print("-" * 80)
        print(f"Tone: {reply.tone}")
        print(f"Length: {len(reply.reply_content)} characters")
        
        # Show what would happen
        mastodon_client.reply(reply.post_id, reply.reply_content, dry_run=True)
    
    print(f"\n{'='*80}")
    print("Summary:")
    print(f"  • Found {len(unique_posts)} posts")
    print(f"  • Generated {len(reply_batch.replies)} replies")
    print(f"  • Mode: DRY RUN (no replies were actually posted)")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
