# Smart Contract Security Data Crawler

A Python-based system for collecting smart contract security training data from 40+ public sources.

## Quick Start

```bash
# 1. Setup virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r crawlers/requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your API keys

# 4. Run tests
pytest tests/ -v

# 5. Check available data sources
python crawlers/run_cloner.py --summary
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
`docs/audit-pdf-to-evmbench/5_POST_TRAINING_DATASETS_AND_RECIPES.md`. The main repos are:

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

More details live in the numbered runbooks:

- `docs/audit-pdf-to-evmbench/1_OVERVIEW_AND_CURRENT_STATE.md`
- `docs/audit-pdf-to-evmbench/2_PIPELINE_AND_ARTIFACTS.md`
- `docs/audit-pdf-to-evmbench/3_OCR_RUNBOOK.md`
- `docs/audit-pdf-to-evmbench/5_POST_TRAINING_DATASETS_AND_RECIPES.md`
- `docs/audit-pdf-to-evmbench/7_AUTOMODEL_B200_POST_TRAINING.md`

---

## Developer Commands

```bash
# Install Python dependencies
pip install -r crawlers/requirements.txt

# Verify setup
python verify_setup.py

# Run tests
pytest tests/ -v

# Validate data source config
python -c "import yaml; yaml.safe_load(open('crawlers/config/sources.yaml'))"

# Reinstall JavaScript dependencies when needed
npm install
```

## Project Structure

```text
crawlers/                 Data collection package
configs/automodel_b200/   Post-training config templates
docs/audit-pdf-to-evmbench/
                          OCR, conversion, review, and training runbooks
modal_apps/               Modal services for OCR and post-training jobs
scripts/                  OCR, dataset prep, publishing, and training helpers
tests/                    Pytest coverage for OCR and training utilities
```

## Credentials

| Service | Purpose |
|---------|---------|
| GitHub | Repository metadata and cloning |
| Kaggle | Dataset downloads |
| Hugging Face | Dataset restore/publish |
| Modal | OCR and training jobs |
