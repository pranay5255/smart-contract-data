# Smart Contract Security Data Collection - Architecture Plan

## Overview

A comprehensive Python-based data collection system for gathering smart contract security training data from 40+ public sources including audit reports, vulnerability datasets, exploit analyses, and educational materials.

---

## System Architecture

```
smart-contract-data/
├── crawlers/                    # Main Python package
│   ├── config/                  # Configuration management
│   │   ├── settings.py          # Global settings, API keys, paths
│   │   └── sources.yaml         # Data source definitions
│   │
│   ├── cloners/                 # GitHub repository handlers
│   │   ├── github_cloner.py     # Clone/update repos
│   │   └── submodule_handler.py # Handle nested submodules
│   │
│   ├── scrapers/                # Web scraping modules
│   │   ├── base_scraper.py      # Abstract base class
│   │   ├── audit_scrapers.py    # Code4rena, Sherlock, CodeHawks
│   │   ├── exploit_scrapers.py  # Rekt News, Trail of Bits
│   │   └── docs_scrapers.py     # OWASP, SWC, Consensys
│   │
│   ├── downloaders/             # Dataset download handlers
│   │   ├── kaggle_downloader.py # Kaggle datasets
│   │   └── hf_downloader.py     # HuggingFace datasets
│   │
│   ├── processors/              # Data processing pipeline
│   │   ├── normalizer.py        # Standardize formats
│   │   ├── extractor.py         # Extract vulnerabilities
│   │   ├── deduplicator.py      # Remove duplicates
│   │   └── indexer.py           # Build searchable index
│   │
│   ├── utils/                   # Shared utilities
│   │   ├── logger.py            # Logging configuration
│   │   ├── helpers.py           # Common functions
│   │   └── rate_limiter.py      # API rate limiting
│   │
│   ├── orchestrator.py          # Main workflow coordinator
│   └── cli.py                   # Command-line interface
│
├── tests/                       # Test suite
│   ├── conftest.py              # Pytest fixtures
│   ├── test_config.py           # Config tests
│   ├── test_cloners.py          # Cloner tests
│   ├── test_scrapers.py         # Scraper tests
│   ├── test_downloaders.py      # Downloader tests
│   ├── test_processors.py       # Processor tests
│   └── test_utils.py            # Utility tests
│
├── scripts/                     # Manual verification scripts
│   ├── verify_cloner.sh         # Test GitHub cloning
│   ├── verify_scraper.sh        # Test web scraping
│   └── verify_all.sh            # Full system test
│
├── output/                      # Collected data storage
│   ├── repos/                   # Cloned GitHub repositories
│   ├── reports/                 # Scraped audit reports
│   ├── datasets/                # Downloaded datasets
│   ├── exploits/                # Exploit write-ups
│   └── processed/               # Normalized output
│
├── data/                        # Additional local data
├── defihackLabs/                # Git submodule
├── dataSorucesReport.md         # Source research document
├── SplitPlan.md                 # This architecture document
└── README.md                    # Implementation guide
```

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                             │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  GitHub Repos   │  Web Platforms  │  Dataset Platforms          │
│  (25+ repos)    │  (10+ sites)    │  (Kaggle, HuggingFace)      │
└────────┬────────┴────────┬────────┴──────────────┬──────────────┘
         │                 │                       │
         ▼                 ▼                       ▼
┌─────────────────┬─────────────────┬─────────────────────────────┐
│  GitHubCloner   │  WebScrapers    │  DatasetDownloaders         │
│  - clone_repo() │  - fetch_page() │  - download_kaggle()        │
│  - update_repo()│  - parse_html() │  - download_huggingface()   │
└────────┬────────┴────────┬────────┴──────────────┬──────────────┘
         │                 │                       │
         └─────────────────┼───────────────────────┘
                           ▼
              ┌────────────────────────┐
              │     RAW OUTPUT         │
              │  repos/ reports/       │
              │  datasets/ exploits/   │
              └───────────┬────────────┘
                          ▼
              ┌────────────────────────┐
              │     PROCESSORS         │
              │  - Normalizer          │
              │  - Extractor           │
              │  - Deduplicator        │
              │  - Indexer             │
              └───────────┬────────────┘
                          ▼
              ┌────────────────────────┐
              │   PROCESSED OUTPUT     │
              │  - vulnerabilities.jsonl│
              │  - audits.jsonl        │
              │  - index.sqlite        │
              └────────────────────────┘
```

---

## Module Specifications

### 1. Configuration Layer (`config/`)

| File | Purpose | Status |
|------|---------|--------|
| `settings.py` | Environment variables, API keys, paths, rate limits | Done |
| `sources.yaml` | Declarative source definitions with URLs, priorities | Done |

### 2. GitHub Cloners (`cloners/`)

| Module | Purpose | Status |
|--------|---------|--------|
| `github_cloner.py` | Clone/update repositories with rate limiting | Done |
| `submodule_handler.py` | Handle nested git submodules | Pending |

### 3. Web Scrapers (`scrapers/`)

| Module | Purpose | Status |
|--------|---------|--------|
| `base_scraper.py` | Abstract base with common logic | Pending |
| `audit_scrapers.py` | Code4rena, Sherlock, CodeHawks, Solodit | Pending |
| `exploit_scrapers.py` | Rekt News, Trail of Bits, Immunefi | Pending |
| `docs_scrapers.py` | OWASP, SWC Registry, Consensys | Pending |

### 4. Dataset Downloaders (`downloaders/`)

| Module | Purpose | Status |
|--------|---------|--------|
| `kaggle_downloader.py` | Kaggle dataset downloads | Pending |
| `hf_downloader.py` | HuggingFace dataset downloads | Pending |

### 5. Data Processors (`processors/`)

| Module | Purpose | Status |
|--------|---------|--------|
| `normalizer.py` | Convert formats to unified JSONL | Pending |
| `extractor.py` | Extract vulnerabilities, findings | Pending |
| `deduplicator.py` | Remove duplicate contracts/reports | Pending |
| `indexer.py` | Build SQLite index for queries | Pending |

### 6. Utilities (`utils/`)

| Module | Purpose | Status |
|--------|---------|--------|
| `logger.py` | Loguru-based logging | Done |
| `helpers.py` | Common helper functions | Done |
| `rate_limiter.py` | API rate limiting decorators | Pending |

---

## Data Sources Summary

| Category | Count | Examples |
|----------|-------|----------|
| GitHub Audit Repos | 13 | Pashov, Cyfrin, Sherlock, SigP |
| GitHub Datasets | 7 | SmartBugs, SolidiFI, Tintinweb |
| GitHub Educational | 5 | RareSkills, OpenZeppelin |
| GitHub Aggregators | 5 | Awesome lists |
| Web Audit Platforms | 4 | Code4rena, Sherlock, CodeHawks |
| Web Exploit Sites | 3 | Rekt News, Trail of Bits |
| Dataset Platforms | 3 | Kaggle (2), HuggingFace (1) |
| **Total** | **40+** | |

---

## Output Schema

```json
{
  "id": "unique-hash",
  "source": "code4rena",
  "type": "vulnerability",
  "severity": "high",
  "title": "Reentrancy in withdraw()",
  "description": "...",
  "code_snippet": "...",
  "file_path": "...",
  "tags": ["reentrancy", "defi"],
  "timestamp": "2024-01-15T00:00:00Z"
}
```

---

## Rate Limits

| Service | Limit | Strategy |
|---------|-------|----------|
| GitHub API | 5000/hour (auth) | Token rotation |
| Web scraping | 10 req/min | Sleep + retry |
| Kaggle | 5 downloads/min | Queue-based |
| HuggingFace | 10 req/min | Token bucket |

---

## Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Foundation (structure, config, utils) | Done |
| 2 | GitHub Cloners | Done |
| 3 | Web Scrapers | Pending |
| 4 | Dataset Downloaders | Pending |
| 5 | Data Processors | Pending |
| 6 | CLI & Orchestrator | Pending |
| 7 | Testing & Documentation | In Progress |
