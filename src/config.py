import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
def get_active_groq_model() -> str:
    """Dynamically selects the best available LLM on the user's Groq API key."""
    if not GROQ_API_KEY or GROQ_API_KEY.startswith("your_"):
        return "openai/gpt-oss-120b"
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SEND_MODE = os.getenv("SEND_MODE", "SIMULATE")  # "SIMULATE" or "LIVE_SMTP"
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_EMAIL = os.getenv("SMTP_EMAIL", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
TEST_RECEIVER_EMAIL = os.getenv("TEST_RECEIVER_EMAIL", "")

# Target Niche & Discovery Queries
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
MIN_ENGAGEMENT_RATE = 1.0

# Brand Campaign Context for Personalization
BRAND_NAME = "NexusAI Studio"
BRAND_OFFER = (
    "a paid sponsorship and affiliate partnership for NexusAI, our automated "
    "local LLM debugging and prompt-testing workbench built for developers"
)

DB_PATH = "data/outreach.db"

def get_active_groq_model() -> str:
    """Dynamically selects the best available LLM on the user's Groq API key."""
    preferred_order = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
    ]
    try:
        client = Groq(api_key=GROQ_API_KEY)
        available = {m.id for m in client.models.list().data}
        for candidate in preferred_order:
            if candidate in available:
                print(f"[LLM Config] Using verified Groq model: {candidate}")
                return candidate
        # Fallback to any available text chat model on the account
        for m_id in available:
            if not any(x in m_id.lower() for x in ["whisper", "guard", "orpheus", "tts", "embed"]):
                print(f"[LLM Config] Using discovered Groq model: {m_id}")
                return m_id
    except Exception as e:
        print(f"[LLM Config] Model list check note: {e}")
    return "openai/gpt-oss-120b"

GROQ_MODEL = get_active_groq_model()