"""
Source Type Definitions

Base dataclasses and enums for different data source types.
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class SourceType(Enum):
    """Types of data sources."""
    GITHUB_REPO = "github_repo"
    WEB_SCRAPER = "web_scraper"
    KAGGLE_DATASET = "kaggle_dataset"
    HUGGINGFACE_DATASET = "huggingface_dataset"


class Priority(Enum):
    """Priority levels for data collection."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DataType(Enum):
    """Types of data that can be collected."""
    SOLIDITY = "solidity"
    MARKDOWN = "md"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    CSV = "csv"
    YAML = "yaml"
    LINKS = "links"
    CODE = "code"
    ARTICLES = "articles"


@dataclass
class BaseSource:
    """Base class for all data sources."""
    name: str
    source_type: SourceType
    data_types: list[str]
    priority: Priority = Priority.MEDIUM
    enabled: bool = True
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert source to dictionary."""
        return {
            "name": self.name,
            "source_type": self.source_type.value,
            "data_types": self.data_types,
            "priority": self.priority.value,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class GitHubSource(BaseSource):
    """GitHub repository source."""
    url: str = ""
    category: str = "general"
    subdirs: list[str] = field(default_factory=list)
    stats: Optional[str] = None
    clone_depth: int = 1
    include_submodules: bool = False

    def __post_init__(self):
        """Set source type."""
        self.source_type = SourceType.GITHUB_REPO

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            "url": self.url,
            "category": self.category,
            "subdirs": self.subdirs,
            "stats": self.stats,
            "clone_depth": self.clone_depth,
            "include_submodules": self.include_submodules,
        })
        return base


@dataclass
class WebScraperSource(BaseSource):
    """Web scraper source."""
    base_url: str = ""
    endpoints: list[str] = field(default_factory=list)
    category: str = "general"
    requires_js: bool = False
    pagination: bool = False
    max_pages: int = 100
    stats: Optional[str] = None

    def __post_init__(self):
        """Set source type."""
        self.source_type = SourceType.WEB_SCRAPER

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            "base_url": self.base_url,
            "endpoints": self.endpoints,
            "category": self.category,
            "requires_js": self.requires_js,
            "pagination": self.pagination,
            "max_pages": self.max_pages,
            "stats": self.stats,
        })
        return base


@dataclass
class KaggleSource(BaseSource):
    """Kaggle dataset source."""
    dataset_id: str = ""
    stats: Optional[str] = None

    def __post_init__(self):
        """Set source type."""
        self.source_type = SourceType.KAGGLE_DATASET

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            "dataset_id": self.dataset_id,
            "stats": self.stats,
        })
        return base


@dataclass
class HuggingFaceSource(BaseSource):
    """HuggingFace dataset source."""
    dataset_id: str = ""
    stats: Optional[str] = None
    split: str = "train"

    def __post_init__(self):
        """Set source type."""
        self.source_type = SourceType.HUGGINGFACE_DATASET

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            "dataset_id": self.dataset_id,
            "stats": self.stats,
            "split": self.split,
        })
        return base
