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

## Current OCR Dataset And Overnight Run Workflow

The crawler outputs have been uploaded to Hugging Face, and the OCR path now runs
through a Modal-hosted SGLang `baidu/Unlimited-OCR` API. Use this section when
setting up a fresh machine or starting an overnight OCR pass over the audit PDFs.

### 1. Prerequisites

Install local tools:

```bash
python -V
modal --version
hf version
pdfinfo -v
```

`pdfinfo` comes from Poppler (`poppler-utils` on Ubuntu/Debian). It is used only
for local page-count planning. The OCR rendering happens inside the Modal service.

Set credentials:

```bash
export HF_TOKEN="<huggingface_token>"
export MODAL_TOKEN_ID="<modal_token_id>"       # if not already logged in
export MODAL_TOKEN_SECRET="<modal_token_secret>"
```

For local Modal CLI auth, `modal setup` is also fine if you prefer browser auth.

### 2. Restore Uploaded Datasets From Hugging Face

The uploaded datasets under `pranay5255` are documented in
`docs/audit-pdf-to-evmbench/POST_TRAINING_DATASET_SOURCES.md`. The main repos are:

- `pranay5255/smart-contract-audit-pdfs`
- `pranay5255/smart-contract-audit-nonpdf-artifacts`
- `pranay5255/smart-contract-vulnerability-benchmarks`
- `pranay5255/smart-contract-kaggle-source-files`
- `pranay5255/smart-contract-csv-datasets`
- `pranay5255/smart-contract-aggregators-educational`

To restore the PDF corpus into the expected local path:

```bash
cd /home/pranay5255/Documents/smart-contract-data

hf download pranay5255/smart-contract-audit-pdfs \
  --repo-type dataset \
  --local-dir crawlers/output \
  --include "**/*.pdf" \
  --include "manifest.csv"
```

To restore CSV datasets:

```bash
hf download pranay5255/smart-contract-csv-datasets \
  --repo-type dataset \
  --local-dir crawlers/output/datasets \
  --include "**/*.csv" \
  --include "manifest.csv"
```

The OCR chunk planner expects audit PDFs under:

```text
crawlers/output/repos/audit_repos
```

### 3. Configure And Deploy Modal OCR

The Modal app is `modal_apps/unlimited_ocr_sglang.py`. It serves three
authenticated endpoints:

- `GET /health`
- `POST /v1/ocr/pdf`
- `POST /v1/ocr/image`

Create a bearer token and store it in a Modal Secret:

```bash
umask 077
python -c "import secrets; print(secrets.token_urlsafe(48))" > /tmp/unlimited_ocr_api_key

modal secret create unlimited-ocr-api \
  OCR_API_KEY="$(cat /tmp/unlimited_ocr_api_key)"
```

Deploy with the Modal CLI:

```bash
modal deploy modal_apps/unlimited_ocr_sglang.py
```

Set the URL printed by `modal deploy`:

```bash
export OCR_URL="https://<your-modal-url>.modal.run"
export OCR_API_KEY="$(cat /tmp/unlimited_ocr_api_key)"
```

Verify readiness and auth:

```bash
python scripts/ocr_modal_client.py \
  --url "$OCR_URL" \
  --health \
  --check-unauthorized
```

The first request may cold-start an H100 and load SGLang. That can take a few
minutes. Subsequent requests are much faster while the container is warm.

### 4. Generate PDF OCR Chunks

The current generated chunk plan is:

```text
crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624
```

Current inventory:

- Total PDFs under `crawlers/output/repos/audit_repos`: `4074`
- OCR candidate audit-report PDFs: `4036`
- Excluded coverage-agreement PDFs: `38`
- Candidate pages: `76894`
- Chunks: `31`
- Typical chunk size: about `2480` pages

Coverage agreements are excluded by default because they are not audit reports.
Regenerate with `--include-excluded` if you want them OCRed too.

Regenerate the same style of plan:

```bash
python scripts/ocr_pdf_make_chunks.py \
  --run-id audit_pdf_chunks_target2500_20260624 \
  --target-pages-per-chunk 2500 \
  --max-pdfs-per-chunk 300 \
  --force
```

Outputs:

- `summary.json`: corpus and chunk summary
- `manifest.jsonl`: all PDFs selected for OCR
- `excluded.jsonl`: PDFs intentionally excluded from OCR
- `chunks/chunk_0000.jsonl` ... `chunks/chunk_0030.jsonl`: balanced work chunks

### 5. Run Overnight OCR On Chunks

Raw API responses are written per PDF page-window. Use a 4-page window for a
good balance between API overhead and failure isolation:

```bash
export OCR_OUTPUT_ROOT="crawlers/output/ocr_runs/unlimited_ocr_modal/raw/audit_pdf_chunks_target2500_20260624"

python scripts/ocr_modal_run_chunk.py \
  --url "$OCR_URL" \
  --chunk crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/chunks/chunk_0000.jsonl \
  --output-root "$OCR_OUTPUT_ROOT" \
  --page-window-size 4 \
  --mode pages \
  --dpi 300 \
  --timeout 1800
```

The runner writes files like:

```text
$OCR_OUTPUT_ROOT/chunk_0000/<bucket>/<pdf_id>_<slug>/pages_0001_0004.raw.json
$OCR_OUTPUT_ROOT/chunk_0000/<bucket>/<pdf_id>_<slug>/pages_0001_0004.summary.json
$OCR_OUTPUT_ROOT/chunk_0000/<bucket>/<pdf_id>_<slug>/pdf_status.json
$OCR_OUTPUT_ROOT/chunk_0000/chunk_progress.jsonl
$OCR_OUTPUT_ROOT/chunk_0000/chunk_summary.json
```

Run all chunks sequentially overnight:

```bash
export OCR_URL="https://<your-modal-url>.modal.run"
export OCR_API_KEY="$(cat /tmp/unlimited_ocr_api_key)"
export OCR_OUTPUT_ROOT="crawlers/output/ocr_runs/unlimited_ocr_modal/raw/audit_pdf_chunks_target2500_20260624"

nohup bash -lc '
set -euo pipefail
for chunk in crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/chunks/chunk_*.jsonl; do
  python scripts/ocr_modal_run_chunk.py \
    --url "$OCR_URL" \
    --chunk "$chunk" \
    --output-root "$OCR_OUTPUT_ROOT" \
    --page-window-size 4 \
    --mode pages \
    --dpi 300 \
    --timeout 1800
done
' > crawlers/output/ocr_runs/unlimited_ocr_modal/overnight_ocr.log 2>&1 &
```

The current Modal app is configured for one H100 with `max_containers=1`, so run
chunks sequentially unless you intentionally raise Modal capacity.

### 6. Resume Or Verify Runs

The chunk runner is resumable by default. If a
`pages_XXXX_YYYY.raw.json` file exists and parses as a completed API response,
that page window is skipped. After a network failure or timeout, rerun the same
chunk command.

Dry-run a chunk layout without API credentials:

```bash
python scripts/ocr_modal_run_chunk.py \
  --url https://example.invalid \
  --chunk crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/chunks/chunk_0000.jsonl \
  --output-root /tmp/ocr_chunk_dry_run \
  --page-window-size 4 \
  --limit 2 \
  --dry-run
```

Run a one-page API smoke test:

```bash
python scripts/ocr_modal_run_chunk.py \
  --url "$OCR_URL" \
  --chunk crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/chunks/chunk_0000.jsonl \
  --output-root /tmp/ocr_chunk_real_smoke \
  --page-start 1 \
  --page-end 1 \
  --page-window-size 1 \
  --limit 1 \
  --mode pages \
  --dpi 300 \
  --timeout 1800
```

More details live in:

- `docs/audit-pdf-to-evmbench/OCR_MODAL_SGLANG.md`
- `docs/audit-pdf-to-evmbench/OCR_OVERNIGHT_RUNS.md`
- `docs/audit-pdf-to-evmbench/POST_TRAINING_DATASET_SOURCES.md`

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
