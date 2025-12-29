"""
Audit platform scrapers.
"""
from __future__ import annotations

from typing import Optional
from urllib.parse import urljoin, urlparse

from config.settings import REPORTS_DIR
from utils.helpers import ensure_dir
from utils.logger import log

from .base_scraper import BaseScraper


def _is_same_host(url: str, base_url: str) -> bool:
    base_host = urlparse(base_url).netloc
    host = urlparse(url).netloc
    return not host or host == base_host


def _extract_links(soup, base_url: str, include_substrings: Optional[list[str]] = None) -> list[dict]:
    items = []
    for link in soup.select("a[href]"):
        href = link.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        href_lower = href.lower()
        if include_substrings and not any(sub in href_lower for sub in include_substrings):
            continue
        url = urljoin(f"{base_url}/", href)
        if not _is_same_host(url, base_url):
            continue
        title = link.get_text(strip=True) or link.get("aria-label") or link.get("title")
        if not title:
            continue
        items.append({"title": title, "url": url})
    return items


class Code4renaScraper(BaseScraper):
    """Scrape Code4rena audit reports."""

    SOURCE = "code4rena"
    ENDPOINTS = ["/reports", "/audits"]

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "audits" / self.SOURCE)
        super().__init__(base_url="https://code4rena.com", output_dir=output_dir, requires_js=False)

    def scrape(self) -> list[dict]:
        items: list[dict] = []
        for endpoint in self.ENDPOINTS:
            url = self.build_url(endpoint)
            try:
                html = self.fetch(url)
            except Exception as exc:
                log.warning(f"{self.SOURCE}: failed to fetch {url}: {exc}")
                continue
            soup = self.parse_html(html)
            links = _extract_links(soup, self.base_url, include_substrings=["/reports", "/audits"])
            for link in links:
                link.update({"source": self.SOURCE, "category": "audit", "endpoint": endpoint})
            items.extend(links)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_audits")
        return items


class SherlockScraper(BaseScraper):
    """Scrape Sherlock contest reports."""

    SOURCE = "sherlock"
    ENDPOINTS = ["/contests"]

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "audits" / self.SOURCE)
        super().__init__(base_url="https://audits.sherlock.xyz", output_dir=output_dir, requires_js=True)

    def scrape(self) -> list[dict]:
        items: list[dict] = []
        for endpoint in self.ENDPOINTS:
            url = self.build_url(endpoint)
            try:
                html = self.fetch(url)
            except Exception as exc:
                log.warning(f"{self.SOURCE}: failed to fetch {url}: {exc}")
                continue
            soup = self.parse_html(html)
            links = _extract_links(soup, self.base_url, include_substrings=["/contests"])
            for link in links:
                link.update({"source": self.SOURCE, "category": "audit", "endpoint": endpoint})
            items.extend(links)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_audits")
        return items


class CodeHawksScraper(BaseScraper):
    """Scrape CodeHawks contest listings."""

    SOURCE = "codehawks"
    ENDPOINTS = ["/c/"]

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "audits" / self.SOURCE)
        super().__init__(base_url="https://codehawks.cyfrin.io", output_dir=output_dir, requires_js=True)

    def scrape(self) -> list[dict]:
        items: list[dict] = []
        for endpoint in self.ENDPOINTS:
            url = self.build_url(endpoint)
            try:
                html = self.fetch(url)
            except Exception as exc:
                log.warning(f"{self.SOURCE}: failed to fetch {url}: {exc}")
                continue
            soup = self.parse_html(html)
            links = _extract_links(soup, self.base_url, include_substrings=["/c/"])
            for link in links:
                link.update({"source": self.SOURCE, "category": "audit", "endpoint": endpoint})
            items.extend(links)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_audits")
        return items


class SoloditScraper(BaseScraper):
    """Scrape Solodit vulnerability reports."""

    SOURCE = "solodit"
    ENDPOINTS = ["/"]

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "audits" / self.SOURCE)
        super().__init__(base_url="https://solodit.xyz", output_dir=output_dir, requires_js=True)

    def scrape(self) -> list[dict]:
        items: list[dict] = []
        include_terms = ["/report", "/audit", "/finding", "/contest"]
        for endpoint in self.ENDPOINTS:
            url = self.build_url(endpoint)
            try:
                html = self.fetch(url)
            except Exception as exc:
                log.warning(f"{self.SOURCE}: failed to fetch {url}: {exc}")
                continue
            soup = self.parse_html(html)
            links = _extract_links(soup, self.base_url, include_substrings=include_terms)
            for link in links:
                link.update({"source": self.SOURCE, "category": "audit", "endpoint": endpoint})
            items.extend(links)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_audits")
        return items
