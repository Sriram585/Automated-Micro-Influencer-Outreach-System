import os
from dotenv import load_dotenv

load_dotenv()

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SEND_MODE = os.getenv("SEND_MODE", "SIMULATE")  # "SIMULATE" or "LIVE_SMTP"
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
TEST_RECEIVER_EMAIL = os.getenv("TEST_RECEIVER_EMAIL", "")

# Target Niche & Discovery Queries (Fetches ~65-80 unique channels across queries)
TARGET_NICHE = "Technology & AI"
SEARCH_QUERIES = [
    "AI engineering tutorial",
    "Python automation projects",
    "LLM agents tutorial",
    "Machine learning portfolio projects",
    "Full stack AI app tutorial",
    "Coding workflow automation"
]

# Filtering Thresholds (Requirement: 5,000 to 100,000 followers)
MIN_FOLLOWERS = 5000
MAX_FOLLOWERS = 100000
MIN_ENGAGEMENT_RATE = 1.0  # 1.0% minimum median engagement rate across recent videos

# Brand Campaign Context for Personalization
BRAND_NAME = "NexusAI Studio"
BRAND_OFFER = (
    "a paid sponsorship and affiliate partnership for NexusAI, our automated "
    "local LLM debugging and prompt-testing workbench built for developers"
)

DB_PATH = "data/outreach.db"