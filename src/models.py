"""
Pydantic models for structured data in BiteRate Social Media AI Agent.
"""
from pydantic import BaseModel, Field
from typing import Optional, List


class Review(BaseModel):
    """Model for a food review from Notion."""
    id: str = Field(description="Notion page ID of the review")
    restaurant: str = Field(description="Name of the restaurant")
    rating: Optional[float] = Field(None, description="Rating out of 5", ge=0, le=5)
    review: Optional[str] = Field(None, description="Review text content")
    cuisine: Optional[str] = Field(None, description="Type of cuisine")
    location: Optional[str] = Field(None, description="Location of the restaurant")


class SocialMediaPost(BaseModel):
    """Structured output model for generated social media posts."""
    content: str = Field(
        description="The main content of the social media post",
        max_length=500
    )
    hashtags: List[str] = Field(
        default_factory=list,
        description="List of hashtags included in the post"
    )
    restaurant_mentioned: Optional[str] = Field(
        None,
        description="Name of the restaurant mentioned in the post, if any"
    )
    rating_mentioned: Optional[float] = Field(
        None,
        description="Rating mentioned in the post, if any",
        ge=0,
        le=5
    )
    tone: str = Field(
        description="The tone/style of the post (e.g., friendly, professional, casual)"
    )
    
    def to_mastodon_post(self) -> str:
        """Convert the structured post to a Mastodon-ready string."""
        post = self.content
        if self.hashtags:
            post += "\n\n" + " ".join(self.hashtags)
        return post
    
    def __str__(self) -> str:
        """String representation of the post."""
        return self.to_mastodon_post()
