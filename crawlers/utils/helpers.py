"""
Helper utilities for the crawler system.
"""
import hashlib
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import yaml
from tenacity import retry, stop_after_attempt, wait_exponential

from config.settings import RETRY_CONFIG, BASE_DIR


def load_sources_config() -> dict:
    """Load the sources configuration from YAML."""
    config_path = BASE_DIR / "config" / "sources.yaml"
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def extract_repo_info(url: str) -> tuple[str, str]:
    """Extract owner and repo name from GitHub URL."""
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) >= 2:
        return parts[0], parts[1]
    raise ValueError(f"Invalid GitHub URL: {url}")


def sanitize_filename(name: str) -> str:
    """Sanitize a string to be safe for use as a filename."""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', "_", name)
    # Remove leading/trailing whitespace and dots
    sanitized = sanitized.strip(". ")
    return sanitized[:255]  # Limit length


def get_file_hash(file_path: Path) -> str:
    """Calculate MD5 hash of a file."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def create_retry_decorator(service: str = "default"):
    """Create a tenacity retry decorator with configured settings."""
    return retry(
        stop=stop_after_attempt(RETRY_CONFIG["max_attempts"]),
        wait=wait_exponential(
            multiplier=RETRY_CONFIG["wait_multiplier"],
            min=RETRY_CONFIG["wait_min"],
            max=RETRY_CONFIG["wait_max"],
        ),
    )


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists and return the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def is_solidity_file(path: Path) -> bool:
    """Check if a file is a Solidity file."""
    return path.suffix.lower() == ".sol"


def is_document_file(path: Path) -> bool:
    """Check if a file is a document (MD, PDF, etc.)."""
    return path.suffix.lower() in [".md", ".pdf", ".txt", ".html"]


def is_data_file(path: Path) -> bool:
    """Check if a file is a data file (JSON, CSV, etc.)."""
    return path.suffix.lower() in [".json", ".csv", ".yaml", ".yml"]


def count_files_by_type(directory: Path) -> dict:
    """Count files in a directory by their extension."""
    counts = {}
    if directory.exists():
        for file in directory.rglob("*"):
            if file.is_file():
                ext = file.suffix.lower() or "no_extension"
                counts[ext] = counts.get(ext, 0) + 1
    return counts
