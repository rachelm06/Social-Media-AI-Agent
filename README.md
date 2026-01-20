# BiteRate Social Media AI Agent

An AI-powered social media post generator for BiteRate, a fictional food review company. This agent fetches company information and reviews from Notion, generates engaging social media posts using an LLM, and posts them to Mastodon.

## Features

- 📚 **Notion Integration**: Fetches company info and food reviews from Notion databases/pages
- 🤖 **LLM-Powered Generation**: Uses OpenAI GPT-4 to create engaging social media posts
- 🐘 **Mastodon Integration**: Posts generated content to Mastodon (currently in dry-run mode)
- ⚙️ **Configurable**: Easy configuration via YAML and environment variables

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Notion API Configuration
NOTION_API_KEY=your_notion_api_key_here
NOTION_DATABASE_ID=your_database_id_here

# LLM API Configuration (OpenAI)
OPENAI_API_KEY=your_openai_api_key_here

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

#### OpenAI API Key
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy the key

#### Mastodon Access Token
1. Go to your Mastodon instance settings
2. Navigate to Development > Applications
3. Create a new application
4. Copy the access token

### 4. Configure the Agent

Edit `config.yaml` to specify:
- Notion database/page IDs to fetch from
- LLM model and settings
- Post generation preferences (tone, length, hashtags)
- Mastodon visibility settings

## Usage

Run the agent:

```bash
python -m src.agent
```

Or:

```bash
cd src
python agent.py
```

## Current Behavior

- **Dry Run Mode**: By default, the agent will NOT actually post to Mastodon. Instead, it will print what would be posted to the command line.
- **Posting Disabled**: The actual Mastodon posting code is commented out. To enable posting, uncomment the code in `src/mastodon_client.py` and set `dry_run: false` in `config.yaml`.

## Project Structure

```
Social Media AI Agent/
├── .env                    # API keys (not in git)
├── config.yaml             # Configuration settings
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── src/
│   ├── __init__.py
│   ├── notion_client.py    # Notion API integration
│   ├── llm_client.py       # LLM integration
│   ├── mastodon_client.py  # Mastodon API integration
│   └── agent.py            # Main orchestration script
└── .gitignore
```

## Configuration

### config.yaml

```yaml
notion:
  database_ids: []  # List of Notion database IDs
  page_ids: []      # List of Notion page IDs
  max_reviews: 10   # Maximum reviews to fetch

llm:
  model: "gpt-4"    # LLM model to use
  temperature: 0.7  # Generation temperature

post_generation:
  tone: "friendly and engaging"
  max_length: 500
  include_hashtags: true
  hashtags: ["#BiteRate", "#FoodReview", "#Foodie"]

mastodon:
  visibility: "public"  # public, unlisted, private, direct
  dry_run: true        # Set to false to actually post
```

## Notes

- The agent currently prints what would be posted instead of actually posting
- Make sure your Notion pages/databases are shared with your integration
- Mastodon posts are limited to 500 characters by default (configurable)
- The agent fetches the most recent reviews from specified databases

## License

This is a fictional project for demonstration purposes.
# Social-Media-AI-Agent
