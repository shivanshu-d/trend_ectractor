import os
from dotenv import load_dotenv
import yaml

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
KEYWORDS_PATH = os.path.join(BASE_DIR, "config", "keywords.yaml")
DB_PATH = os.path.join(DATA_DIR, "db.sqlite3")

# envs
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "trend-extractor/1.0 by yourname")
GEO = os.getenv("GEO", "IN")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true"

def load_keywords():
    try:
        with open(KEYWORDS_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        # fallback: simple keywords
        return {
            "categories": {
                "general": ["marketing","seo","content","ads","social","video","influencer","ai"]
            }
        }
