"""
Base scraper utilities for web sources.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from ratelimit import limits, sleep_and_retry

from config.settings import HEADERS, REQUEST_TIMEOUT, RATE_LIMITS
from utils.helpers import create_retry_decorator, ensure_dir, sanitize_filename
from utils.logger import log


class BaseScraper(ABC):
    """Base class for web scrapers with shared utilities."""

    def __init__(self, base_url: str, output_dir: Path, requires_js: bool = False):
        self.base_url = base_url.rstrip("/")
        self.output_dir = ensure_dir(output_dir)
        self.requires_js = requires_js
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Return a list of scraped records."""
        raise NotImplementedError

    def build_url(self, endpoint: str) -> str:
        """Join the base URL with an endpoint."""
        return urljoin(f"{self.base_url}/", endpoint.lstrip("/"))

    @sleep_and_retry
    @limits(calls=RATE_LIMITS["web_scraper"]["calls"], period=RATE_LIMITS["web_scraper"]["period"])
    def _rate_limited_get(self, url: str, headers: Optional[dict] = None) -> requests.Response:
        return self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)

    @create_retry_decorator("web_scraper")
    def fetch_page(self, url: str, headers: Optional[dict] = None) -> str:
        """Fetch a page using requests."""
        try:
            response = self._rate_limited_get(url, headers=headers)
            response.raise_for_status()
            return response.text
        except requests.RequestException as exc:
            log.error(f"Failed to fetch {url}: {exc}")
            raise

    def fetch_page_js(self, url: str) -> str:
        """Fetch a page that requires JavaScript rendering."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            log.error("Playwright is required for JS-enabled scrapers.")
            raise RuntimeError("Playwright not installed for JS scraping.") from exc

        timeout_ms = REQUEST_TIMEOUT * 1000
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent=HEADERS.get("User-Agent"))
            page = context.new_page()
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            html = page.content()
            context.close()
            browser.close()
        return html

    def fetch(self, url: str, headers: Optional[dict] = None) -> str:
        """Fetch a page using the appropriate transport."""
        if self.requires_js:
            return self.fetch_page_js(url)
        return self.fetch_page(url, headers=headers)

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML into BeautifulSoup."""
        return BeautifulSoup(html, "lxml")

    def save_report(self, data: dict, filename: str) -> Path:
        """Write a JSON report to the output directory."""
        ensure_dir(self.output_dir)
        safe_name = sanitize_filename(filename)
        if not safe_name.lower().endswith(".json"):
            safe_name += ".json"
        path = self.output_dir / safe_name
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=True)
        log.info(f"Saved report to {path}")
        return path

    def handle_pagination(self, base_url: str, max_pages: int = 100) -> list[str]:
        """Follow next links (rel=next) to gather paginated URLs."""
        if "{page}" in base_url:
            return [base_url.format(page=page) for page in range(1, max_pages + 1)]

        urls: list[str] = []
        next_url = base_url
        for _ in range(max_pages):
            if not next_url or next_url in urls:
                break
            urls.append(next_url)
            try:
                html = self.fetch(next_url)
            except Exception:
                break
            soup = self.parse_html(html)
            next_anchor = (
                soup.find("a", rel="next")
                or soup.select_one("a.next")
                or soup.select_one("a[aria-label='Next']")
            )
            next_link = soup.find("link", rel="next")
            next_href = None
            if next_anchor and next_anchor.get("href"):
                next_href = next_anchor["href"]
            elif next_link and next_link.get("href"):
                next_href = next_link["href"]
            if not next_href:
                break
            next_url = urljoin(f"{self.base_url}/", next_href)
        return urls

    def build_payload(self, source: str, items: list[dict]) -> dict:
        """Standard payload envelope for saved reports."""
        return {
            "source": source,
            "count": len(items),
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "items": items,
        }

    def dedupe_items(self, items: list[dict], key: str = "url") -> list[dict]:
        """Remove duplicate items based on a key."""
        seen = set()
        deduped = []
        for item in items:
            value = item.get(key)
            if not value or value in seen:
                continue
            seen.add(value)
            deduped.append(item)
        return deduped
