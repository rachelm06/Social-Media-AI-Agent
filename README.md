# BiteRate Social Media AI Agent

An AI-powered social media post generator for BiteRate, a fictional food review company. This agent fetches company information and reviews from Notion, generates engaging social media posts using an LLM, creates custom AI-generated images, and posts them to Mastodon with optional human-in-the-loop approval via Telegram.

## Features

- 📚 **Notion Integration**: Fetches company info and food reviews from Notion databases/pages
- 🤖 **LLM-Powered Generation**: Uses OpenRouter/OpenAI to create engaging social media posts
- 🎨 **AI Image Generation**: Generates custom images using fine-tuned FLUX models on Replicate
- 🐘 **Mastodon Integration**: Posts generated content and images to Mastodon
- 👤 **Human-in-the-Loop (HITL)**: Optional Telegram approval workflow for human oversight
- 🔍 **Reply Generation**: Search Mastodon for food-related posts and generate structured replies
- ⚙️ **Configurable**: Easy configuration via YAML and environment variables

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or use `uv`:

```bash
uv sync
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Notion API Configuration
NOTION_API_KEY=your_notion_api_key_here

# LLM API Configuration (OpenRouter or OpenAI)
OPENROUTER_API_KEY=your_openrouter_api_key_here
# OR
OPENAI_API_KEY=your_openai_api_key_here

# Replicate API Configuration (for image generation)
REPLICATE_API_TOKEN=your_replicate_api_token_here

# Telegram Configuration (for HITL approval)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here

# Mastodon Configuration
MASTODON_INSTANCE_URL=https://your-mastodon-instance.com
MASTODON_ACCESS_TOKEN=your_access_token_here
```

### 3. Get API Keys

#### Notion API Key
1. Go to https://www.notion.so/my-integrations
2. Create a new integration
3. Copy the "Internal Integration Token"
4. Share your Notion pages/databases with the integration

#### OpenRouter API Key
1. Go to https://openrouter.ai/keys
2. Create a new API key
3. Copy the key

#### Replicate API Token
1. Go to https://replicate.com/account/api-tokens
2. Create a new API token
3. Copy the token

#### Telegram Bot Token & Chat ID
1. Open Telegram and search for `@BotFather`
2. Send `/newbot` and follow the instructions
3. Copy the bot token you receive
4. Start a chat with your bot
5. Visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
6. Find your chat ID in the response (`"chat":{"id":XXXXXXXX}`)

#### Mastodon Access Token
1. Go to your Mastodon instance settings
2. Navigate to Development > Applications
3. Create a new application
4. Copy the access token

### 4. Configure the Agent

Edit `config.yaml` to specify:
- Notion database/page IDs to fetch from
- LLM model and settings (OpenRouter/OpenAI)
- Image generation settings (trigger word, model version)
- Telegram HITL settings
- Post generation preferences (tone, length, hashtags)
- Mastodon visibility settings

## Usage

### Main Workflow (Post Generation)

Run the agent:

```bash
python run.py
```

The agent will:
1. Fetch company info and reviews from Notion
2. Generate a social media post using the LLM
3. Generate a custom AI image using your fine-tuned Replicate model
4. Send the post to Telegram for approval (if enabled)
5. Post to Mastodon if approved (or skip if rejected)

### Reply Generation

Generate replies to recent Mastodon posts:

```bash
python reply_to_posts.py
```

This will:
1. Search Mastodon for food/restaurant-related posts
2. Generate replies using structured outputs
3. Display what would be replied (dry-run mode)

## Configuration

### config.yaml

```yaml
# Notion Settings
notion:
  database_ids: []  # List of Notion database IDs
  page_ids: []      # List of Notion page IDs
  max_reviews: 10   # Maximum reviews to fetch

# LLM Settings
llm:
  provider: "openrouter"  # Options: openai, openrouter
  model: "z-ai/glm-4.5-air:free"  # Model to use
  temperature: 0.7
  max_tokens: 500

# Post Generation Settings
post_generation:
  tone: "friendly and engaging"
  max_length: 500
  include_hashtags: true
  hashtags: ["#BiteRate", "#FoodReview", "#Foodie", "#AIGenerated"]

# Image Generation Settings
image_generation:
  trigger_word: "P3@NUT"  # Trigger word for fine-tuned model
  model: "sundai-club/rachel_frenchie_mode:version_hash"  # Full model version

# Telegram HITL Settings
telegram:
  enabled: true  # Enable Telegram human-in-the-loop approval

# Mastodon Settings
mastodon:
  visibility: "public"  # public, unlisted, private, direct
  dry_run: false       # Set to true to preview without posting
```

## Workflow

### Main Post Generation Flow

```
Notion Content → LLM Post Generation → AI Image Generation → Telegram Approval → Mastodon Post
                                            ↓
                                     (If Rejected)
                                            ↓
                                     Collect Feedback
```

### Telegram HITL Workflow

When enabled, the agent will:
1. Send the generated post and image preview to Telegram
2. Display Approve/Reject buttons
3. Wait for your decision
4. If approved: Post to Mastodon
5. If rejected: Ask for feedback reason and skip posting

## Project Structure

```
Social Media AI Agent/
├── .env                    # API keys (not in git)
├── config.yaml             # Configuration settings
├── requirements.txt        # Python dependencies
├── pyproject.toml          # Project metadata (for uv)
├── README.md               # This file
├── run.py                  # Main entry point
├── reply_to_posts.py       # Reply generation script
├── src/
│   ├── __init__.py
│   ├── agent.py            # Main orchestration script
│   ├── notion_client.py    # Notion API integration
│   ├── llm_client.py       # LLM integration (OpenRouter/OpenAI)
│   ├── image_client.py     # Replicate image generation
│   ├── telegram_client.py  # Telegram HITL approval workflow
│   ├── mastodon_client.py  # Mastodon API integration
│   └── models.py           # Pydantic data models
└── .gitignore
```

## Key Features Explained

### Human-in-the-Loop (HITL)

The Telegram integration allows you to review every post before it goes live. This provides:
- **Quality control**: Catch errors before publishing
- **Brand consistency**: Ensure posts match your voice
- **Learning opportunity**: Rejection feedback can improve future generations

### AI Image Generation

The agent generates custom images using your fine-tuned FLUX model. Each post includes a unique image created with the prompt: `"{trigger_word} is in a restaurant"`.

### Structured Replies

The reply generation feature uses structured outputs (Pydantic models) to generate consistent, well-formatted replies to multiple posts at once.

## Notes

- Ensure your Notion pages/databases are shared with your integration
- Mastodon posts are limited to 500 characters by default (configurable)
- Telegram HITL approval has a 5-minute timeout
- Image generation may take 10-30 seconds depending on Replicate queue
- Make sure all API keys are properly set in `.env` before running

## License

This is a fictional project for demonstration purposes.
