"""
FastAPI application for BiteRate Social Media AI Agent.
"""
import os
import yaml
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.agent import BiteRateAgent
from src.database_client import DatabaseClient

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="BiteRate Social Media AI Agent API",
    description="API for managing the BiteRate social media automation agent",
    version="1.0.0"
)

# Initialize clients
agent: Optional[BiteRateAgent] = None
db_client: Optional[DatabaseClient] = None

# Pydantic models for API
class RunAgentRequest(BaseModel):
    """Request model for running the agent."""
    dry_run: bool = False

class PostResponse(BaseModel):
    """Response model for posts."""
    id: int
    content: str
    hashtags: List[str]
    status: str
    created_at: str
    published_at: Optional[str] = None
    mastodon_url: Optional[str] = None

class ReviewResponse(BaseModel):
    """Response model for reviews."""
    id: str
    restaurant: str
    rating: Optional[float] = None
    cuisine: Optional[str] = None
    location: Optional[str] = None

class StatsResponse(BaseModel):
    """Response model for statistics."""
    total_posts: int
    published_posts: int
    pending_posts: int
    rejected_posts: int
    total_reviews: int
    total_replies: int

@app.on_event("startup")
async def startup_event():
    """Initialize clients on startup."""
    global agent, db_client
    try:
        agent = BiteRateAgent()
        db_client = DatabaseClient()
        print("✓ API initialized successfully")
    except Exception as e:
        print(f"⚠️ Error initializing API: {e}")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "BiteRate Social Media AI Agent API",
        "version": "1.0.0",
        "endpoints": {
            "POST /run": "Trigger agent workflow",
            "GET /posts": "Get recent posts",
            "GET /reviews": "Get reviews",
            "GET /stats": "Get statistics",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_initialized": agent is not None,
        "database_initialized": db_client is not None
    }

@app.post("/run")
async def run_agent(request: RunAgentRequest, background_tasks: BackgroundTasks):
    """
    Trigger the agent workflow.
    This will fetch from Notion, generate post, create image, get approval, and post to Mastodon.
    """
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    try:
        # Run agent in background
        def run_agent_task():
            result = agent.run()
            return result
        
        # For now, run synchronously (can be made async later)
        result = run_agent_task()
        
        return {
            "status": "success",
            "message": "Agent workflow completed",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running agent: {str(e)}")

@app.get("/posts", response_model=List[PostResponse])
async def get_posts(limit: int = 10, status: Optional[str] = None):
    """Get recent posts from database."""
    if not db_client:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        posts = db_client.get_recent_posts(limit=limit)
        
        # Filter by status if provided
        if status:
            posts = [p for p in posts if p.get("status") == status]
        
        # Convert to response format
        result = []
        for post in posts:
            hashtags = []
            if post.get("hashtags"):
                import json
                try:
                    hashtags = json.loads(post["hashtags"])
                except:
                    hashtags = []
            
            result.append(PostResponse(
                id=post["id"],
                content=post["content"],
                hashtags=hashtags,
                status=post.get("status", "unknown"),
                created_at=post.get("created_at", ""),
                published_at=post.get("published_at"),
                mastodon_url=post.get("mastodon_url")
            ))
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching posts: {str(e)}")

@app.get("/reviews", response_model=List[ReviewResponse])
async def get_reviews(limit: int = 10):
    """Get reviews from database."""
    if not db_client:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        conn = db_client._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reviews ORDER BY created_at DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        conn.close()
        
        return [ReviewResponse(
            id=row["id"],
            restaurant=row["restaurant"],
            rating=row["rating"],
            cuisine=row["cuisine"],
            location=row["location"]
        ) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching reviews: {str(e)}")

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get workflow statistics."""
    if not db_client:
        raise HTTPException(status_code=500, detail="Database not initialized")
    
    try:
        conn = db_client._get_connection()
        cursor = conn.cursor()
        
        # Get post counts
        cursor.execute("SELECT status, COUNT(*) as count FROM posts GROUP BY status")
        status_counts = {row["status"]: row["count"] for row in cursor.fetchall()}
        
        # Get review count
        cursor.execute("SELECT COUNT(*) as count FROM reviews")
        total_reviews = cursor.fetchone()["count"]
        
        # Get reply count
        cursor.execute("SELECT COUNT(*) as count FROM replies")
        total_replies = cursor.fetchone()["count"]
        
        conn.close()
        
        return StatsResponse(
            total_posts=sum(status_counts.values()),
            published_posts=status_counts.get("published", 0),
            pending_posts=status_counts.get("pending", 0),
            rejected_posts=status_counts.get("rejected", 0),
            total_reviews=total_reviews,
            total_replies=total_replies
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
