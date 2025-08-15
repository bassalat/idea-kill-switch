"""Configuration settings for Kill Switch application."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# Claude Settings
CLAUDE_MODEL = "claude-sonnet-4-20250514"  # Claude Sonnet 4 - High-performance with exceptional reasoning
# Pricing: $3/1M input tokens, $15/1M output tokens
CLAUDE_MAX_TOKENS = 4096
CLAUDE_TEMPERATURE = 0.7

# Serper Settings
SERPER_BASE_URL = "https://google.serper.dev"
# Pricing: $0.30 per 1000 queries = $0.0003 per query
SERPER_SEARCH_LIMIT = 500  # Increased to handle broader searches
SERPER_TIME_RANGE = "6 months"

# Firecrawl Settings
FIRECRAWL_BASE_URL = "https://api.firecrawl.dev/v1"
# Pricing: $0.01 per URL scrape
FIRECRAWL_BATCH_SIZE = int(os.getenv("FIRECRAWL_BATCH_SIZE", "10"))  # URLs per batch
FIRECRAWL_MAX_URLS = int(os.getenv("FIRECRAWL_MAX_URLS", "30"))  # Max URLs to scrape per module
FIRECRAWL_TIMEOUT = 30000  # ms
FIRECRAWL_WAIT_FOR = 3000  # ms

# Validation Thresholds - Three Tier System
# Easy Threshold - "Market Exists"
EASY_COMPLAINTS_REQUIRED = 20
EASY_PAIN_SCORE = 5
EASY_QUALITY_THRESHOLD = "low"  # Accepts any quality complaints

# Medium Threshold - "Strong Opportunity" (Default)
MEDIUM_COMPLAINTS_REQUIRED = 40  # Increased for weighted system
MEDIUM_PAIN_SCORE = 6
MEDIUM_QUALITY_THRESHOLD = "medium"  # Requires moderate quality

# Difficult Threshold - "Exceptional Problem"
DIFFICULT_COMPLAINTS_REQUIRED = 60  # High bar for weighted complaints
DIFFICULT_PAIN_SCORE = 8
DIFFICULT_QUALITY_THRESHOLD = "high"  # Requires high-impact complaints
DIFFICULT_URGENCY_THRESHOLD = 40  # % actively seeking solutions
DIFFICULT_EMOTIONAL_THRESHOLD = 30  # % using strong emotional language

# Other validation thresholds
MIN_COMPETITOR_PRICE = 50
MIN_SIGNUP_RATE = 0.02
MIN_WILLINGNESS_TO_PAY = 50

# Default threshold level
DEFAULT_THRESHOLD_LEVEL = "medium"

# Application Settings
APP_NAME = "AI-Powered Kill Switch"
APP_DESCRIPTION = "Validate business ideas quickly with AI"
SESSION_TIMEOUT = 3600  # 1 hour

# Export Settings
EXPORT_DIR = Path("exports")
EXPORT_DIR.mkdir(exist_ok=True)

# API Rate Limiting
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 30  # seconds

# Cache Settings
ENABLE_CACHE = True
CACHE_TTL = 3600  # 1 hour

# UI Settings
PROGRESS_UPDATE_INTERVAL = 0.5  # seconds
MAX_DISPLAY_COMPLAINTS = 20  # Show more sample complaints
MAX_DISPLAY_COMPETITORS = 10