"""
Sources Module

Data source definitions and registry for the smart contract security crawler.
"""
from sources.source_types import (
    BaseSource,
    GitHubSource,
    WebScraperSource,
    KaggleSource,
    HuggingFaceSource,
    SourceType,
    Priority,
    DataType,
)
from sources.source_registry import SourceRegistry

__all__ = [
    # Source types
    "BaseSource",
    "GitHubSource",
    "WebScraperSource",
    "KaggleSource",
    "HuggingFaceSource",
    # Enums
    "SourceType",
    "Priority",
    "DataType",
    # Registry
    "SourceRegistry",
]
