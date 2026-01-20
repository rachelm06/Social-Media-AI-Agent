"""
LLM Client for generating social media posts from BiteRate content.
"""
import os
from typing import List, Optional
from openai import OpenAI
from src.models import Review


class LLMClient:
    """Client for generating social media posts using LLM."""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        model: str = "z-ai/glm-4.5-air:free", 
        temperature: float = 0.7,
        provider: str = "openrouter",
        max_tokens: int = 500
    ):
        """
        Initialize LLM client.
        
        Args:
            api_key: API key. If None, will try to get from environment.
            model: Model to use for generation
            temperature: Temperature for generation
            provider: Provider to use - "openai" or "openrouter"
            max_tokens: Maximum tokens to generate
        """
        self.max_tokens = max_tokens
        self.provider = provider.lower()
        
        if self.provider == "openrouter":
            self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
            if not self.api_key:
                raise ValueError("OpenRouter API key is required. Set OPENROUTER_API_KEY or OPENAI_API_KEY in .env file.")
            # OpenRouter uses OpenAI-compatible API with different base URL
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.ai/api/v1",
                default_headers={
                    "HTTP-Referer": "https://github.com/biterate-social-media-agent",
                    "X-Title": "BiteRate Social Media Agent",
                }
            )
        else:
            # Default to OpenAI
            self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
            if not self.api_key:
                raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env file.")
            self.client = OpenAI(api_key=self.api_key)
        
        self.model = model
        self.temperature = temperature
    
    def generate_post(
        self,
        company_info: str,
        reviews: List[Review],
        tone: str = "friendly and engaging",
        max_length: int = 500,
        include_hashtags: bool = True,
        hashtags: List[str] = None,
        guidelines: str = ""
    ) -> str:
        """
        Generate a social media post based on company info and reviews.
        
        Args:
            company_info: Company information from Notion
            reviews: List of Review Pydantic models
            tone: Desired tone for the post
            max_length: Maximum character length
            include_hashtags: Whether to include hashtags
            hashtags: List of hashtags to include
            guidelines: Additional posting guidelines
            
        Returns:
            Plain text social media post
        """
        hashtags = hashtags or []
        
        # Prepare context from reviews
        review_context = self._format_reviews_for_context(reviews)
        
        # Create prompt
        prompt = self._create_prompt(company_info, review_context, tone, max_length, include_hashtags, hashtags, guidelines)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a social media manager for BiteRate, a food review company. Create engaging, authentic social media posts that highlight food reviews and company values. Return only the post text, nothing else."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            post_text = response.choices[0].message.content.strip()
            
            # Remove hashtags if LLM already included them (to avoid duplicates)
            # Only remove lines that are purely hashtags
            if post_text:
                lines = post_text.split('\n')
                cleaned_lines = []
                for line in lines:
                    line_stripped = line.strip()
                    # Skip lines that are ONLY hashtags (and maybe whitespace)
                    if line_stripped and all(word.strip().startswith('#') for word in line_stripped.split() if word.strip()):
                        # This line is only hashtags, skip it
                        continue
                    cleaned_lines.append(line)
                post_text = '\n'.join(cleaned_lines).strip()
            
            # Ensure post doesn't exceed max_length (before adding hashtags)
            if post_text and len(post_text) > max_length - 50:  # Leave room for hashtags
                post_text = post_text[:max_length - 53] + "..."
            
            # Add hashtags if requested (only if not already in the text)
            if include_hashtags and hashtags:
                hashtag_str = " ".join(hashtags)
                # Make sure adding hashtags doesn't exceed max_length
                if len(post_text) + len(hashtag_str) + 2 <= max_length:
                    post_text = post_text + "\n\n" + hashtag_str
                else:
                    # If adding hashtags would exceed, just append without newline
                    remaining = max_length - len(post_text) - 1
                    if remaining > 0:
                        post_text = post_text + " " + " ".join(hashtags)[:remaining]
            
            return post_text
        except Exception as e:
            print(f"Error generating post: {e}")
            # Return a minimal fallback post
            fallback = "Check out our latest food reviews on BiteRate!"
            if include_hashtags and hashtags:
                fallback += "\n\n" + " ".join(hashtags)
            return fallback
    
    def _format_reviews_for_context(self, reviews: List[Review]) -> str:
        """Format reviews into a context string for the LLM."""
        if not reviews:
            return "No recent reviews available."
        
        formatted = []
        for i, review in enumerate(reviews[:5], 1):  # Use top 5 reviews
            review_str = f"Review {i}:\n"
            review_str += f"Restaurant: {review.restaurant}\n"
            if review.cuisine:
                review_str += f"Cuisine: {review.cuisine}\n"
            if review.location:
                review_str += f"Location: {review.location}\n"
            if review.rating is not None:
                review_str += f"Rating: {review.rating}/5\n"
            if review.review:
                review_str += f"Review: {review.review}\n"
            
            formatted.append(review_str)
        
        return "\n\n".join(formatted)
    
    def _create_prompt(
        self,
        company_info: str,
        review_context: str,
        tone: str,
        max_length: int,
        include_hashtags: bool,
        hashtags: List[str],
        guidelines: str = ""
    ) -> str:
        """Create the prompt for post generation."""
        prompt = f"""Generate a social media post for BiteRate, a food review company based on the following information.

IMPORTANT: Use the specific details from the Company Information and Recent Reviews below to create your post. Reference actual restaurants, dishes, locations, and ratings mentioned.

Company Information:
{company_info}

Recent Reviews:
{review_context}

Requirements:
- Tone: {tone}
- Maximum length: {max_length} characters
- Make it engaging and authentic
- Focus on food experiences and reviews
- Keep it concise and social media friendly
- Do NOT include hashtags in your response - they will be added automatically"""

        if guidelines:
            prompt += f"\n\nPosting Guidelines:\n{guidelines}"
        
        prompt += "\n\nGenerate the post text now. Use the actual review content above. Return only the post text, no explanations or hashtags:"
        
        return prompt