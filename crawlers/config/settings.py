"""
Crawler Settings and Configuration
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BASE_DIR.parent
load_dotenv(PROJECT_DIR / ".env")
os.environ.setdefault("KAGGLE_CONFIG_DIR", str(PROJECT_DIR / ".kaggle"))


def _env_value(name: str) -> str | None:
    """Return configured env values while ignoring template placeholders."""
    value = os.getenv(name)
    if not value or value.lower().startswith("your_"):
        return None
    return value


OUTPUT_DIR = BASE_DIR / "output"
REPOS_DIR = OUTPUT_DIR / "repos"
REPORTS_DIR = OUTPUT_DIR / "reports"
DATASETS_DIR = OUTPUT_DIR / "datasets"
EXPLOITS_DIR = OUTPUT_DIR / "exploits"

# Ensure directories exist
for dir_path in [REPOS_DIR, REPORTS_DIR, DATASETS_DIR, EXPLOITS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# API Keys (from environment)
GITHUB_TOKEN = _env_value("GITHUB_TOKEN")
KAGGLE_USERNAME = _env_value("KAGGLE_USERNAME")
KAGGLE_KEY = _env_value("KAGGLE_KEY")
HUGGINGFACE_TOKEN = _env_value("HUGGINGFACE_TOKEN")

# Rate limiting settings
RATE_LIMITS = {
    "github": {"calls": 30, "period": 60},  # 30 calls per minute
    "web_scraper": {"calls": 10, "period": 60},  # 10 calls per minute
    "kaggle": {"calls": 5, "period": 60},
    "huggingface": {"calls": 10, "period": 60},
}

# Retry settings
RETRY_CONFIG = {
    "max_attempts": 3,
    "wait_min": 1,
    "wait_max": 10,
    "wait_multiplier": 2,
}

# Request settings
REQUEST_TIMEOUT = 30
USER_AGENT = "SmartContractSecurityCrawler/1.0"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# File extensions to collect
SOLIDITY_EXTENSIONS = [".sol"]
DOCUMENT_EXTENSIONS = [".md", ".pdf", ".txt", ".html"]
DATA_EXTENSIONS = [".json", ".csv", ".yaml", ".yml"]

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = BASE_DIR / "crawler.log"

# Scheduling
SCHEDULE_CONFIG = {
    "github_repos": "daily",
    "web_scrapers": "weekly",
    "datasets": "monthly",
}
