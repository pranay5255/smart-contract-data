"""
Web scrapers for audit platforms, exploit analysis, and documentation.
"""
from .base_scraper import BaseScraper
from .audit_scrapers import (
    Code4renaScraper,
    SherlockScraper,
    CodeHawksScraper,
    SoloditScraper,
    scrape_all_audits,
)
from .docs_scrapers import (
    SWCRegistryScraper,
    OWASPScraper,
    ConsensusBestPracticesScraper,
    scrape_all_docs,
)
from .exploit_scrapers import (
    RektNewsScraper,
    TrailOfBitsScraper,
    ImmunefiScraper,
    scrape_all_exploits,
)

__all__ = [
    # Base
    "BaseScraper",
    # Audit scrapers
    "Code4renaScraper",
    "SherlockScraper",
    "CodeHawksScraper",
    "SoloditScraper",
    "scrape_all_audits",
    # Exploit scrapers
    "RektNewsScraper",
    "TrailOfBitsScraper",
    "ImmunefiScraper",
    "scrape_all_exploits",
    # Documentation scrapers
    "SWCRegistryScraper",
    "OWASPScraper",
    "ConsensusBestPracticesScraper",
    "scrape_all_docs",
]
