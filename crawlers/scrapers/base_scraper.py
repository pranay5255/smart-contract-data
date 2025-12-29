"""
Base scraper utilities for web sources.

Per scraper.md requirements:
- Extract all text content from JS pages, especially markdown
- Download PDFs if available and store in separate folder
- Store raw HTML/JSON for traceability
"""
from __future__ import annotations

import hashlib
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

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
        self.raw_dir = ensure_dir(output_dir / "raw")  # Store raw HTML/JSON
        self.pdf_dir = ensure_dir(output_dir / "pdfs")  # Store downloaded PDFs
        self.requires_js = requires_js
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._playwright_browser = None

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Return a list of scraped records."""
        raise NotImplementedError

    def build_url(self, endpoint: str) -> str:
        """Join the base URL with an endpoint."""
        return urljoin(f"{self.base_url}/", endpoint.lstrip("/"))

    @sleep_and_retry
    @limits(calls=RATE_LIMITS["web_scraper"]["calls"], period=RATE_LIMITS["web_scraper"]["period"])
    def _rate_limited_get(self, url: str, headers: Optional[dict] = None, stream: bool = False) -> requests.Response:
        return self.session.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=stream)

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

    def fetch_page_js(self, url: str, wait_for_selector: Optional[str] = None) -> str:
        """Fetch a page that requires JavaScript rendering using Playwright."""
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
            try:
                page.goto(url, wait_until="networkidle", timeout=timeout_ms)
                if wait_for_selector:
                    page.wait_for_selector(wait_for_selector, timeout=timeout_ms // 2)
                # Extra wait for dynamic content
                page.wait_for_timeout(2000)
                html = page.content()
            finally:
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

    def save_raw_html(self, html: str, url: str, prefix: str = "") -> Path:
        """Save raw HTML for traceability."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        filename = f"{prefix}_{url_hash}.html" if prefix else f"{url_hash}.html"
        safe_name = sanitize_filename(filename)
        path = self.raw_dir / safe_name
        with open(path, "w", encoding="utf-8") as f:
            f.write(html)
        log.debug(f"Saved raw HTML: {path}")
        return path

    def save_raw_json(self, data: dict, url: str, prefix: str = "") -> Path:
        """Save raw JSON for traceability."""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        filename = f"{prefix}_{url_hash}.json" if prefix else f"{url_hash}.json"
        safe_name = sanitize_filename(filename)
        path = self.raw_dir / safe_name
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        log.debug(f"Saved raw JSON: {path}")
        return path

    def download_pdf(self, url: str, filename: Optional[str] = None) -> Optional[Path]:
        """Download a PDF file if available."""
        try:
            response = self._rate_limited_get(url, stream=True)
            response.raise_for_status()

            # Verify it's actually a PDF
            content_type = response.headers.get("content-type", "").lower()
            if "pdf" not in content_type and not url.lower().endswith(".pdf"):
                log.warning(f"URL {url} does not appear to be a PDF")
                return None

            if not filename:
                # Extract filename from URL or headers
                parsed = urlparse(url)
                filename = Path(parsed.path).name
                if not filename or not filename.lower().endswith(".pdf"):
                    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
                    filename = f"document_{url_hash}.pdf"

            safe_name = sanitize_filename(filename)
            path = self.pdf_dir / safe_name

            with open(path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            log.info(f"Downloaded PDF: {path}")
            return path

        except requests.RequestException as exc:
            log.warning(f"Failed to download PDF from {url}: {exc}")
            return None

    def extract_text_content(self, soup: BeautifulSoup) -> str:
        """Extract all meaningful text content from a page."""
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
            element.decompose()

        # Try to find main content area
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(class_=re.compile(r"(content|post|article|entry)", re.I))
            or soup.find(id=re.compile(r"(content|post|article|entry)", re.I))
            or soup.body
        )

        if not main_content:
            main_content = soup

        # Get text with preserved line breaks
        text = main_content.get_text(separator="\n", strip=True)

        # Clean up excessive whitespace
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(line for line in lines if line)

        return text

    def extract_markdown_content(self, soup: BeautifulSoup) -> str:
        """Extract and preserve markdown-like content from HTML."""
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()

        # Find main content
        main_content = (
            soup.find("main")
            or soup.find("article")
            or soup.find(class_=re.compile(r"(markdown|prose|content)", re.I))
            or soup.body
        )

        if not main_content:
            return self.extract_text_content(soup)

        # Convert to markdown-like format
        lines = []

        for element in main_content.descendants:
            if element.name == "h1":
                lines.append(f"\n# {element.get_text(strip=True)}\n")
            elif element.name == "h2":
                lines.append(f"\n## {element.get_text(strip=True)}\n")
            elif element.name == "h3":
                lines.append(f"\n### {element.get_text(strip=True)}\n")
            elif element.name == "h4":
                lines.append(f"\n#### {element.get_text(strip=True)}\n")
            elif element.name == "p":
                lines.append(f"\n{element.get_text(strip=True)}\n")
            elif element.name == "li":
                lines.append(f"- {element.get_text(strip=True)}")
            elif element.name == "pre" or element.name == "code":
                code_text = element.get_text()
                if "\n" in code_text:
                    lines.append(f"\n```\n{code_text}\n```\n")
                else:
                    lines.append(f"`{code_text}`")
            elif element.name == "blockquote":
                for line in element.get_text(strip=True).split("\n"):
                    lines.append(f"> {line}")

        # Clean up and join
        text = "\n".join(lines)
        # Remove excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def find_pdf_links(self, soup: BeautifulSoup) -> list[str]:
        """Find all PDF links on a page."""
        pdf_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if href.lower().endswith(".pdf"):
                full_url = urljoin(f"{self.base_url}/", href)
                pdf_links.append(full_url)
        return list(set(pdf_links))

    def save_report(self, data: dict, filename: str) -> Path:
        """Write a JSON report to the output directory."""
        ensure_dir(self.output_dir)
        safe_name = sanitize_filename(filename)
        if not safe_name.lower().endswith(".json"):
            safe_name += ".json"
        path = self.output_dir / safe_name
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
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
                or soup.select_one("a:contains('Next')")
                or soup.select_one("a:contains('→')")
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

    def scrape_detail_page(self, url: str, save_raw: bool = True) -> dict:
        """
        Scrape a detail page to extract full content.

        Returns dict with:
        - url: str
        - title: str
        - content: str (extracted text)
        - markdown: str (markdown-formatted content)
        - pdf_links: list[str]
        - raw_html_path: str (if save_raw=True)
        """
        try:
            html = self.fetch(url)
            soup = self.parse_html(html)

            # Extract title
            title_tag = soup.find("h1") or soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else ""

            # Extract content
            content = self.extract_text_content(soup)
            markdown = self.extract_markdown_content(soup)

            # Find PDF links
            pdf_links = self.find_pdf_links(soup)

            result = {
                "url": url,
                "title": title,
                "content": content,
                "markdown": markdown,
                "pdf_links": pdf_links,
            }

            # Save raw HTML for traceability
            if save_raw:
                raw_path = self.save_raw_html(html, url)
                result["raw_html_path"] = str(raw_path)

            return result

        except Exception as exc:
            log.error(f"Failed to scrape detail page {url}: {exc}")
            return {"url": url, "error": str(exc)}
