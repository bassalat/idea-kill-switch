"""Configuration settings for Kill Switch application."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Claude Settings
CLAUDE_MODEL = "claude-sonnet-4-20250514"  # Claude Sonnet 4 - High-performance with exceptional reasoning
CLAUDE_MAX_TOKENS = 4096
CLAUDE_TEMPERATURE = 0.7

# Serper Settings
SERPER_BASE_URL = "https://google.serper.dev"
SERPER_SEARCH_LIMIT = 500  # Increased to handle broader searches
SERPER_TIME_RANGE = "6 months"

# Validation Thresholds
MIN_COMPLAINTS_REQUIRED = 30  # Reduced since we're analyzing broader discussions
MIN_PAIN_SCORE = 6  # Slightly reduced to account for indirect pain signals
MIN_COMPETITOR_PRICE = 50
MIN_SIGNUP_RATE = 0.02
MIN_WILLINGNESS_TO_PAY = 50

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