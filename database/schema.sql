-- SQLite Database Schema for BiteRate Social Media AI Agent
-- This schema stores reviews, posts, feedback, and workflow history

-- Reviews table (from Notion)
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    notion_page_id TEXT UNIQUE NOT NULL,
    restaurant TEXT NOT NULL,
    rating REAL CHECK (rating >= 0 AND rating <= 5),
    review TEXT,
    cuisine TEXT,
    location TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Social Media Posts table (generated posts)
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    hashtags TEXT,  -- JSON array stored as text
    restaurant_mentioned TEXT,
    rating_mentioned REAL CHECK (rating_mentioned >= 0 AND rating_mentioned <= 5),
    tone TEXT,
    image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    mastodon_post_id TEXT,
    mastodon_url TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'published', 'failed'))
);

-- Telegram Approval History
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject')),
    rejection_reason TEXT,
    approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id)
);

-- Feedback History (for learning and improvement)
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER,
    feedback_type TEXT CHECK (feedback_type IN ('rejection', 'edit', 'improvement')),
    feedback_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id)
);

-- Reply History (for Mastodon replies)
CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_post_id TEXT NOT NULL,  -- Mastodon post ID being replied to
    original_post_url TEXT,
    original_content TEXT,
    reply_content TEXT NOT NULL,
    tone TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP,
    mastodon_reply_id TEXT,
    mastodon_url TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'published', 'failed'))
);

-- Workflow Execution Log
CREATE TABLE IF NOT EXISTS workflow_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_type TEXT NOT NULL CHECK (workflow_type IN ('post_generation', 'reply_generation')),
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    error_message TEXT,
    metadata TEXT  -- JSON stored as text for additional context
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_reviews_restaurant ON reviews(restaurant);
CREATE INDEX IF NOT EXISTS idx_reviews_cuisine ON reviews(cuisine);
CREATE INDEX IF NOT EXISTS idx_reviews_location ON reviews(location);
CREATE INDEX IF NOT EXISTS idx_reviews_rating ON reviews(rating);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at);
CREATE INDEX IF NOT EXISTS idx_posts_published_at ON posts(published_at);
CREATE INDEX IF NOT EXISTS idx_approvals_post_id ON approvals(post_id);
CREATE INDEX IF NOT EXISTS idx_approvals_decision ON approvals(decision);
CREATE INDEX IF NOT EXISTS idx_feedback_post_id ON feedback(post_id);
CREATE INDEX IF NOT EXISTS idx_replies_status ON replies(status);
CREATE INDEX IF NOT EXISTS idx_workflow_logs_type ON workflow_logs(workflow_type);
CREATE INDEX IF NOT EXISTS idx_workflow_logs_status ON workflow_logs(status);

-- Triggers to update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS update_reviews_timestamp 
    AFTER UPDATE ON reviews
    BEGIN
        UPDATE reviews SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Function to get recent posts (SQLite doesn't support stored functions, but we can create views)
CREATE VIEW IF NOT EXISTS recent_posts AS
    SELECT 
        p.*,
        a.decision as approval_decision,
        a.rejection_reason
    FROM posts p
    LEFT JOIN approvals a ON p.id = a.post_id
    ORDER BY p.created_at DESC
    LIMIT 50;

-- View for posts by status
CREATE VIEW IF NOT EXISTS posts_by_status AS
    SELECT 
        status,
        COUNT(*) as count,
        MAX(created_at) as latest_post
    FROM posts
    GROUP BY status;
