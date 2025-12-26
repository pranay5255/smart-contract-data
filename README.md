# Smart Contract Security Data Crawler

A Python-based system for collecting smart contract security training data from 40+ public sources.

## Quick Start

```bash
# 1. Setup virtual environment
cd crawlers
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run tests
pytest tests/ -v

# 5. Start crawling
python -m crawlers.cli clone --all
```

---

## Implementation Steps

### Step 1: Environment Setup

```bash
# Create and activate virtual environment
cd /home/pranay5255/Documents/smart-contract-data/crawlers
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << 'EOF'
GITHUB_TOKEN=your_github_token_here
KAGGLE_USERNAME=your_kaggle_username
KAGGLE_KEY=your_kaggle_api_key
HUGGINGFACE_TOKEN=your_hf_token
LOG_LEVEL=INFO
EOF
```

### Step 2: Verify Configuration

```bash
# Test configuration loads correctly
cd /home/pranay5255/Documents/smart-contract-data
python3 -c "
import sys
sys.path.insert(0, 'crawlers')
from config.settings import *
print('Base Dir:', BASE_DIR)
print('Output Dir:', OUTPUT_DIR)
print('GitHub Token:', 'SET' if GITHUB_TOKEN else 'NOT SET')
print('Kaggle:', 'SET' if KAGGLE_USERNAME else 'NOT SET')
"
```

### Step 3: Test GitHub Cloner

```bash
# Test cloning a single repository
cd /home/pranay5255/Documents/smart-contract-data
python3 -c "
import sys
sys.path.insert(0, 'crawlers')
from cloners.github_cloner import GitHubCloner
from utils.helpers import load_sources_config

cloner = GitHubCloner()

# Test with a small repo
result = cloner.clone_repo(
    url='https://github.com/smartbugs/smartbugs-curated',
    category='test',
    priority='high'
)
print(f'Status: {result.status}')
print(f'Path: {result.local_path}')
"
```

### Step 4: Clone All GitHub Repositories

```bash
# Clone all configured repositories
cd /home/pranay5255/Documents/smart-contract-data
python3 << 'EOF'
import sys
sys.path.insert(0, 'crawlers')
from cloners.github_cloner import GitHubCloner
from utils.helpers import load_sources_config

config = load_sources_config()
cloner = GitHubCloner()

results = cloner.clone_all_from_config(config)
summary = cloner.get_status_summary(results)

print(f"Total: {summary['total']}")
print(f"Cloned: {summary['cloned']}")
print(f"Updated: {summary['updated']}")
print(f"Failed: {summary['failed']}")
EOF
```

### Step 5: Implement Web Scrapers

Create `crawlers/scrapers/base_scraper.py`:

```python
# See implementation in scrapers/base_scraper.py
```

Create `crawlers/scrapers/audit_scrapers.py`:

```python
# Implement Code4rena, Sherlock, CodeHawks scrapers
```

### Step 6: Implement Dataset Downloaders

Create `crawlers/downloaders/kaggle_downloader.py`:

```python
# Implement Kaggle dataset downloads
```

Create `crawlers/downloaders/hf_downloader.py`:

```python
# Implement HuggingFace dataset downloads
```

### Step 7: Implement Processors

Create processing pipeline in `crawlers/processors/`:

```python
# normalizer.py - Convert to unified format
# extractor.py - Extract vulnerabilities
# deduplicator.py - Remove duplicates
# indexer.py - Build search index
```

### Step 8: Create CLI

```bash
# After implementing cli.py, use these commands:
python -m crawlers.cli clone --all
python -m crawlers.cli clone --category audit_repos
python -m crawlers.cli scrape --source code4rena
python -m crawlers.cli download --platform kaggle
python -m crawlers.cli process --all
python -m crawlers.cli run --full-pipeline
```

---

## Manual Verification Commands

### Verify Directory Structure

```bash
# Check project structure
tree -L 2 /home/pranay5255/Documents/smart-contract-data/crawlers/

# Check output directories
ls -la /home/pranay5255/Documents/smart-contract-data/crawlers/output/
```

### Verify GitHub Cloner

```bash
# Run cloner test
cd /home/pranay5255/Documents/smart-contract-data
bash scripts/verify_cloner.sh
```

### Verify Configuration

```bash
# Check sources.yaml is valid
python3 -c "import yaml; yaml.safe_load(open('crawlers/config/sources.yaml'))" && echo "YAML OK"

# Count configured sources
python3 -c "
import yaml
config = yaml.safe_load(open('crawlers/config/sources.yaml'))
github = sum(len(v) for v in config.get('github_repos', {}).values())
web = sum(len(v) for v in config.get('web_scrapers', {}).values())
datasets = sum(len(v) for v in config.get('dataset_downloads', {}).values())
print(f'GitHub repos: {github}')
print(f'Web sources: {web}')
print(f'Datasets: {datasets}')
print(f'Total: {github + web + datasets}')
"
```

### Run All Tests

```bash
# Run pytest suite
cd /home/pranay5255/Documents/smart-contract-data
pytest tests/ -v --tb=short

# Run with coverage
pytest tests/ -v --cov=crawlers --cov-report=term-missing
```

---

## Project Structure

```
crawlers/
├── config/
│   ├── __init__.py
│   ├── settings.py      # Configuration settings
│   └── sources.yaml     # Data source definitions
├── cloners/
│   ├── __init__.py
│   └── github_cloner.py # GitHub repo cloning
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py  # Abstract base class
│   └── audit_scrapers.py # Audit platform scrapers
├── downloaders/
│   ├── __init__.py
│   └── kaggle_downloader.py
├── processors/
│   ├── __init__.py
│   └── normalizer.py
├── utils/
│   ├── __init__.py
│   ├── logger.py        # Logging setup
│   └── helpers.py       # Helper functions
├── output/              # Output directories
├── requirements.txt
└── cli.py              # Command-line interface
```

---

## API Keys Required

| Service | Purpose | Get Key |
|---------|---------|---------|
| GitHub | API access for repo info | https://github.com/settings/tokens |
| Kaggle | Dataset downloads | https://www.kaggle.com/settings |
| HuggingFace | Dataset downloads | https://huggingface.co/settings/tokens |

---

## Troubleshooting

### Import Errors

```bash
# Ensure you're in the right directory
cd /home/pranay5255/Documents/smart-contract-data

# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/crawlers"
```

### Rate Limiting

```bash
# Check GitHub rate limit
curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit
```

### Missing Dependencies

```bash
# Reinstall all dependencies
pip install -r crawlers/requirements.txt --force-reinstall
```
