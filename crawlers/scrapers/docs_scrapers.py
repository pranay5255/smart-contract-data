"""
Documentation scrapers.

Per scraper.md requirements:
- Extract all text content from JS pages, especially markdown
- Download PDFs if available and store in separate folder
- Store raw HTML/JSON for traceability
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from config.settings import REPORTS_DIR
from utils.helpers import ensure_dir
from utils.logger import log

from .base_scraper import BaseScraper


def _extract_swc_entries(soup, base_url: str) -> list[dict]:
    """Extract SWC registry entries with details."""
    items = []
    seen = set()

    # Look for SWC-XXX patterns in links and text
    for link in soup.select("a[href]"):
        href = link.get("href", "").strip()
        text = link.get_text(strip=True)

        if not href or not text:
            continue

        # Check for SWC pattern
        swc_match = re.search(r"SWC[- ]?(\d+)", text, re.IGNORECASE)
        href_match = re.search(r"SWC[- ]?(\d+)", href, re.IGNORECASE)

        if not swc_match and not href_match:
            continue

        swc_id = swc_match.group(1) if swc_match else href_match.group(1)
        url = urljoin(f"{base_url}/", href)

        if url in seen:
            continue
        seen.add(url)

        items.append({
            "title": text,
            "url": url,
            "swc_id": f"SWC-{swc_id}",
        })

    return items


def _extract_documentation_links(soup, base_url: str, include_patterns: list[str] = None) -> list[dict]:
    """Extract documentation links with optional pattern filtering."""
    items = []
    seen = set()
    include_patterns = include_patterns or []

    for link in soup.select("a[href]"):
        href = link.get("href", "").strip()
        text = link.get_text(strip=True)

        if not href or not text:
            continue
        if href.startswith(("#", "mailto:", "javascript:")):
            continue

        # Check patterns
        if include_patterns:
            if not any(re.search(pattern, href, re.I) for pattern in include_patterns):
                continue

        url = urljoin(f"{base_url}/", href)
        if url in seen:
            continue
        seen.add(url)

        items.append({"title": text, "url": url})

    return items


class SWCRegistryScraper(BaseScraper):
    """
    Scrape SWC Registry entries.

    The Smart Contract Weakness Classification registry contains
    standardized vulnerability definitions for Solidity.
    """

    SOURCE = "swc_registry"
    ENDPOINTS = ["/"]

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "docs" / self.SOURCE)
        super().__init__(base_url="https://swcregistry.io", output_dir=output_dir, requires_js=False)

    def _get_swc_entries(self, soup) -> list[dict]:
        """Extract SWC entries from the registry page."""
        entries = _extract_swc_entries(soup, self.base_url)

        # Also look for table-based entries
        for row in soup.select("tr"):
            cells = row.select("td")
            if len(cells) >= 2:
                id_cell = cells[0]
                title_cell = cells[1]

                swc_match = re.search(r"SWC[- ]?(\d+)", id_cell.get_text())
                if swc_match:
                    swc_id = f"SWC-{swc_match.group(1)}"
                    title = title_cell.get_text(strip=True)

                    link = row.find("a", href=True)
                    url = self.base_url
                    if link:
                        url = urljoin(f"{self.base_url}/", link["href"])

                    if url not in [e["url"] for e in entries]:
                        entries.append({
                            "title": title or swc_id,
                            "url": url,
                            "swc_id": swc_id,
                        })

        return entries

    def scrape(self) -> list[dict]:
        """Scrape SWC Registry entries with full content."""
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
            entries = self._get_swc_entries(soup)
            log.info(f"{self.SOURCE}: Found {len(entries)} SWC entries")

            for entry in entries:
                if entry["url"] != self.base_url and entry["url"] != url:
                    detail = self.scrape_detail_page(entry["url"])
                    detail.update({
                        "source": self.SOURCE,
                        "category": "docs",
                        "swc_id": entry.get("swc_id"),
                        "listing_title": entry["title"],
                    })
                else:
                    detail = {
                        "source": self.SOURCE,
                        "category": "docs",
                        "swc_id": entry.get("swc_id"),
                        "title": entry["title"],
                        "url": entry["url"],
                    }

                items.append(detail)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_docs")
        log.info(f"{self.SOURCE}: Scraped {len(items)} SWC entries")
        return items


class OWASPScraper(BaseScraper):
    """
    Scrape OWASP Smart Contract Top 10 sections.

    OWASP maintains a top 10 list of smart contract vulnerabilities
    with detailed descriptions and mitigations.
    """

    SOURCE = "owasp_sc_top10"
    ENDPOINTS = ["/"]

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "docs" / self.SOURCE)
        super().__init__(
            base_url="https://owasp.org/www-project-smart-contract-top-10",
            output_dir=output_dir,
            requires_js=False,
        )

    def _get_top10_entries(self, soup) -> list[dict]:
        """Extract OWASP Top 10 entries."""
        entries = []
        seen = set()

        # Look for SC0X patterns (OWASP Smart Contract Top 10 format)
        for link in soup.select("a[href]"):
            href = link.get("href", "").strip()
            text = link.get_text(strip=True)

            if not href or not text:
                continue

            # Look for SC01-SC10 patterns
            sc_match = re.search(r"SC[- ]?(\d+)", text, re.IGNORECASE)
            if sc_match or re.search(r"SC\d+", href, re.IGNORECASE):
                url = urljoin(f"{self.base_url}/", href)
                if url in seen:
                    continue
                seen.add(url)

                sc_id = sc_match.group(1) if sc_match else None
                entries.append({
                    "title": text,
                    "url": url,
                    "sc_id": f"SC{sc_id:02d}" if sc_id else None,
                })

        # Also extract section headings with IDs
        for heading in soup.select("h2[id], h3[id]"):
            section_id = heading.get("id")
            title = heading.get_text(strip=True)

            if not section_id or not title:
                continue

            url = f"{self.base_url}#{section_id}"
            if url not in seen:
                seen.add(url)
                entries.append({
                    "title": title,
                    "url": url,
                    "section_id": section_id,
                })

        return entries

    def scrape(self) -> list[dict]:
        """Scrape OWASP Smart Contract Top 10 with full content."""
        items: list[dict] = []

        for endpoint in self.ENDPOINTS:
            url = self.build_url(endpoint)
            log.info(f"{self.SOURCE}: Fetching {url}")

            try:
                html = self.fetch(url)
                self.save_raw_html(html, url, prefix="main")
            except Exception as exc:
                log.warning(f"{self.SOURCE}: failed to fetch {url}: {exc}")
                continue

            soup = self.parse_html(html)

            # Extract full page content as it's a single-page doc
            page_detail = {
                "source": self.SOURCE,
                "category": "docs",
                "url": url,
                "title": "OWASP Smart Contract Top 10",
                "content": self.extract_text_content(soup),
                "markdown": self.extract_markdown_content(soup),
            }
            items.append(page_detail)

            # Also get individual entries
            entries = self._get_top10_entries(soup)
            log.info(f"{self.SOURCE}: Found {len(entries)} Top 10 entries")

            for entry in entries:
                # For anchor links on same page, extract that section
                if "#" in entry["url"]:
                    section_id = entry["url"].split("#")[-1]
                    section = soup.find(id=section_id)
                    if section:
                        content = section.get_text(separator="\n", strip=True)
                        items.append({
                            "source": self.SOURCE,
                            "category": "docs",
                            "url": entry["url"],
                            "title": entry["title"],
                            "content": content,
                            "sc_id": entry.get("sc_id"),
                            "section_id": entry.get("section_id"),
                        })
                elif entry["url"] != url:
                    # External link - scrape detail page
                    detail = self.scrape_detail_page(entry["url"])
                    detail.update({
                        "source": self.SOURCE,
                        "category": "docs",
                        "listing_title": entry["title"],
                        "sc_id": entry.get("sc_id"),
                    })
                    items.append(detail)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_docs")
        log.info(f"{self.SOURCE}: Scraped {len(items)} entries")
        return items


class ConsensusBestPracticesScraper(BaseScraper):
    """
    Scrape Consensys Smart Contract Best Practices guide.

    Comprehensive security best practices documentation.
    """

    SOURCE = "consensys_best_practices"
    ENDPOINTS = ["/"]

    def __init__(self, output_dir=None):
        output_dir = output_dir or ensure_dir(REPORTS_DIR / "docs" / self.SOURCE)
        super().__init__(
            base_url="https://consensys.github.io/smart-contract-best-practices",
            output_dir=output_dir,
            requires_js=False,
        )

    def scrape(self) -> list[dict]:
        """Scrape Consensys best practices documentation."""
        items: list[dict] = []

        url = self.base_url
        log.info(f"{self.SOURCE}: Fetching {url}")

        try:
            html = self.fetch(url)
            self.save_raw_html(html, url, prefix="main")
        except Exception as exc:
            log.warning(f"{self.SOURCE}: failed to fetch {url}: {exc}")
            return items

        soup = self.parse_html(html)

        # Get main page content
        main_detail = {
            "source": self.SOURCE,
            "category": "docs",
            "url": url,
            "title": "Smart Contract Best Practices",
            "content": self.extract_text_content(soup),
            "markdown": self.extract_markdown_content(soup),
        }
        items.append(main_detail)

        # Find navigation links to sub-pages
        nav_links = []
        for link in soup.select("nav a[href], .sidebar a[href], .toc a[href]"):
            href = link.get("href", "")
            if href and not href.startswith(("#", "http://", "https://")):
                text = link.get_text(strip=True)
                if text:
                    nav_links.append({
                        "title": text,
                        "url": urljoin(f"{self.base_url}/", href),
                    })

        log.info(f"{self.SOURCE}: Found {len(nav_links)} sub-pages")

        # Scrape sub-pages
        for link_info in nav_links:
            if link_info["url"] == url:
                continue
            detail = self.scrape_detail_page(link_info["url"])
            detail.update({
                "source": self.SOURCE,
                "category": "docs",
                "listing_title": link_info["title"],
            })
            items.append(detail)

        items = self.dedupe_items(items)
        self.save_report(self.build_payload(self.SOURCE, items), f"{self.SOURCE}_docs")
        log.info(f"{self.SOURCE}: Scraped {len(items)} pages")
        return items


# Convenience function to run all documentation scrapers
def scrape_all_docs() -> dict[str, list[dict]]:
    """Run all documentation scrapers and return combined results."""
    scrapers = [
        SWCRegistryScraper(),
        OWASPScraper(),
        ConsensusBestPracticesScraper(),
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
