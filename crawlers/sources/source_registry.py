"""
Source Registry

Loads and manages all data sources from configuration.
"""
from pathlib import Path
from typing import Optional

from sources.source_types import (
    GitHubSource,
    WebScraperSource,
    KaggleSource,
    HuggingFaceSource,
    Priority,
)
from utils.helpers import load_sources_config
from utils.logger import log


class SourceRegistry:
    """Registry for all data sources."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize registry with configuration."""
        self.config = load_sources_config(config_path)
        self._github_sources: dict[str, list[GitHubSource]] = {}
        self._web_sources: dict[str, list[WebScraperSource]] = {}
        self._kaggle_sources: list[KaggleSource] = []
        self._huggingface_sources: list[HuggingFaceSource] = []
        self._load_sources()

    def _load_sources(self):
        """Load all sources from configuration."""
        self._load_github_sources()
        self._load_web_sources()
        self._load_dataset_sources()

    def _load_github_sources(self):
        """Load GitHub repository sources."""
        github_config = self.config.get("github_repos", {})

        for category, repos in github_config.items():
            sources = []
            for repo in repos:
                source = GitHubSource(
                    name=repo.get("name", ""),
                    url=repo.get("url", ""),
                    category=category,
                    data_types=repo.get("data_types", []),
                    priority=Priority(repo.get("priority", "medium")),
                    subdirs=repo.get("subdirs", []),
                    stats=repo.get("stats"),
                )
                sources.append(source)

            self._github_sources[category] = sources
            log.debug(f"Loaded {len(sources)} GitHub sources for category: {category}")

    def _load_web_sources(self):
        """Load web scraper sources."""
        web_config = self.config.get("web_scrapers", {})

        for category, scrapers in web_config.items():
            sources = []
            for scraper in scrapers:
                source = WebScraperSource(
                    name=scraper.get("name", ""),
                    base_url=scraper.get("base_url", ""),
                    endpoints=scraper.get("endpoints", []),
                    category=category,
                    data_types=scraper.get("data_types", []),
                    priority=Priority(scraper.get("priority", "medium")),
                    requires_js=scraper.get("requires_js", False),
                    pagination=scraper.get("pagination", False),
                    stats=scraper.get("stats"),
                )
                sources.append(source)

            self._web_sources[category] = sources
            log.debug(f"Loaded {len(sources)} web sources for category: {category}")

    def _load_dataset_sources(self):
        """Load dataset download sources."""
        downloads_config = self.config.get("dataset_downloads", {})

        # Kaggle datasets
        for dataset in downloads_config.get("kaggle", []):
            source = KaggleSource(
                name=dataset.get("name", ""),
                dataset_id=dataset.get("dataset_id", ""),
                data_types=dataset.get("data_types", []),
                priority=Priority(dataset.get("priority", "medium")),
                stats=dataset.get("stats"),
            )
            self._kaggle_sources.append(source)

        log.debug(f"Loaded {len(self._kaggle_sources)} Kaggle sources")

        # HuggingFace datasets
        for dataset in downloads_config.get("huggingface", []):
            source = HuggingFaceSource(
                name=dataset.get("name", ""),
                dataset_id=dataset.get("dataset_id", ""),
                data_types=dataset.get("data_types", []),
                priority=Priority(dataset.get("priority", "medium")),
                stats=dataset.get("stats"),
            )
            self._huggingface_sources.append(source)

        log.debug(f"Loaded {len(self._huggingface_sources)} HuggingFace sources")

    # GitHub sources
    def get_github_sources(self, category: Optional[str] = None, priority: Optional[Priority] = None) -> list[GitHubSource]:
        """Get GitHub sources by category and/or priority."""
        if category:
            sources = self._github_sources.get(category, [])
        else:
            sources = [s for sources_list in self._github_sources.values() for s in sources_list]

        if priority:
            sources = [s for s in sources if s.priority == priority]

        return sources

    def get_github_categories(self) -> list[str]:
        """Get all GitHub source categories."""
        return list(self._github_sources.keys())

    # Web sources
    def get_web_sources(self, category: Optional[str] = None, priority: Optional[Priority] = None) -> list[WebScraperSource]:
        """Get web scraper sources by category and/or priority."""
        if category:
            sources = self._web_sources.get(category, [])
        else:
            sources = [s for sources_list in self._web_sources.values() for s in sources_list]

        if priority:
            sources = [s for s in sources if s.priority == priority]

        return sources

    def get_web_categories(self) -> list[str]:
        """Get all web scraper categories."""
        return list(self._web_sources.keys())

    # Dataset sources
    def get_kaggle_sources(self, priority: Optional[Priority] = None) -> list[KaggleSource]:
        """Get Kaggle sources by priority."""
        sources = self._kaggle_sources
        if priority:
            sources = [s for s in sources if s.priority == priority]
        return sources

    def get_huggingface_sources(self, priority: Optional[Priority] = None) -> list[HuggingFaceSource]:
        """Get HuggingFace sources by priority."""
        sources = self._huggingface_sources
        if priority:
            sources = [s for s in sources if s.priority == priority]
        return sources

    # Statistics
    def get_summary(self) -> dict:
        """Get summary of all sources."""
        return {
            "github": {
                "total": sum(len(sources) for sources in self._github_sources.values()),
                "by_category": {cat: len(sources) for cat, sources in self._github_sources.items()},
            },
            "web_scrapers": {
                "total": sum(len(sources) for sources in self._web_sources.values()),
                "by_category": {cat: len(sources) for cat, sources in self._web_sources.items()},
            },
            "datasets": {
                "kaggle": len(self._kaggle_sources),
                "huggingface": len(self._huggingface_sources),
            },
        }

    def print_summary(self):
        """Print a formatted summary of all sources."""
        summary = self.get_summary()

        print("\n" + "="*60)
        print("DATA SOURCES SUMMARY")
        print("="*60)

        print(f"\nGitHub Repositories: {summary['github']['total']}")
        for category, count in summary['github']['by_category'].items():
            print(f"  - {category}: {count}")

        print(f"\nWeb Scrapers: {summary['web_scrapers']['total']}")
        for category, count in summary['web_scrapers']['by_category'].items():
            print(f"  - {category}: {count}")

        print(f"\nDataset Downloads:")
        print(f"  - Kaggle: {summary['datasets']['kaggle']}")
        print(f"  - HuggingFace: {summary['datasets']['huggingface']}")

        print("\n" + "="*60 + "\n")
