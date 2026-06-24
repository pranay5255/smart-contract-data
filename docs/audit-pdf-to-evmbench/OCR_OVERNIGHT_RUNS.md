# Modal OCR Overnight Runs

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
python scripts/ocr_pdf_make_chunks.py   --run-id audit_pdf_chunks_target2500_20260624   --target-pages-per-chunk 2500   --max-pdfs-per-chunk 300   --force
```

Use `--chunk-count N` instead of `--target-pages-per-chunk` if you want an exact number of chunks.

## Run One Chunk

```bash
export OCR_URL="https://pranay5255-80470--unlimited-ocr-sglang-create-asgi-app.modal.run"
export OCR_API_KEY="..."
export OCR_OUTPUT_ROOT="crawlers/output/ocr_runs/unlimited_ocr_modal/raw/audit_pdf_chunks_target2500_20260624"

python scripts/ocr_modal_run_chunk.py   --url "$OCR_URL"   --chunk crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/chunks/chunk_0000.jsonl   --output-root "$OCR_OUTPUT_ROOT"   --page-window-size 4   --mode pages   --dpi 300   --timeout 1800
```

The runner writes raw API responses like:

```text
$OCR_OUTPUT_ROOT/chunk_0000/<bucket>/<pdf_id>_<slug>/pages_0001_0004.raw.json
```

It also writes per-window summaries, `pdf_status.json` per PDF, `chunk_progress.jsonl`, and `chunk_summary.json` per chunk.

## Run All Chunks Sequentially

```bash
for chunk in crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/chunks/chunk_*.jsonl; do
  python scripts/ocr_modal_run_chunk.py     --url "$OCR_URL"     --chunk "$chunk"     --output-root "$OCR_OUTPUT_ROOT"     --page-window-size 4     --mode pages     --dpi 300     --timeout 1800
done
```

Run one chunk at a time with the current Modal app because it is configured with one H100 and `max_containers=1`. Parallel chunk runners will contend for the same deployed service unless the Modal app capacity is changed.

## Resume Behavior

The runner is resumable by default. If a `pages_XXXX_YYYY.raw.json` exists and parses as a completed API response, that page window is skipped. Rerun the same chunk command after network failures or timeouts.

Use `--no-resume` only when you intentionally want to overwrite existing raw responses.

## Small Verification Commands

Dry-run chunk layout without API credentials:

```bash
python scripts/ocr_modal_run_chunk.py   --url https://example.invalid   --chunk crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/chunks/chunk_0000.jsonl   --output-root /tmp/ocr_chunk_dry_run   --page-window-size 4   --limit 2   --dry-run
```

One-PDF, one-page API smoke:

```bash
python scripts/ocr_modal_run_chunk.py   --url "$OCR_URL"   --chunk crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624/chunks/chunk_0000.jsonl   --output-root /tmp/ocr_chunk_real_smoke   --page-start 1   --page-end 1   --page-window-size 1   --limit 1   --mode pages   --dpi 300   --timeout 1800
```
