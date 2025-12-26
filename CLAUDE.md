# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-based data collection system for gathering smart contract security training data from 40+ public sources (audit reports, vulnerability datasets, exploit analyses, educational materials from GitHub, Code4rena, Sherlock, Kaggle, HuggingFace, etc.).

## Commands

```bash
# Setup (from project root)
cd crawlers && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add API keys

# Run tests
pytest tests/ -v
pytest tests/test_cloners.py -v  # Single test file
pytest -m "not slow"             # Skip slow tests
pytest -m integration            # Only integration tests

# Verify YAML config
python3 -c "import yaml; yaml.safe_load(open('crawlers/config/sources.yaml'))" && echo "OK"

# Test GitHub cloner manually
python3 -c "
import sys; sys.path.insert(0, 'crawlers')
from cloners.github_cloner import GitHubCloner
from utils.helpers import load_sources_config
cloner = GitHubCloner()
result = cloner.clone_repo('https://github.com/smartbugs/smartbugs-curated', 'test', 'high')
print(f'Status: {result.status}, Path: {result.local_path}')
"
```

## Architecture

```
crawlers/                     # Main package (run from project root with sys.path.insert)
├── config/
│   ├── settings.py          # Env vars, paths, rate limits (REPOS_DIR, GITHUB_TOKEN, etc.)
│   └── sources.yaml         # All 40+ data sources declaratively defined
├── cloners/
│   └── github_cloner.py     # GitHubCloner class - clone/update repos with rate limiting
├── scrapers/                # NOT IMPLEMENTED - web scraping for audit platforms
├── downloaders/             # NOT IMPLEMENTED - Kaggle/HuggingFace downloads
├── processors/              # NOT IMPLEMENTED - normalize to JSONL, dedupe, index
├── utils/
│   ├── helpers.py           # load_sources_config(), extract_repo_info(), file utils
│   └── logger.py            # Loguru setup with file rotation
└── output/                  # repos/, reports/, datasets/, exploits/
```

## Key Patterns

**Import pattern** (required because package isn't installed):
```python
import sys
sys.path.insert(0, 'crawlers')
from config.settings import REPOS_DIR, GITHUB_TOKEN
from cloners.github_cloner import GitHubCloner
from utils.helpers import load_sources_config
```

**Config loading**:
```python
config = load_sources_config()  # Returns dict from sources.yaml
# config['github_repos']['audits'] -> list of repo dicts
# config['web_scrapers']['audit_platforms'] -> list of scraper configs
```

**Cloner usage**:
```python
cloner = GitHubCloner()
results = cloner.clone_all_from_config(config)  # Returns list[RepoInfo]
summary = cloner.get_status_summary(results)    # Returns dict with counts
```

## Implementation Status

| Component | Status |
|-----------|--------|
| config/, utils/ | Done |
| cloners/github_cloner.py | Done |
| scrapers/ | Empty - needs base_scraper.py, audit_scrapers.py, exploit_scrapers.py |
| downloaders/ | Empty - needs kaggle_downloader.py, hf_downloader.py |
| processors/ | Empty - needs normalizer.py, extractor.py, deduplicator.py, indexer.py |
| cli.py, orchestrator.py | Not created |
| tests/test_*.py | Fixtures only (conftest.py), no actual tests |

## Environment Variables

Required in `.env`:
- `GITHUB_TOKEN` - GitHub API token (5000 req/hr authenticated)
- `KAGGLE_USERNAME`, `KAGGLE_KEY` - For Kaggle dataset downloads
- `HUGGINGFACE_TOKEN` - For HuggingFace dataset access
- `LOG_LEVEL` - Optional, defaults to INFO

## Output Schema Target

```json
{
  "id": "unique-hash",
  "source": "code4rena",
  "type": "vulnerability",
  "severity": "high",
  "title": "Reentrancy in withdraw()",
  "description": "...",
  "code_snippet": "...",
  "tags": ["reentrancy", "defi"]
}
```
