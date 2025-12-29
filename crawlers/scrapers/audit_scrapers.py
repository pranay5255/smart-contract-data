"""
Audit platform scrapers.

Per scraper.md requirements:
- Extract all text content from JS pages, especially markdown
- Download PDFs if available and store in separate folder
- Store raw HTML/JSON for traceability
"""
from __future__ import annotations

import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from config.settings import REPORTS_DIR
from utils.helpers import ensure_dir
from utils.logger import log

from .base_scraper import BaseScraper


def _is_same_host(url: str, base_url: str) -> bool:
    """Check if URL belongs to the same host as base_url."""
    base_host = urlparse(base_url).netloc
    host = urlparse(url).netloc
    return not host or host == base_host


def _extract_links(
    soup,
    base_url: str,
    include_substrings: Optional[list[str]] = None,
    exclude_substrings: Optional[list[str]] = None,
) -> list[dict]:
    """Extract links matching criteria from parsed HTML."""
    items = []
    seen_urls = set()
    exclude_substrings = exclude_substrings or []

    for link in soup.select("a[href]"):
        href = link.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue

        href_lower = href.lower()

        # Check inclusion
        if include_substrings and not any(sub in href_lower for sub in include_substrings):
            continue

        # Check exclusion
        if any(sub in href_lower for sub in exclude_substrings):
            continue

        url = urljoin(f"{base_url}/", href)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        if not _is_same_host(url, base_url):
            continue

        title = link.get_text(strip=True) or link.get("aria-label") or link.get("title")
        if not title:
            continue

        items.append({"title": title, "url": url})

    return items


class Code4renaScraper(BaseScraper):
    """
    Scrape Code4rena audit reports.

    Code4rena hosts competitive audits with reports in markdown format.
    Reports are typically at /reports/{contest-name}
    """

    SOURCE = "code4rena"
    ENDPOINTS = ["/reports"]
    REPORT_PATTERN = re.compile(r"/reports/[\w\-]+")

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "audits" / self.SOURCE)
        super().__init__(base_url="https://code4rena.com", output_dir=output_dir, requires_js=False)

    def _get_report_links(self, soup) -> list[dict]:
        """Extract report links from the reports page."""
        links = []
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if self.REPORT_PATTERN.search(href):
                url = urljoin(f"{self.base_url}/", href)
                title = link.get_text(strip=True)
                if title and url not in [l["url"] for l in links]:
                    links.append({"title": title, "url": url})
        return links

    def scrape(self) -> list[dict]:
        """Scrape all Code4rena reports with full content."""
        items: list[dict] = []

        for endpoint in self.ENDPOINTS:
            url = self.build_url(endpoint)
            log.info(f"{self.SOURCE}: Fetching {url}")

            try:
                html = self.fetch(url)
                self.save_raw_html(html, url, prefix="listing")
            except Exception as exc:
                log.warning(f"{self.SOURCE}: failed to fetch {url}: {exc}")
                continue

            soup = self.parse_html(html)
            links = self._get_report_links(soup)
            log.info(f"{self.SOURCE}: Found {len(links)} report links")

            # Scrape each report detail page
            for link_info in links:
                detail = self.scrape_detail_page(link_info["url"])
                detail.update({
                    "source": self.SOURCE,
                    "category": "audit",
                    "listing_title": link_info["title"],
                })

                # Download any PDFs found
                for pdf_url in detail.get("pdf_links", []):
                    pdf_path = self.download_pdf(pdf_url)
                    if pdf_path:
                        detail.setdefault("downloaded_pdfs", []).append(str(pdf_path))

                items.append(detail)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_audits")
        log.info(f"{self.SOURCE}: Scraped {len(items)} reports")
        return items


class SherlockScraper(BaseScraper):
    """
    Scrape Sherlock contest reports.

    Sherlock requires JS rendering. Contest pages contain judging reports
    and findings in markdown format.
    """

    SOURCE = "sherlock"
    ENDPOINTS = ["/contests"]

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "audits" / self.SOURCE)
        super().__init__(base_url="https://audits.sherlock.xyz", output_dir=output_dir, requires_js=True)

    def _get_contest_links(self, soup) -> list[dict]:
        """Extract contest links from the listing page."""
        links = []
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if "/contests/" in href and href != "/contests/":
                url = urljoin(f"{self.base_url}/", href)
                title = link.get_text(strip=True)
                if title and len(title) > 2 and url not in [l["url"] for l in links]:
                    links.append({"title": title, "url": url})
        return links

    def scrape(self) -> list[dict]:
        """Scrape all Sherlock contest reports with full content."""
        items: list[dict] = []

        for endpoint in self.ENDPOINTS:
            url = self.build_url(endpoint)
            log.info(f"{self.SOURCE}: Fetching {url}")

            try:
                html = self.fetch(url)
                self.save_raw_html(html, url, prefix="listing")
            except Exception as exc:
                log.warning(f"{self.SOURCE}: failed to fetch {url}: {exc}")
                continue

            soup = self.parse_html(html)
            links = self._get_contest_links(soup)
            log.info(f"{self.SOURCE}: Found {len(links)} contest links")

            # Scrape each contest detail page
            for link_info in links:
                detail = self.scrape_detail_page(link_info["url"])
                detail.update({
                    "source": self.SOURCE,
                    "category": "audit",
                    "listing_title": link_info["title"],
                })

                # Download any PDFs found
                for pdf_url in detail.get("pdf_links", []):
                    pdf_path = self.download_pdf(pdf_url)
                    if pdf_path:
                        detail.setdefault("downloaded_pdfs", []).append(str(pdf_path))

                items.append(detail)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_audits")
        log.info(f"{self.SOURCE}: Scraped {len(items)} contests")
        return items


class CodeHawksScraper(BaseScraper):
    """
    Scrape CodeHawks contest listings.

    CodeHawks (Cyfrin) requires JS rendering. Contains competitive audits
    with detailed findings.
    """

    SOURCE = "codehawks"
    CONTEST_PATTERN = re.compile(r"/contests/[\w\-]+")

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "audits" / self.SOURCE)
        super().__init__(base_url="https://codehawks.cyfrin.io", output_dir=output_dir, requires_js=True)

    def _get_contest_links(self, soup) -> list[dict]:
        """Extract contest links from the listing page."""
        links = []
        for link in soup.select("a[href]"):
            href = link.get("href", "")
            if self.CONTEST_PATTERN.search(href) or "/c/" in href:
                url = urljoin(f"{self.base_url}/", href)
                title = link.get_text(strip=True)
                # Skip navigation links
                if title and len(title) > 2 and url not in [l["url"] for l in links]:
                    links.append({"title": title, "url": url})
        return links

    def scrape(self) -> list[dict]:
        """Scrape all CodeHawks contest listings with full content."""
        items: list[dict] = []

        # Main contests page
        url = self.build_url("/contests")
        log.info(f"{self.SOURCE}: Fetching {url}")

        try:
            html = self.fetch(url)
            self.save_raw_html(html, url, prefix="listing")
        except Exception as exc:
            log.warning(f"{self.SOURCE}: failed to fetch {url}: {exc}")
            return items

        soup = self.parse_html(html)
        links = self._get_contest_links(soup)
        log.info(f"{self.SOURCE}: Found {len(links)} contest links")

        # Scrape each contest detail page
        for link_info in links:
            detail = self.scrape_detail_page(link_info["url"])
            detail.update({
                "source": self.SOURCE,
                "category": "audit",
                "listing_title": link_info["title"],
            })

            # Download any PDFs found
            for pdf_url in detail.get("pdf_links", []):
                pdf_path = self.download_pdf(pdf_url)
                if pdf_path:
                    detail.setdefault("downloaded_pdfs", []).append(str(pdf_path))

            items.append(detail)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_audits")
        log.info(f"{self.SOURCE}: Scraped {len(items)} contests")
        return items


class SoloditScraper(BaseScraper):
    """
    Scrape Solodit vulnerability reports.

    Solodit aggregates findings from multiple audit platforms.
    Heavy JS rendering required. Contains 49,956+ results.
    """

    SOURCE = "solodit"
    FINDING_PATTERN = re.compile(r"/(issues|findings|checklist)/")

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "audits" / self.SOURCE)
        super().__init__(base_url="https://solodit.xyz", output_dir=output_dir, requires_js=True)

    def _get_finding_links(self, soup) -> list[dict]:
        """Extract finding/issue links from the page."""
        links = []
        include_terms = ["/issues/", "/findings/", "/checklist/", "/report/"]

        for link in soup.select("a[href]"):
            href = link.get("href", "").lower()
            if not any(term in href for term in include_terms):
                continue

            url = urljoin(f"{self.base_url}/", link.get("href", ""))
            title = link.get_text(strip=True)

            if title and len(title) > 2 and url not in [l["url"] for l in links]:
                links.append({"title": title, "url": url})

        return links

    def scrape(self) -> list[dict]:
        """Scrape Solodit findings with full content."""
        items: list[dict] = []

        # Main page
        url = self.base_url
        log.info(f"{self.SOURCE}: Fetching {url}")

        try:
            html = self.fetch(url)
            self.save_raw_html(html, url, prefix="listing")
        except Exception as exc:
            log.warning(f"{self.SOURCE}: failed to fetch {url}: {exc}")
            return items

        soup = self.parse_html(html)
        links = self._get_finding_links(soup)
        log.info(f"{self.SOURCE}: Found {len(links)} finding links")

        # Limit to first 100 for initial scrape (site has 49k+ results)
        links = links[:100]

        # Scrape each finding detail page
        for link_info in links:
            detail = self.scrape_detail_page(link_info["url"])
            detail.update({
                "source": self.SOURCE,
                "category": "audit",
                "listing_title": link_info["title"],
            })

            # Download any PDFs found
            for pdf_url in detail.get("pdf_links", []):
                pdf_path = self.download_pdf(pdf_url)
                if pdf_path:
                    detail.setdefault("downloaded_pdfs", []).append(str(pdf_path))

            items.append(detail)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_audits")
        log.info(f"{self.SOURCE}: Scraped {len(items)} findings")
        return items


# Convenience function to run all audit scrapers
def scrape_all_audits() -> dict[str, list[dict]]:
    """Run all audit platform scrapers and return combined results."""
    scrapers = [
        Code4renaScraper(),
        SherlockScraper(),
        CodeHawksScraper(),
        SoloditScraper(),
    ]

    results = {}
    for scraper in scrapers:
        try:
            log.info(f"Running {scraper.SOURCE} scraper...")
            results[scraper.SOURCE] = scraper.scrape()
        except Exception as exc:
            log.error(f"Failed to run {scraper.SOURCE} scraper: {exc}")
            results[scraper.SOURCE] = []

    return results
