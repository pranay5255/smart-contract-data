# Product Requirements Document (PRD)
# Smart Contract Security Data Collection System

**Version:** 1.0
**Created:** 2025-12-27
**Status:** In Development (~25% complete)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Goals](#2-project-goals)
3. [Current State Assessment](#3-current-state-assessment)
4. [System Architecture](#4-system-architecture)
5. [Data Sources Inventory](#5-data-sources-inventory)
6. [Technical Specifications](#6-technical-specifications)
7. [Deliverables by Phase](#7-deliverables-by-phase)
8. [File Specifications](#8-file-specifications)
9. [Data Schemas](#9-data-schemas)
10. [Dependencies & Environment](#10-dependencies--environment)
11. [Rate Limiting Strategy](#11-rate-limiting-strategy)
12. [Testing Requirements](#12-testing-requirements)
13. [Risk Assessment](#13-risk-assessment)
14. [Acceptance Criteria](#14-acceptance-criteria)

---

## 1. Executive Summary

### 1.1 What This Project Is

A Python-based automated data collection system designed to aggregate smart contract security training data from 40+ public sources. The system clones GitHub repositories, scrapes web platforms, downloads datasets, and processes everything into a unified, searchable format.

### 1.2 Why This Exists

To create a comprehensive dataset for training ML models on smart contract security, including:
- Vulnerability detection
- Audit report analysis
- Exploit pattern recognition
- Security best practices

### 1.3 Target Output

- **~60,000+ Solidity smart contracts** (labeled and unlabeled)
- **~1,000+ audit reports** (PDF/MD format)
- **~500+ exploit write-ups** (structured analysis)
- **Unified JSONL dataset** with searchable SQLite index

---

## 2. Project Goals

### 2.1 Primary Objectives

| Objective | Success Metric |
|-----------|----------------|
| Clone all 26 GitHub repositories | 100% success rate, organized by category |
| Scrape all 12 web sources | Data from each platform collected |
| Download all 3 dataset platform sources | Kaggle + HuggingFace datasets acquired |
| Normalize to unified schema | All data converted to JSONL format |
| Build searchable index | SQLite database with full-text search |
| Provide CLI interface | Single command to run full pipeline |

### 2.2 Non-Goals (Out of Scope)

- Real-time monitoring of new audits
- Proprietary/paid audit report acquisition
- Smart contract bytecode decompilation
- Vulnerability detection ML model training (this is data collection only)

---

## 3. Current State Assessment

### 3.1 Implementation Status

```
COMPLETED (Phase 1-2):
├── config/settings.py          ✓ 66 lines - Environment, paths, rate limits
├── config/sources.yaml         ✓ 263 lines - All 41 sources defined
├── cloners/github_cloner.py    ✓ 227 lines - Full clone/update functionality
├── utils/helpers.py            ✓ 91 lines - Utility functions
├── utils/logger.py             ✓ 33 lines - Loguru logging setup
├── tests/conftest.py           ✓ 142 lines - Pytest fixtures
├── requirements.txt            ✓ 48 dependencies listed
└── README.md                   ✓ 290 lines - Documentation

NOT STARTED (Phase 3-7):
├── scrapers/                   ✗ Empty package (4 files needed)
├── downloaders/                ✗ Empty package (2 files needed)
├── processors/                 ✗ Empty package (4 files needed)
├── cli.py                      ✗ Not created
├── orchestrator.py             ✗ Not created
├── utils/rate_limiter.py       ✗ Not created
├── cloners/submodule_handler.py ✗ Not created
├── tests/test_*.py             ✗ No actual tests (6 files needed)
└── scripts/*.sh                ✗ Empty directory (3 files needed)
```

### 3.2 Lines of Code Summary

| Category | Lines | Files |
|----------|-------|-------|
| Implemented | ~820 | 7 |
| To Implement | ~2,500 (est.) | 20 |
| Total Estimated | ~3,300 | 27 |

---

## 4. System Architecture

### 4.1 Directory Structure

```
smart-contract-data/
├── crawlers/                    # Main Python package
│   ├── config/                  # Configuration management
│   │   ├── __init__.py
│   │   ├── settings.py          # Global settings, API keys, paths
│   │   └── sources.yaml         # Data source definitions (41 sources)
│   │
│   ├── cloners/                 # GitHub repository handlers
│   │   ├── __init__.py
│   │   ├── github_cloner.py     # Clone/update repos [DONE]
│   │   └── submodule_handler.py # Handle nested submodules [TODO]
│   │
│   ├── scrapers/                # Web scraping modules
│   │   ├── __init__.py
│   │   ├── base_scraper.py      # Abstract base class [TODO]
│   │   ├── audit_scrapers.py    # Code4rena, Sherlock, CodeHawks, Solodit [TODO]
│   │   ├── exploit_scrapers.py  # Rekt News, Trail of Bits, Immunefi [TODO]
│   │   └── docs_scrapers.py     # OWASP, SWC, Consensys, etc. [TODO]
│   │
│   ├── downloaders/             # Dataset download handlers
│   │   ├── __init__.py
│   │   ├── kaggle_downloader.py # Kaggle datasets [TODO]
│   │   └── hf_downloader.py     # HuggingFace datasets [TODO]
│   │
│   ├── processors/              # Data processing pipeline
│   │   ├── __init__.py
│   │   ├── normalizer.py        # Standardize formats [TODO]
│   │   ├── extractor.py         # Extract vulnerabilities [TODO]
│   │   ├── deduplicator.py      # Remove duplicates [TODO]
│   │   └── indexer.py           # Build searchable index [TODO]
│   │
│   ├── utils/                   # Shared utilities
│   │   ├── __init__.py
│   │   ├── logger.py            # Logging configuration [DONE]
│   │   ├── helpers.py           # Common functions [DONE]
│   │   └── rate_limiter.py      # API rate limiting [TODO]
│   │
│   ├── orchestrator.py          # Main workflow coordinator [TODO]
│   ├── cli.py                   # Command-line interface [TODO]
│   └── requirements.txt         # Dependencies [DONE]
│
├── tests/                       # Test suite
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures [DONE]
│   ├── test_config.py           # [TODO]
│   ├── test_cloners.py          # [TODO]
│   ├── test_scrapers.py         # [TODO]
│   ├── test_downloaders.py      # [TODO]
│   ├── test_processors.py       # [TODO]
│   └── test_utils.py            # [TODO]
│
├── scripts/                     # Verification scripts
│   ├── verify_cloner.sh         # [TODO]
│   ├── verify_scraper.sh        # [TODO]
│   └── verify_all.sh            # [TODO]
│
├── output/                      # Collected data storage
│   ├── repos/                   # Cloned GitHub repositories
│   │   ├── aggregators/
│   │   ├── audit_repos/
│   │   ├── vulnerability_datasets/
│   │   └── educational/
│   ├── reports/                 # Scraped audit reports
│   ├── datasets/                # Downloaded datasets
│   ├── exploits/                # Exploit write-ups
│   └── processed/               # Normalized output
│       ├── vulnerabilities.jsonl
│       ├── audits.jsonl
│       ├── exploits.jsonl
│       └── index.sqlite
│
├── CLAUDE.md                    # AI assistant guidance
├── PRD.md                       # This document
├── SplitPlan.md                 # Architecture plan
├── dataSorucesReport.md         # Data sources research
├── README.md                    # User documentation
└── pytest.ini                   # Test configuration
```

### 4.2 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              INPUT LAYER                                 │
├────────────────────┬────────────────────┬───────────────────────────────┤
│   GitHub Repos     │   Web Platforms    │   Dataset Platforms           │
│   (26 repos)       │   (12 sites)       │   (3 sources)                 │
│                    │                    │                               │
│ • Audit reports    │ • Code4rena        │ • Kaggle (2 datasets)         │
│ • Vulnerability    │ • Sherlock         │ • HuggingFace (1 dataset)     │
│   datasets         │ • CodeHawks        │                               │
│ • Educational      │ • Solodit          │                               │
│   materials        │ • Rekt News        │                               │
│ • Awesome lists    │ • Trail of Bits    │                               │
└────────┬───────────┴────────┬───────────┴───────────────┬───────────────┘
         │                    │                           │
         ▼                    ▼                           ▼
┌────────────────────┬────────────────────┬───────────────────────────────┐
│   GitHubCloner     │   WebScrapers      │   DatasetDownloaders          │
│                    │                    │                               │
│ • clone_repo()     │ • BaseScraper      │ • KaggleDownloader            │
│ • update_repo()    │ • AuditScrapers    │ • HuggingFaceDownloader       │
│ • clone_all()      │ • ExploitScrapers  │                               │
│                    │ • DocsScrapers     │                               │
│ Rate: 30/min       │ Rate: 10/min       │ Rate: 5/min                   │
└────────┬───────────┴────────┬───────────┴───────────────┬───────────────┘
         │                    │                           │
         └────────────────────┼───────────────────────────┘
                              │
                              ▼
                 ┌────────────────────────┐
                 │      RAW OUTPUT        │
                 │                        │
                 │  output/repos/         │
                 │  output/reports/       │
                 │  output/datasets/      │
                 │  output/exploits/      │
                 └───────────┬────────────┘
                             │
                             ▼
                 ┌────────────────────────┐
                 │      PROCESSORS        │
                 │                        │
                 │  1. Normalizer         │ → Unified JSONL format
                 │  2. Extractor          │ → Pull vuln/findings
                 │  3. Deduplicator       │ → MD5-based dedup
                 │  4. Indexer            │ → SQLite FTS index
                 └───────────┬────────────┘
                             │
                             ▼
                 ┌────────────────────────┐
                 │   PROCESSED OUTPUT     │
                 │                        │
                 │  • vulnerabilities.jsonl│
                 │  • audits.jsonl        │
                 │  • exploits.jsonl      │
                 │  • index.sqlite        │
                 └────────────────────────┘
```

---

## 5. Data Sources Inventory

### 5.1 GitHub Repositories (26 total)

#### 5.1.1 Aggregators (4 repos)

| Name | URL | Priority | Data Types |
|------|-----|----------|------------|
| Awesome Smart Contract Security (Saeidshirazi) | https://github.com/saeidshirazi/Awesome-Smart-Contract-Security | HIGH | MD, links |
| Awesome Smart Contract Security (Moeinfatehi) | https://github.com/moeinfatehi/Awesome-Smart-Contract-Security | HIGH | MD, articles |
| Awesome Ethereum Security (Crytic) | https://github.com/crytic/awesome-ethereum-security | HIGH | MD, tools |
| Awesome Smart Contract Datasets | https://github.com/acorn421/awesome-smart-contract-datasets | MEDIUM | MD, dataset links |

#### 5.1.2 Audit Report Repositories (13 repos)

| Name | URL | Priority | Notes |
|------|-----|----------|-------|
| Sherlock Reports | https://github.com/sherlock-protocol/sherlock-reports | HIGH | Contest audits |
| Cyfrin Audit Reports | https://github.com/Cyfrin/cyfrin-audit-reports | HIGH | Team audits |
| Pashov Audits | https://github.com/pashov/audits | HIGH | 100+ PDFs, /solo and /team dirs |
| SigP Public Audits | https://github.com/sigp/public-audits | HIGH | Score 9/10 |
| Hexens Public Reports | https://github.com/Hexens/Smart-Contract-Review-Public-Reports | HIGH | Score 8.5/10 |
| TechRate Audits | https://github.com/TechRate/Smart-Contract-Audits | MEDIUM | Free checks |
| ImmuneBytes Reports | https://github.com/ImmuneBytes/Smart-Contract-Audit-Reports | MEDIUM | Broad range |
| MixBytes Public Audits | https://github.com/mixbytes/audits_public | HIGH | AAVE, Yearn |
| EthereumCommonwealth Auditing | https://github.com/EthereumCommonwealth/Auditing | MEDIUM | No hacks record |
| Nethermind Public Reports | https://github.com/NethermindEth/PublicAuditReports | HIGH | Manual inspections |
| Halborn Public Reports | https://github.com/HalbornSecurity/PublicReports | MEDIUM | Multi-chain |
| Credshields Audit Reports | https://github.com/Credshields/audit-reports | MEDIUM | Detailed reviews |

#### 5.1.3 Vulnerability Datasets (4 repos)

| Name | URL | Priority | Statistics |
|------|-----|----------|------------|
| SmartBugs Curated | https://github.com/smartbugs/smartbugs-curated | HIGH | 143 contracts, 208 vulnerabilities, annotated |
| SmartBugs Wild | https://github.com/smartbugs/smartbugs-wild | HIGH | 47,398 contracts, unannotated |
| SolidiFI Benchmark | https://github.com/DependableSystemsLab/SolidiFI-benchmark | HIGH | 9,369 bugs in 7 types, injected |
| Tintinweb VulnDB | https://github.com/tintinweb/smart-contract-vulndb | HIGH | JSON aggregated, daily updates |

#### 5.1.4 Educational Repositories (5 repos)

| Name | URL | Priority | Content |
|------|-----|----------|---------|
| RareSkills Huff Puzzles | https://github.com/RareSkills/huff-puzzles | HIGH | Low-level puzzles |
| RareSkills Solidity Riddles | https://github.com/RareSkills/solidity-riddles | HIGH | Security riddles |
| RareSkills Gas Puzzles | https://github.com/RareSkills/gas-puzzles | HIGH | 488 stars |
| Cyfrin Foundry Course | https://github.com/Cyfrin/foundry-full-course-cu | HIGH | Full course |
| OpenZeppelin Contracts | https://github.com/OpenZeppelin/openzeppelin-contracts | HIGH | Reference impl |

### 5.2 Web Scraping Sources (12 total)

#### 5.2.1 Audit Platforms (4 sites)

| Name | Base URL | Requires JS | Pagination | Est. Records |
|------|----------|-------------|------------|--------------|
| Code4rena | https://code4rena.com | No | Date filter | 100+ reports |
| Sherlock | https://audits.sherlock.xyz | Yes (Selenium) | Contest dirs | 50+ contests |
| CodeHawks | https://codehawks.cyfrin.io | Yes | Contest slugs | 40+ contests |
| Solodit | https://solodit.xyz | Yes | Page numbers | 49,956+ results |

**Code4rena Endpoints:**
- `/reports` - All published audit reports
- `/audits` - Past and upcoming audits
- Example: `/audits/2025-09-monad`

**Sherlock Endpoints:**
- `/contests` - All contest listings
- `/contests/{id}/report` - Individual contest reports

**CodeHawks Endpoints:**
- `/c/` - Contest listing
- Example slugs: `2025-04-starknet-part-2`, `2024-12-alchemix`

#### 5.2.2 Exploit Analysis Sites (3 sites)

| Name | Base URL | Requires JS | Notes |
|------|----------|-------------|-------|
| Rekt News | https://rekt.news | No | Date pagination, exploit write-ups |
| Trail of Bits Blog | https://blog.trailofbits.com | No | `/category/blockchain`, `/category/security` |
| Immunefi | https://immunefi.com | Yes | Bug bounty disclosures |

#### 5.2.3 Documentation Sites (5 sites)

| Name | Base URL | Content Type |
|------|----------|--------------|
| Consensys Best Practices | https://consensys.github.io/smart-contract-best-practices | Security patterns |
| SWC Registry | https://swcregistry.io | Weakness classification (CWE links) |
| OWASP Smart Contract Top 10 | https://owasp.org/www-project-smart-contract-top-10 | 2025 edition |
| OpenZeppelin Docs | https://docs.openzeppelin.com/contracts | Reference docs |
| Secureum Substack | https://secureum.substack.com | Audit techniques |

### 5.3 Dataset Platform Sources (3 total)

#### 5.3.1 Kaggle Datasets (2)

| Name | Dataset ID | Statistics | Priority |
|------|------------|------------|----------|
| Smart Contract Vulnerability Dataset | tranduongminhdai/smart-contract-vulnerability-datset | 12k+ contracts, 8 vuln types, CSV labels | HIGH |
| BCCC-VulSCs-2023 | bcccdatasets/bccc-vulscs-2023 | 36,670 samples, 70 features | HIGH |

#### 5.3.2 HuggingFace Datasets (1)

| Name | Dataset ID | Statistics | Priority |
|------|------------|------------|----------|
| Zellic Smart Contract Fiesta | Zellic/smart-contract-fiesta | 3,298,271 raw files → 514,506 deduplicated | HIGH |

---

## 6. Technical Specifications

### 6.1 Existing Implementation Details

#### 6.1.1 settings.py (config/settings.py)

```python
# Key exports:
BASE_DIR = Path(__file__).parent.parent  # crawlers/
OUTPUT_DIR = BASE_DIR / "output"
REPOS_DIR = OUTPUT_DIR / "repos"
REPORTS_DIR = OUTPUT_DIR / "reports"
DATASETS_DIR = OUTPUT_DIR / "datasets"
EXPLOITS_DIR = OUTPUT_DIR / "exploits"

# API Keys (from .env):
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
KAGGLE_USERNAME = os.getenv("KAGGLE_USERNAME")
KAGGLE_KEY = os.getenv("KAGGLE_KEY")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")

# Rate limits:
RATE_LIMITS = {
    "github": {"calls": 30, "period": 60},      # 30/min
    "web_scraper": {"calls": 10, "period": 60}, # 10/min
    "kaggle": {"calls": 5, "period": 60},       # 5/min
    "huggingface": {"calls": 10, "period": 60}, # 10/min
}

# Retry config:
RETRY_CONFIG = {
    "max_attempts": 3,
    "wait_min": 1,
    "wait_max": 10,
    "wait_multiplier": 2,  # Exponential backoff
}

# File extensions:
SOLIDITY_EXTENSIONS = [".sol"]
DOCUMENT_EXTENSIONS = [".md", ".pdf", ".txt", ".html"]
DATA_EXTENSIONS = [".json", ".csv", ".yaml", ".yml"]
```

#### 6.1.2 github_cloner.py (cloners/github_cloner.py)

```python
@dataclass
class RepoInfo:
    name: str
    url: str
    local_path: Path
    category: str
    priority: str
    status: str  # 'cloned', 'updated', 'failed'
    error: Optional[str] = None

class GitHubCloner:
    def __init__(self, output_dir: Optional[Path] = None)
    def _rate_limited_call(self, func, *args, **kwargs)  # @sleep_and_retry decorated
    def get_repo_info(self, url: str) -> dict
    def clone_repo(self, url: str, category: str, priority: str) -> RepoInfo
    def update_repo(self, url: str, category: str, priority: str) -> RepoInfo
    def clone_all_from_config(self, config: dict) -> list[RepoInfo]
    def get_status_summary(self, results: list[RepoInfo]) -> dict
```

**Key behaviors:**
- Uses `git clone --depth 1` for shallow clones
- Organizes repos by category: `output/repos/{category}/{repo_name}/`
- Falls back to fresh clone if `git pull` fails
- Returns structured RepoInfo with status tracking

#### 6.1.3 helpers.py (utils/helpers.py)

```python
def load_sources_config() -> dict              # Load sources.yaml
def extract_repo_info(url: str) -> tuple       # (owner, repo_name)
def sanitize_filename(name: str) -> str        # Safe filesystem names
def get_file_hash(file_path: Path) -> str      # MD5 hash
def create_retry_decorator(service: str)       # Tenacity wrapper
def ensure_dir(path: Path) -> Path             # mkdir -p
def is_solidity_file(path: Path) -> bool
def is_document_file(path: Path) -> bool
def is_data_file(path: Path) -> bool
def count_files_by_type(directory: Path) -> dict
```

#### 6.1.4 logger.py (utils/logger.py)

```python
def setup_logger(log_file: Path, level: str = "INFO"):
    # Loguru configuration
    # Console: colored output, INFO level
    # File: rotation at 10MB, retention 1 week, DEBUG level
```

### 6.2 Import Pattern (Required)

The package is not installed, so imports require path manipulation:

```python
import sys
sys.path.insert(0, 'crawlers')

from config.settings import REPOS_DIR, GITHUB_TOKEN, RATE_LIMITS
from cloners.github_cloner import GitHubCloner
from utils.helpers import load_sources_config
from utils.logger import setup_logger, log
```

---

## 7. Deliverables by Phase

### 7.1 Phase 2: GitHub Cloners (1 remaining task)

| Deliverable | File | Description | Est. Lines |
|-------------|------|-------------|------------|
| Submodule Handler | `cloners/submodule_handler.py` | Handle nested git submodules in cloned repos | ~80 |

**Specification for submodule_handler.py:**
```python
class SubmoduleHandler:
    def __init__(self, repo_path: Path)
    def has_submodules(self) -> bool
    def list_submodules(self) -> list[dict]
    def init_submodules(self, recursive: bool = True) -> bool
    def update_submodules(self) -> bool
```

### 7.2 Phase 3: Web Scrapers (9 tasks)

| # | Deliverable | File | Est. Lines |
|---|-------------|------|------------|
| 1 | Base Scraper | `scrapers/base_scraper.py` | ~150 |
| 2-5 | Audit Scrapers | `scrapers/audit_scrapers.py` | ~400 |
| 6-8 | Exploit Scrapers | `scrapers/exploit_scrapers.py` | ~250 |
| 9 | Docs Scrapers | `scrapers/docs_scrapers.py` | ~200 |

**Specification for base_scraper.py:**
```python
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    def __init__(self, base_url: str, output_dir: Path, requires_js: bool = False)

    @abstractmethod
    def scrape(self) -> list[dict]

    def fetch_page(self, url: str, headers: dict = None) -> str
    def fetch_page_js(self, url: str) -> str  # Selenium/Playwright
    def parse_html(self, html: str) -> BeautifulSoup
    def save_report(self, data: dict, filename: str)
    def handle_pagination(self, base_url: str, max_pages: int = 100) -> list[str]

    @property
    def rate_limiter(self) -> RateLimiter
```

**Specification for audit_scrapers.py:**
```python
class Code4renaScraper(BaseScraper):
    # Endpoints: /reports, /audits
    # Output: {title, url, date, findings: [{severity, title, description}]}

class SherlockScraper(BaseScraper):
    # Requires JS (Selenium)
    # Endpoints: /contests, /contests/{id}/report

class CodeHawksScraper(BaseScraper):
    # Requires JS
    # 40+ contest slugs

class SoloditScraper(BaseScraper):
    # Requires JS
    # 49,956+ results with pagination
```

**Specification for exploit_scrapers.py:**
```python
class RektNewsScraper(BaseScraper):
    # Date-based pagination
    # Output: {title, date, protocol, amount_lost, vulnerability_type, analysis}

class TrailOfBitsScraper(BaseScraper):
    # Category filters: /blockchain, /security

class ImmunefiBugScraper(BaseScraper):
    # Requires JS
    # Bug bounty disclosures
```

**Specification for docs_scrapers.py:**
```python
class ConsensysScraper(BaseScraper)
class SWCRegistryScraper(BaseScraper)
class OWASPScraper(BaseScraper)
class OpenZeppelinDocsScraper(BaseScraper)
class SecureumScraper(BaseScraper)
```

### 7.3 Phase 4: Dataset Downloaders (2 tasks)

| # | Deliverable | File | Est. Lines |
|---|-------------|------|------------|
| 1 | Kaggle Downloader | `downloaders/kaggle_downloader.py` | ~120 |
| 2 | HuggingFace Downloader | `downloaders/hf_downloader.py` | ~100 |

**Specification for kaggle_downloader.py:**
```python
class KaggleDownloader:
    def __init__(self, output_dir: Path = DATASETS_DIR)
    def authenticate(self) -> bool  # Uses KAGGLE_USERNAME, KAGGLE_KEY
    def download_dataset(self, dataset_id: str) -> Path
    def download_all_from_config(self, config: dict) -> list[dict]
    def extract_dataset(self, zip_path: Path) -> Path
    def get_dataset_info(self, dataset_id: str) -> dict
```

**Specification for hf_downloader.py:**
```python
class HuggingFaceDownloader:
    def __init__(self, output_dir: Path = DATASETS_DIR)
    def authenticate(self) -> bool  # Uses HUGGINGFACE_TOKEN
    def download_dataset(self, dataset_id: str, split: str = None) -> Path
    def stream_large_dataset(self, dataset_id: str) -> Iterator
    def download_all_from_config(self, config: dict) -> list[dict]
```

### 7.4 Phase 5: Data Processors (4 tasks)

| # | Deliverable | File | Est. Lines |
|---|-------------|------|------------|
| 1 | Normalizer | `processors/normalizer.py` | ~200 |
| 2 | Extractor | `processors/extractor.py` | ~250 |
| 3 | Deduplicator | `processors/deduplicator.py` | ~100 |
| 4 | Indexer | `processors/indexer.py` | ~150 |

**Specification for normalizer.py:**
```python
class DataNormalizer:
    def __init__(self, output_dir: Path)

    def normalize_solidity(self, file_path: Path) -> dict
    def normalize_audit_md(self, file_path: Path) -> dict
    def normalize_audit_pdf(self, file_path: Path) -> dict  # Uses pdfplumber
    def normalize_exploit_html(self, html: str, source: str) -> dict
    def normalize_json_dataset(self, file_path: Path) -> list[dict]

    def process_directory(self, dir_path: Path, source_type: str) -> list[dict]
    def write_jsonl(self, records: list[dict], output_file: Path)
```

**Specification for extractor.py:**
```python
class VulnerabilityExtractor:
    def __init__(self)

    # Patterns for known vulnerability types
    VULNERABILITY_PATTERNS = {
        "reentrancy": [...],
        "overflow": [...],
        "access_control": [...],
        # ... 10+ types
    }

    def extract_from_solidity(self, code: str) -> list[dict]
    def extract_from_audit(self, report: dict) -> list[dict]
    def extract_severity(self, text: str) -> str  # high/medium/low/info
    def extract_code_snippets(self, text: str) -> list[str]
    def tag_vulnerability(self, finding: dict) -> list[str]
```

**Specification for deduplicator.py:**
```python
class Deduplicator:
    def __init__(self)

    def hash_content(self, content: str) -> str  # MD5
    def hash_file(self, file_path: Path) -> str
    def find_duplicates(self, records: list[dict]) -> dict[str, list]
    def deduplicate(self, records: list[dict], key: str = "content") -> list[dict]
    def deduplicate_files(self, directory: Path) -> dict  # Stats
```

**Specification for indexer.py:**
```python
class SQLiteIndexer:
    def __init__(self, db_path: Path)

    def create_tables(self)
    def index_vulnerability(self, record: dict)
    def index_audit(self, record: dict)
    def index_exploit(self, record: dict)
    def build_fts_index(self)  # Full-text search

    def search(self, query: str, filters: dict = None) -> list[dict]
    def get_stats(self) -> dict
```

### 7.5 Phase 6: CLI & Orchestration (3 tasks)

| # | Deliverable | File | Est. Lines |
|---|-------------|------|------------|
| 1 | Rate Limiter | `utils/rate_limiter.py` | ~80 |
| 2 | CLI | `cli.py` | ~200 |
| 3 | Orchestrator | `orchestrator.py` | ~250 |

**Specification for rate_limiter.py:**
```python
class TokenBucketRateLimiter:
    def __init__(self, calls: int, period: int)
    def acquire(self) -> bool
    def wait_for_token(self)

class RateLimiterRegistry:
    _limiters: dict[str, TokenBucketRateLimiter]

    @classmethod
    def get(cls, service: str) -> TokenBucketRateLimiter

def rate_limited(service: str):
    """Decorator for rate-limited functions"""
```

**Specification for cli.py:**
```python
import click

@click.group()
def cli():
    """Smart Contract Security Data Crawler"""

@cli.command()
@click.option('--all', is_flag=True)
@click.option('--category', type=str)
def clone(all, category):
    """Clone GitHub repositories"""

@cli.command()
@click.option('--source', type=str)
@click.option('--all', is_flag=True)
def scrape(source, all):
    """Scrape web platforms"""

@cli.command()
@click.option('--platform', type=click.Choice(['kaggle', 'huggingface']))
def download(platform):
    """Download datasets"""

@cli.command()
@click.option('--all', is_flag=True)
def process(all):
    """Process and normalize data"""

@cli.command()
def run():
    """Run full pipeline"""

@cli.command()
def status():
    """Show collection status"""
```

**Specification for orchestrator.py:**
```python
class PipelineOrchestrator:
    def __init__(self, config: dict)

    # Component instances
    self.cloner: GitHubCloner
    self.scrapers: dict[str, BaseScraper]
    self.downloaders: dict[str, BaseDownloader]
    self.normalizer: DataNormalizer
    self.extractor: VulnerabilityExtractor
    self.deduplicator: Deduplicator
    self.indexer: SQLiteIndexer

    def run_clone_phase(self) -> dict
    def run_scrape_phase(self) -> dict
    def run_download_phase(self) -> dict
    def run_process_phase(self) -> dict

    def run_full_pipeline(self) -> dict
    def get_pipeline_status(self) -> dict
    def resume_from_checkpoint(self, phase: str) -> dict
```

### 7.6 Phase 7: Testing & Scripts (9 tasks)

| # | Deliverable | File | Description |
|---|-------------|------|-------------|
| 1 | Config Tests | `tests/test_config.py` | Test settings.py, sources.yaml loading |
| 2 | Cloner Tests | `tests/test_cloners.py` | Test GitHubCloner, SubmoduleHandler |
| 3 | Scraper Tests | `tests/test_scrapers.py` | Test all scraper classes |
| 4 | Downloader Tests | `tests/test_downloaders.py` | Test Kaggle/HF downloaders |
| 5 | Processor Tests | `tests/test_processors.py` | Test normalizer, extractor, etc. |
| 6 | Utils Tests | `tests/test_utils.py` | Test helpers.py, logger.py |
| 7 | Cloner Script | `scripts/verify_cloner.sh` | Manual verification |
| 8 | Scraper Script | `scripts/verify_scraper.sh` | Manual verification |
| 9 | Full Script | `scripts/verify_all.sh` | Integration test |

**Test markers (from pytest.ini):**
```ini
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
```

---

## 8. File Specifications

### 8.1 Complete File List with Estimates

| File Path | Status | Est. Lines | Priority |
|-----------|--------|------------|----------|
| `config/__init__.py` | Done | 0 | - |
| `config/settings.py` | Done | 66 | - |
| `config/sources.yaml` | Done | 263 | - |
| `cloners/__init__.py` | Done | 0 | - |
| `cloners/github_cloner.py` | Done | 227 | - |
| `cloners/submodule_handler.py` | TODO | 80 | LOW |
| `scrapers/__init__.py` | Done | 0 | - |
| `scrapers/base_scraper.py` | TODO | 150 | HIGH |
| `scrapers/audit_scrapers.py` | TODO | 400 | HIGH |
| `scrapers/exploit_scrapers.py` | TODO | 250 | HIGH |
| `scrapers/docs_scrapers.py` | TODO | 200 | MEDIUM |
| `downloaders/__init__.py` | Done | 0 | - |
| `downloaders/kaggle_downloader.py` | TODO | 120 | HIGH |
| `downloaders/hf_downloader.py` | TODO | 100 | HIGH |
| `processors/__init__.py` | Done | 0 | - |
| `processors/normalizer.py` | TODO | 200 | HIGH |
| `processors/extractor.py` | TODO | 250 | HIGH |
| `processors/deduplicator.py` | TODO | 100 | MEDIUM |
| `processors/indexer.py` | TODO | 150 | MEDIUM |
| `utils/__init__.py` | Done | 0 | - |
| `utils/logger.py` | Done | 33 | - |
| `utils/helpers.py` | Done | 91 | - |
| `utils/rate_limiter.py` | TODO | 80 | MEDIUM |
| `cli.py` | TODO | 200 | MEDIUM |
| `orchestrator.py` | TODO | 250 | MEDIUM |
| `tests/conftest.py` | Done | 142 | - |
| `tests/test_config.py` | TODO | 50 | LOW |
| `tests/test_cloners.py` | TODO | 80 | LOW |
| `tests/test_scrapers.py` | TODO | 120 | LOW |
| `tests/test_downloaders.py` | TODO | 60 | LOW |
| `tests/test_processors.py` | TODO | 100 | LOW |
| `tests/test_utils.py` | TODO | 50 | LOW |
| `scripts/verify_cloner.sh` | TODO | 30 | LOW |
| `scripts/verify_scraper.sh` | TODO | 40 | LOW |
| `scripts/verify_all.sh` | TODO | 50 | LOW |

**Totals:**
- Done: ~820 lines across 7 substantial files
- TODO: ~2,890 lines across 20 files
- Total: ~3,710 lines

---

## 9. Data Schemas

### 9.1 Unified Output Schema (JSONL)

#### 9.1.1 Vulnerability Record

```json
{
  "id": "sha256-hash-of-content",
  "source": "smartbugs-curated",
  "source_type": "github",
  "type": "vulnerability",
  "vulnerability_type": "reentrancy",
  "severity": "high",
  "title": "Reentrancy in withdraw()",
  "description": "The withdraw function allows reentrancy attacks...",
  "code_snippet": "function withdraw() public { ... }",
  "file_path": "contracts/Vault.sol",
  "line_numbers": [45, 52],
  "tags": ["reentrancy", "defi", "external-call"],
  "cwe_id": "CWE-841",
  "swc_id": "SWC-107",
  "references": ["https://swcregistry.io/docs/SWC-107"],
  "timestamp": "2024-01-15T00:00:00Z",
  "metadata": {
    "contract_name": "Vault",
    "solidity_version": "0.8.0",
    "has_fix": true
  }
}
```

#### 9.1.2 Audit Record

```json
{
  "id": "sha256-hash",
  "source": "code4rena",
  "source_type": "web",
  "type": "audit",
  "title": "Monad Audit Report",
  "protocol": "Monad",
  "auditor": "Code4rena",
  "date": "2025-09-15",
  "url": "https://code4rena.com/audits/2025-09-monad",
  "findings": [
    {
      "id": "H-01",
      "severity": "high",
      "title": "...",
      "description": "...",
      "code_snippet": "...",
      "recommendation": "..."
    }
  ],
  "finding_counts": {
    "critical": 0,
    "high": 3,
    "medium": 7,
    "low": 12,
    "informational": 5
  },
  "tags": ["defi", "layer1"],
  "timestamp": "2025-09-20T00:00:00Z"
}
```

#### 9.1.3 Exploit Record

```json
{
  "id": "sha256-hash",
  "source": "rekt-news",
  "source_type": "web",
  "type": "exploit",
  "title": "Balancer Rekt",
  "protocol": "Balancer",
  "date": "2023-08-22",
  "amount_lost_usd": 128000000,
  "vulnerability_type": "flash-loan-attack",
  "chain": "ethereum",
  "description": "Detailed analysis of the exploit...",
  "attack_vector": "...",
  "root_cause": "...",
  "tx_hashes": ["0x..."],
  "attacker_addresses": ["0x..."],
  "tags": ["defi", "flash-loan", "amm"],
  "references": [
    "https://rekt.news/balancer-rekt2",
    "https://blog.trailofbits.com/..."
  ],
  "timestamp": "2023-08-23T00:00:00Z"
}
```

### 9.2 SQLite Index Schema

```sql
-- Main tables
CREATE TABLE vulnerabilities (
    id TEXT PRIMARY KEY,
    source TEXT,
    vulnerability_type TEXT,
    severity TEXT,
    title TEXT,
    description TEXT,
    code_snippet TEXT,
    file_path TEXT,
    tags TEXT,  -- JSON array
    timestamp TEXT,
    raw_json TEXT
);

CREATE TABLE audits (
    id TEXT PRIMARY KEY,
    source TEXT,
    protocol TEXT,
    auditor TEXT,
    date TEXT,
    title TEXT,
    finding_counts TEXT,  -- JSON object
    tags TEXT,
    timestamp TEXT,
    raw_json TEXT
);

CREATE TABLE exploits (
    id TEXT PRIMARY KEY,
    source TEXT,
    protocol TEXT,
    date TEXT,
    amount_lost_usd INTEGER,
    vulnerability_type TEXT,
    chain TEXT,
    title TEXT,
    tags TEXT,
    timestamp TEXT,
    raw_json TEXT
);

-- Full-text search
CREATE VIRTUAL TABLE vulnerabilities_fts USING fts5(
    title, description, code_snippet, tags,
    content='vulnerabilities'
);

CREATE VIRTUAL TABLE audits_fts USING fts5(
    title, protocol, tags,
    content='audits'
);

CREATE VIRTUAL TABLE exploits_fts USING fts5(
    title, protocol, description, tags,
    content='exploits'
);
```

---

## 10. Dependencies & Environment

### 10.1 Python Dependencies (requirements.txt)

```
# Web scraping
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
selenium>=4.15.0
playwright>=1.40.0

# GitHub API
PyGithub>=2.1.0

# Dataset platforms
kaggle>=1.5.16
huggingface-hub>=0.19.0
datasets>=2.15.0

# Data processing
pandas>=2.1.0
pyyaml>=6.0.1
python-dotenv>=1.0.0

# PDF processing
PyPDF2>=3.0.0
pdfplumber>=0.10.0

# Markdown processing
markdown>=3.5.0
markdown-it-py>=3.0.0

# Rate limiting and retries
ratelimit>=2.2.1
tenacity>=8.2.0

# Async support
aiohttp>=3.9.0
aiofiles>=23.2.0

# CLI
click>=8.1.0
rich>=13.7.0
tqdm>=4.66.0

# Scheduling
schedule>=1.2.0
apscheduler>=3.10.0

# Logging
loguru>=0.7.0
```

### 10.2 Environment Variables (.env)

```bash
# Required
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Required for dataset downloads
KAGGLE_USERNAME=your_username
KAGGLE_KEY=your_api_key
HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### 10.3 System Requirements

- Python 3.10+
- Git (for cloning)
- Chrome/Chromium (for Selenium-based scrapers)
- ~50GB disk space (for all datasets)
- Internet connection with reasonable bandwidth

---

## 11. Rate Limiting Strategy

### 11.1 Rate Limits by Service

| Service | Calls | Period | Strategy |
|---------|-------|--------|----------|
| GitHub API | 30 | 60s | Token rotation if multiple tokens |
| GitHub (unauthenticated) | 60 | 3600s | Avoid, always use token |
| Web scraping (general) | 10 | 60s | Sleep + exponential backoff |
| Code4rena | 10 | 60s | Respect robots.txt |
| Sherlock | 5 | 60s | JS rendering overhead |
| Kaggle API | 5 | 60s | Queue-based downloads |
| HuggingFace | 10 | 60s | Streaming for large datasets |

### 11.2 Retry Strategy

```python
RETRY_CONFIG = {
    "max_attempts": 3,
    "wait_min": 1,      # seconds
    "wait_max": 10,     # seconds
    "wait_multiplier": 2,  # exponential backoff: 1s, 2s, 4s
}

# HTTP status codes to retry
RETRY_STATUS_CODES = [429, 500, 502, 503, 504]
```

---

## 12. Testing Requirements

### 12.1 Test Categories

| Category | Marker | Description |
|----------|--------|-------------|
| Unit | `@pytest.mark.unit` | Fast, isolated, mocked dependencies |
| Integration | `@pytest.mark.integration` | Real API calls, slow |
| Slow | `@pytest.mark.slow` | Long-running tests |

### 12.2 Test Coverage Targets

| Module | Target Coverage |
|--------|-----------------|
| config/ | 90% |
| cloners/ | 85% |
| scrapers/ | 80% |
| downloaders/ | 80% |
| processors/ | 85% |
| utils/ | 90% |
| cli.py | 75% |
| orchestrator.py | 75% |

### 12.3 Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run only unit tests
pytest tests/ -v -m unit

# Run excluding slow tests
pytest tests/ -v -m "not slow"

# Run with coverage
pytest tests/ -v --cov=crawlers --cov-report=term-missing

# Run single test file
pytest tests/test_cloners.py -v
```

### 12.4 Existing Test Fixtures (conftest.py)

```python
@pytest.fixture
def project_root() -> Path

@pytest.fixture
def crawlers_dir() -> Path

@pytest.fixture
def temp_dir() -> Path  # Auto-cleanup

@pytest.fixture
def sample_sources_config() -> dict  # Minimal test config

@pytest.fixture
def mock_github_url() -> str

@pytest.fixture
def mock_invalid_url() -> str

@pytest.fixture
def sample_solidity_code() -> str  # Vulnerable contract

@pytest.fixture
def sample_audit_report() -> str  # MD format

@pytest.fixture
def sources_yaml_path() -> Path

@pytest.fixture
def loaded_sources_config() -> dict
```

---

## 13. Risk Assessment

### 13.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Website structure changes | HIGH | MEDIUM | Modular scrapers, version checks |
| Rate limiting/IP blocks | MEDIUM | HIGH | Distributed IPs, respect limits |
| Large dataset download failures | MEDIUM | MEDIUM | Resumable downloads, checksums |
| PDF parsing failures | MEDIUM | LOW | Multiple PDF libraries, fallbacks |
| JS rendering timeouts | MEDIUM | MEDIUM | Headless browser pool, retries |

### 13.2 Data Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Duplicate data inflation | HIGH | MEDIUM | MD5 deduplication |
| Outdated vulnerability info | MEDIUM | LOW | Timestamp tracking, updates |
| Inconsistent severity labels | HIGH | MEDIUM | Normalization mapping |
| Missing source attribution | LOW | HIGH | Strict source tracking |

### 13.3 Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API key exposure | LOW | CRITICAL | .env files, .gitignore |
| Disk space exhaustion | MEDIUM | MEDIUM | Incremental downloads, cleanup |
| Long-running pipeline failures | MEDIUM | MEDIUM | Checkpointing, resume capability |

---

## 14. Acceptance Criteria

### 14.1 Phase Completion Criteria

#### Phase 3: Web Scrapers
- [ ] All 4 audit platform scrapers functional
- [ ] All 3 exploit site scrapers functional
- [ ] All 5 documentation scrapers functional
- [ ] Rate limiting enforced for all scrapers
- [ ] Error handling with retry logic
- [ ] Output saved to `output/reports/` and `output/exploits/`

#### Phase 4: Dataset Downloaders
- [ ] Kaggle authentication working
- [ ] Both Kaggle datasets downloadable
- [ ] HuggingFace authentication working
- [ ] Zellic dataset downloadable (streaming for size)
- [ ] Output saved to `output/datasets/`

#### Phase 5: Data Processors
- [ ] All raw data normalizable to JSONL
- [ ] Vulnerability extraction from Solidity code
- [ ] Vulnerability extraction from audit reports
- [ ] Deduplication reduces dataset by >20%
- [ ] SQLite index queryable with FTS

#### Phase 6: CLI & Orchestration
- [ ] All CLI commands functional
- [ ] Full pipeline runnable with single command
- [ ] Progress reporting during execution
- [ ] Resumable from any phase

#### Phase 7: Testing
- [ ] All test files created
- [ ] >75% code coverage
- [ ] All verification scripts working
- [ ] CI-ready test configuration

### 14.2 Final Deliverables

| Deliverable | Location | Format |
|-------------|----------|--------|
| Cloned repositories | `output/repos/` | Git repos |
| Scraped audit reports | `output/reports/` | MD/PDF |
| Scraped exploit write-ups | `output/exploits/` | JSON |
| Downloaded datasets | `output/datasets/` | Various |
| Normalized vulnerabilities | `output/processed/vulnerabilities.jsonl` | JSONL |
| Normalized audits | `output/processed/audits.jsonl` | JSONL |
| Normalized exploits | `output/processed/exploits.jsonl` | JSONL |
| Searchable index | `output/processed/index.sqlite` | SQLite |

### 14.3 Success Metrics

| Metric | Target |
|--------|--------|
| Total Solidity contracts collected | >50,000 |
| Total audit reports collected | >500 |
| Total exploit write-ups collected | >200 |
| Unique vulnerabilities indexed | >10,000 |
| Pipeline completion time | <24 hours |
| Test coverage | >75% |

---

## Appendix A: Quick Reference Commands

```bash
# Setup
cd crawlers && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Clone all GitHub repos
python -c "
import sys; sys.path.insert(0, 'crawlers')
from cloners.github_cloner import GitHubCloner
from utils.helpers import load_sources_config
cloner = GitHubCloner()
results = cloner.clone_all_from_config(load_sources_config())
print(cloner.get_status_summary(results))
"

# Run tests
pytest tests/ -v
pytest tests/ -v --cov=crawlers

# Future CLI (after implementation)
python -m crawlers.cli clone --all
python -m crawlers.cli scrape --all
python -m crawlers.cli download --platform kaggle
python -m crawlers.cli process --all
python -m crawlers.cli run  # Full pipeline
```

---

## Appendix B: Sources YAML Structure Reference

```yaml
github_repos:
  aggregators:      # 4 repos
  audit_repos:      # 13 repos
  vulnerability_datasets:  # 4 repos
  educational:      # 5 repos

web_scrapers:
  audit_platforms:  # 4 sites (Code4rena, Sherlock, CodeHawks, Solodit)
  exploit_sites:    # 3 sites (Rekt, ToB, Immunefi)
  documentation:    # 5 sites

dataset_downloads:
  kaggle:           # 2 datasets
  huggingface:      # 1 dataset
```

---

*End of PRD Document*
