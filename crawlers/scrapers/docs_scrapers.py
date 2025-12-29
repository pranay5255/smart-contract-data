"""
Documentation scrapers.
"""
from __future__ import annotations

from urllib.parse import urljoin

from config.settings import REPORTS_DIR
from utils.helpers import ensure_dir
from utils.logger import log

from .base_scraper import BaseScraper


def _extract_swc_links(soup, base_url: str) -> list[dict]:
    items = []
    for link in soup.select("a[href]"):
        href = link.get("href", "").strip()
        text = link.get_text(strip=True)
        if not href or not text:
            continue
        if "SWC-" not in text.upper() and "SWC-" not in href.upper():
            continue
        url = urljoin(f"{base_url}/", href)
        items.append({"title": text, "url": url})
    return items


def _extract_section_links(soup, base_url: str) -> list[dict]:
    items = []
    for heading in soup.select("h2[id], h3[id]"):
        section_id = heading.get("id")
        title = heading.get_text(strip=True)
        if not section_id or not title:
            continue
        url = f"{base_url}#{section_id}"
        items.append({"title": title, "url": url})
    return items


class SWCRegistryScraper(BaseScraper):
    """Scrape SWC Registry entries."""

    SOURCE = "swc_registry"
    ENDPOINTS = ["/"]

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "docs" / self.SOURCE)
        super().__init__(base_url="https://swcregistry.io", output_dir=output_dir, requires_js=False)

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
            links = _extract_swc_links(soup, self.base_url)
            for link in links:
                link.update({"source": self.SOURCE, "category": "docs", "endpoint": endpoint})
            items.extend(links)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_docs")
        return items


class OWASPScraper(BaseScraper):
    """Scrape OWASP Smart Contract Top 10 sections."""

    SOURCE = "owasp_sc_top10"
    ENDPOINTS = ["/"]

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "docs" / self.SOURCE)
        super().__init__(
            base_url="https://owasp.org/www-project-smart-contract-top-10",
            output_dir=output_dir,
            requires_js=False,
        )

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
            links = _extract_section_links(soup, self.base_url)
            for link in links:
                link.update({"source": self.SOURCE, "category": "docs", "endpoint": endpoint})
            items.extend(links)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_docs")
        return items
