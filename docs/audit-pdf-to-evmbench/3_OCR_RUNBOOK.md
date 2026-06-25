# OCR Runbook

This is the operational runbook for the current OCR portion of the experiment: deploy/check the Modal service, create chunks, run chunks, resume failed work, and materialize raw responses into downstream page records.

## Current Objects And Artifacts

- Modal app: `unlimited-ocr-sglang`.
- Model: `baidu/Unlimited-OCR`, served as `Unlimited-OCR` through SGLang.
- Current chunk plan: `crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624`.
- Current raw output root for that plan: `crawlers/output/ocr_runs/unlimited_ocr_modal/raw/audit_pdf_chunks_target2500_20260624`.
- Current materialized output root for that plan: `crawlers/output/ocr_runs/unlimited_ocr_modal/artifacts/audit_pdf_chunks_target2500_20260624`.
- Current scripts: `scripts/ocr_pdf_make_chunks.py`, `scripts/ocr_modal_run_chunk.py`, `scripts/ocr_modal_client.py`, and `scripts/ocr_modal_materialize_pages.py`.

## Future OCR Work

- Decide whether long-term OCR should retain rendered page images or only checksums plus OCR text.
- Tune prompt, page-window size, and mode once finding extraction quality is measured.
- Add stronger OCR quality metrics if confidence-like signals become available.
- Increase Modal capacity only if parallel chunk runners are needed.

## Modal SGLang Unlimited-OCR Service
This document describes the OCR service added in `modal_apps/unlimited_ocr_sglang.py`.
It exposes OCR-specific JSON endpoints on Modal and keeps the SGLang OpenAI-compatible
server private on `127.0.0.1:10000` inside the same container.

## Service

- Modal app: `unlimited-ocr-sglang`
- Model: `baidu/Unlimited-OCR`
- Served model name: `Unlimited-OCR`
- Backend: `sglang`
- Endpoint version: `modal-sglang-unlimited-ocr-v1`
- GPU: one cold `H100` container, `min_containers=0`
- Auth: `Authorization: Bearer <OCR_API_KEY>`
- Secret: Modal Secret `unlimited-ocr-api` with key `OCR_API_KEY`
- Hugging Face cache: Modal Volume `huggingface-cache`

The image uses CUDA 12.9 with Python 3.12, clones `baidu/Unlimited-OCR` at commit
`7e98affeacba24e95562fbaa234ddb89b856874a`, installs the repository SGLang wheel,
and pins `kernels==0.11.7` and `pymupdf==1.27.2.2`.

## Setup

Create the API key secret:

```shell
modal secret create unlimited-ocr-api OCR_API_KEY='<token>'
```

Serve locally through Modal while iterating:

```shell
modal serve modal_apps/unlimited_ocr_sglang.py
```

Deploy persistently:

```shell
modal deploy modal_apps/unlimited_ocr_sglang.py
```

Use the URL printed by `modal serve` or `modal deploy` as `OCR_URL`.

## Endpoints

### `GET /health`

Requires bearer auth. Returns readiness and backend metadata:

```json
{
  "ready": true,
  "model": "Unlimited-OCR",
  "model_id": "baidu/Unlimited-OCR",
  "backend": "sglang",
  "endpoint_version": "modal-sglang-unlimited-ocr-v1",
  "sglang": {"ready": true, "status_code": 200, "url": "http://127.0.0.1:10000/health"}
}
```

### `POST /v1/ocr/image`

`multipart/form-data` fields:

- `file`: image upload.
- `prompt`: optional, default `document parsing.`
- `image_mode`: optional, `gundam` or `base`, default `gundam`
- `ngram_window`: optional, default `128`

### `POST /v1/ocr/pdf`

`multipart/form-data` fields:

- `file`: PDF upload.
- `page_start`: optional one-based start page.
- `page_end`: optional one-based end page, inclusive.
- `mode`: optional, `document` or `pages`, default `document`
- `dpi`: optional, default `300`
- `image_mode`: optional, must be `base`, default `base`
- `prompt`: optional, default `Multi page parsing.`
- `ngram_window`: optional, default `1024`

`mode=document` renders the selected pages and sends them as one multimodal SGLang
request. `mode=pages` sends one request per rendered page and returns page-level
OCR records suitable for `extracted_pages/<pdf_id>.jsonl`.

## Response Shape

Both OCR endpoints return:

```json
{
  "id": "ocr_<uuid>",
  "model": "Unlimited-OCR",
  "backend": "sglang",
  "endpoint_version": "modal-sglang-unlimited-ocr-v1",
  "source": {
    "filename": "report.pdf",
    "sha256": "...",
    "page_count": 12,
    "selected_pages": [1, 2]
  },
  "settings": {
    "dpi": 300,
    "image_mode": "base",
    "mode": "pages",
    "ngram_size": 35,
    "ngram_window": 1024,
    "prompt": "Multi page parsing."
  },
  "text": "...",
  "pages": [{"page_number": 1, "image_sha256": "...", "text": "..."}],
  "warnings": [],
  "timing_ms": {"total": 0}
}
```

## Smoke Test

The workspace smoke-test PDF is:

```text
crawlers/output/repos/audit_repos/sherlock-reports/audits/2024.06.09 - Final - Telcoin Wallet Audit Report.pdf
```

Run a health check:

```shell
export OCR_API_KEY='<token>'
export OCR_URL='https://your-modal-url'
python scripts/ocr_modal_client.py --url "$OCR_URL" --health
```

Verify unauthorized requests return `401`, then OCR pages 1-2:

```shell
python scripts/ocr_modal_client.py \
  --url "$OCR_URL" \
  --check-unauthorized \
  --kind pdf \
  --mode pages \
  --page-start 1 \
  --page-end 2 \
  "crawlers/output/repos/audit_repos/sherlock-reports/audits/2024.06.09 - Final - Telcoin Wallet Audit Report.pdf"
```

The successful response should include:

- `source.sha256`
- `source.selected_pages` equal to `[1, 2]`
- `model`, `backend`, and `endpoint_version`
- non-empty `text`
- page records with `page_number`, `image_sha256`, and `text`

## Direct Curl Examples

```shell
curl -fsS "$OCR_URL/health" \
  -H "Authorization: Bearer $OCR_API_KEY"
```

```shell
curl -fsS "$OCR_URL/v1/ocr/pdf" \
  -H "Authorization: Bearer $OCR_API_KEY" \
  -F "file=@crawlers/output/repos/audit_repos/sherlock-reports/audits/2024.06.09 - Final - Telcoin Wallet Audit Report.pdf" \
  -F "mode=pages" \
  -F "page_start=1" \
  -F "page_end=2"
```

## Upstream References

- Unlimited-OCR repository: <https://github.com/baidu/Unlimited-OCR>
- Unlimited-OCR model: <https://huggingface.co/baidu/Unlimited-OCR>
- Modal web functions: <https://modal.com/docs/guide/webhooks>
- Modal SGLang example: <https://modal.com/docs/examples/sglang_low_latency>
- SGLang vision API: <https://docs.sglang.io/docs/basic_usage/openai_api_vision>


## Overnight Chunk Runs
This workflow splits the audit-report PDFs into balanced chunks and runs the Modal `/v1/ocr/pdf` endpoint in resumable page windows.

## Generated Chunk Plan

Current plan:

- Plan directory: `crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624`
- Manifest: `crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/manifest.jsonl`
- Chunk index: `crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/chunks/chunks_index.json`
- Excluded manifest: `crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/excluded.jsonl`

Inventory:

- Total PDFs under `crawlers/output/repos/audit_repos`: 4,074
- Audit-report candidate PDFs: 4,036
- Excluded coverage-agreement PDFs: 38
- Candidate pages: 76,894
- Chunks: 31
- Typical chunk size: about 2,480 pages

Coverage agreements are excluded by default because they are not audit reports. Regenerate with `--include-excluded` if they should be OCRed too.

## Regenerate Chunks

```bash
python scripts/ocr_pdf_make_chunks.py \
  --run-id audit_pdf_chunks_target2500_20260624 \
  --target-pages-per-chunk 2500 \
  --max-pdfs-per-chunk 300 \
  --force
```

Use `--chunk-count N` instead of `--target-pages-per-chunk` if you want an exact number of chunks.

## Run One Chunk

```bash
export OCR_URL="https://pranay5255-80470--unlimited-ocr-sglang-create-asgi-app.modal.run"
export OCR_API_KEY="..."
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

The runner writes raw API responses like:

```text
$OCR_OUTPUT_ROOT/chunk_0000/<bucket>/<pdf_id>_<slug>/pages_0001_0004.raw.json
```

It also writes per-window summaries, `pdf_status.json` per PDF, `chunk_progress.jsonl`, and `chunk_summary.json` per chunk.

## Run All Chunks Sequentially

```bash
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
```

Run one chunk at a time with the current Modal app because it is configured with one H100 and `max_containers=1`. Parallel chunk runners will contend for the same deployed service unless the Modal app capacity is changed.

## Resume Behavior

The runner is resumable by default. If a `pages_XXXX_YYYY.raw.json` exists and parses as a completed API response, that page window is skipped. Rerun the same chunk command after network failures or timeouts.

Use `--no-resume` only when you intentionally want to overwrite existing raw responses.

## Small Verification Commands

Dry-run chunk layout without API credentials:

```bash
python scripts/ocr_modal_run_chunk.py \
  --url https://example.invalid \
  --chunk crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/chunks/chunk_0000.jsonl \
  --output-root /tmp/ocr_chunk_dry_run \
  --page-window-size 4 \
  --limit 2 \
  --dry-run
```

One-PDF, one-page API smoke:

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


## Materialize Raw Responses

After chunk runs write raw responses, convert them into downstream page-level JSONL records:

```bash
export OCR_RUN_ID="audit_pdf_chunks_target2500_20260624"
export OCR_RAW_ROOT="crawlers/output/ocr_runs/unlimited_ocr_modal/raw/$OCR_RUN_ID"
export OCR_ARTIFACT_ROOT="crawlers/output/ocr_runs/unlimited_ocr_modal/artifacts/$OCR_RUN_ID"

python scripts/ocr_modal_materialize_pages.py \
  --raw-root "$OCR_RAW_ROOT" \
  --artifact-root "$OCR_ARTIFACT_ROOT"
```

Materialize a single chunk when debugging or recovering a partial run:

```bash
python scripts/ocr_modal_materialize_pages.py \
  --raw-root "$OCR_RAW_ROOT" \
  --artifact-root "$OCR_ARTIFACT_ROOT" \
  --chunk-id chunk_0000
```

The command writes:

```text
$OCR_ARTIFACT_ROOT/extracted_pages/<pdf_id>.jsonl
$OCR_ARTIFACT_ROOT/materialize_summary.json
```

Default artifact-root behavior:

- If `--raw-root` ends in `raw`, the script creates a timestamped sibling under `artifacts/materialized_<timestamp>`.
- If `--raw-root` is a specific run directory such as `.../raw/audit_pdf_chunks_target2500_20260624`, the default artifact root is `.../artifacts/audit_pdf_chunks_target2500_20260624`.

## Verify Materialization

Run the unit test for the materializer:

```bash
pytest tests/test_ocr_modal_materialize_pages.py
```

Inspect summary counts after a real run:

```bash
python -m json.tool "$OCR_ARTIFACT_ROOT/materialize_summary.json" | head -n 80
```

Check generated page files:

```bash
find "$OCR_ARTIFACT_ROOT/extracted_pages" -name '*.jsonl' | head
wc -l "$OCR_ARTIFACT_ROOT"/extracted_pages/*.jsonl
```

The downstream pipeline should consume `extracted_pages/<pdf_id>.jsonl`, not the raw `pages_XXXX_YYYY.raw.json` files directly.
