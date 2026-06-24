# Modal SGLang Unlimited-OCR

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
