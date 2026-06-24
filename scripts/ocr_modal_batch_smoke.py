#!/usr/bin/env python3
"""Sample audit PDFs and dry-run them against the Modal OCR API."""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import secrets
import time
from collections import Counter
from pathlib import Path
from typing import Any

import requests


DEFAULT_ROOT = Path("crawlers/output/repos/audit_repos")
DEFAULT_OUTPUT_DIR = Path("/tmp/unlimited_ocr_batch_smoke")


def api_key_from_args(args: argparse.Namespace) -> str:
    if args.api_key:
        return args.api_key
    api_key = os.environ.get(args.api_key_env)
    if api_key:
        return api_key
    raise SystemExit(f"Set --api-key or environment variable {args.api_key_env}")


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def classify_pdf(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    parts = rel.parts
    lowered = [part.lower() for part in parts]

    if "coverage-agreements" in lowered:
        return "excluded/coverage-agreements"
    if lowered[:1] == ["publicreports"] and len(parts) >= 2:
        return f"public_reports/{parts[1]}"
    if len(lowered) >= 3 and lowered[0] == "sherlock-reports" and lowered[1] == "audits":
        return "sherlock_reports/audits"
    return "other_audit_repo_pdfs"


def discover_pdfs(root: Path, include_excluded: bool) -> tuple[list[Path], dict[str, Any]]:
    pdfs = sorted(path for path in root.rglob("*.pdf") if path.is_file())
    buckets = Counter(classify_pdf(path, root) for path in pdfs)
    candidates = [
        path
        for path in pdfs
        if include_excluded or not classify_pdf(path, root).startswith("excluded/")
    ]
    return candidates, {
        "root": str(root),
        "total_pdfs": len(pdfs),
        "candidate_pdfs": len(candidates),
        "excluded_pdfs": len(pdfs) - len(candidates),
        "buckets": dict(sorted(buckets.items())),
    }


def request_json(
    *,
    method: str,
    url: str,
    api_key: str | None,
    timeout: int,
    **kwargs: Any,
) -> requests.Response:
    headers = kwargs.pop("headers", {})
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return requests.request(method, url, headers=headers, timeout=timeout, **kwargs)


def check_health(base_url: str, api_key: str, timeout: int) -> dict[str, Any]:
    response = request_json(
        method="GET",
        url=f"{base_url}/health",
        api_key=api_key,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def check_unauthorized(base_url: str, timeout: int) -> int:
    response = request_json(
        method="GET",
        url=f"{base_url}/health",
        api_key=None,
        timeout=timeout,
    )
    return response.status_code


def submit_pdf(
    *,
    base_url: str,
    path: Path,
    api_key: str,
    page_start: int,
    page_end: int,
    mode: str,
    dpi: int,
    timeout: int,
) -> tuple[int, dict[str, Any]]:
    data: dict[str, str | int] = {
        "mode": mode,
        "page_start": page_start,
        "page_end": page_end,
        "dpi": dpi,
    }
    with path.open("rb") as handle:
        started = time.perf_counter()
        response = request_json(
            method="POST",
            url=f"{base_url}/v1/ocr/pdf",
            api_key=api_key,
            timeout=timeout,
            data=data,
            files={"file": (path.name, handle, "application/pdf")},
        )
        elapsed_ms = int((time.perf_counter() - started) * 1000)
    response.raise_for_status()
    return elapsed_ms, response.json()


def slugify(value: str, max_length: int = 80) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return slug[:max_length] or "pdf"


def summarize_response(path: Path, bucket: str, client_elapsed_ms: int, data: dict[str, Any]) -> dict[str, Any]:
    selected_pages = data.get("source", {}).get("selected_pages") or []
    page_count = data.get("source", {}).get("page_count")
    processed_pages = len(selected_pages) or 1
    timing_ms = data.get("timing_ms", {})
    total_ms = timing_ms.get("total") if isinstance(timing_ms.get("total"), int) else client_elapsed_ms
    seconds_per_processed_page = total_ms / 1000 / processed_pages
    estimated_full_pdf_seconds = (
        round(seconds_per_processed_page * page_count, 3)
        if isinstance(page_count, int) and page_count > 0
        else None
    )
    pages = data.get("pages") or []
    page_text_lengths = [len(page.get("text") or "") for page in pages if isinstance(page, dict)]

    return {
        "path": str(path),
        "bucket": bucket,
        "status": "ok",
        "id": data.get("id"),
        "page_count": page_count,
        "selected_pages": selected_pages,
        "client_elapsed_ms": client_elapsed_ms,
        "api_timing_ms": timing_ms,
        "usage": data.get("usage", {}),
        "throughput": data.get("throughput", {}),
        "text_length": len(data.get("text") or ""),
        "page_text_lengths": page_text_lengths,
        "nonempty_pages": sum(1 for length in page_text_lengths if length > 0),
        "estimated_full_pdf_seconds": estimated_full_pdf_seconds,
        "text_preview": (data.get("text") or "")[:500],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Randomly sample audit PDFs and call /v1/ocr/pdf.")
    parser.add_argument("--url", required=True, help="Base URL from modal deploy or modal serve")
    parser.add_argument("--api-key", help="Bearer API key")
    parser.add_argument("--api-key-env", default="OCR_API_KEY")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--sample-size", type=int, default=3)
    parser.add_argument("--seed", type=int, help="Random seed; generated if omitted")
    parser.add_argument("--include-excluded", action="store_true", help="Include coverage agreements")
    parser.add_argument("--page-start", type=int, default=1)
    parser.add_argument("--page-end", type=int, default=1)
    parser.add_argument("--mode", choices=("document", "pages"), default="pages")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--check-unauthorized", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_url = normalize_base_url(args.url)
    api_key = api_key_from_args(args)
    root = args.root.resolve()
    if not root.exists():
        raise SystemExit(f"PDF root does not exist: {root}")
    if args.sample_size <= 0:
        raise SystemExit("--sample-size must be positive")
    if args.page_start <= 0 or args.page_end < args.page_start:
        raise SystemExit("Use a positive page range with page_end >= page_start")

    seed = args.seed if args.seed is not None else secrets.randbits(32)
    rng = random.Random(seed)
    candidates, segregation = discover_pdfs(root, args.include_excluded)
    if not candidates:
        raise SystemExit(f"No candidate PDFs found under {root}")

    sample_size = min(args.sample_size, len(candidates))
    sample = rng.sample(candidates, sample_size)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    unauthorized_status = None
    if args.check_unauthorized:
        unauthorized_status = check_unauthorized(base_url, args.timeout)
        if unauthorized_status != 401:
            raise SystemExit(f"Expected unauthorized /health status 401, got {unauthorized_status}")

    health = check_health(base_url, api_key, args.timeout)
    results: list[dict[str, Any]] = []
    for index, pdf_path in enumerate(sample, start=1):
        bucket = classify_pdf(pdf_path, root)
        try:
            client_elapsed_ms, response_data = submit_pdf(
                base_url=base_url,
                path=pdf_path,
                api_key=api_key,
                page_start=args.page_start,
                page_end=args.page_end,
                mode=args.mode,
                dpi=args.dpi,
                timeout=args.timeout,
            )
            response_path = args.output_dir / f"{index:02d}_{slugify(pdf_path.stem)}.json"
            response_path.write_text(
                json.dumps(response_data, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            summary = summarize_response(pdf_path, bucket, client_elapsed_ms, response_data)
            summary["response_path"] = str(response_path)
        except Exception as exc:  # noqa: BLE001 - CLI should keep the batch moving.
            summary = {
                "path": str(pdf_path),
                "bucket": bucket,
                "status": "error",
                "error": str(exc),
            }
        results.append(summary)

    summary_data = {
        "base_url": base_url,
        "endpoint": "/v1/ocr/pdf",
        "health": health,
        "unauthorized_health_status": unauthorized_status,
        "segregation": segregation,
        "sample": {
            "seed": seed,
            "sample_size": sample_size,
            "paths": [str(path) for path in sample],
        },
        "request": {
            "mode": args.mode,
            "page_start": args.page_start,
            "page_end": args.page_end,
            "dpi": args.dpi,
        },
        "results": results,
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary_data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary_data["summary_path"] = str(summary_path)
    print(json.dumps(summary_data, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
