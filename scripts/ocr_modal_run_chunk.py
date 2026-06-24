#!/usr/bin/env python3
"""Run one planned OCR PDF chunk against the Modal API and store raw responses."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


DEFAULT_OUTPUT_ROOT = Path("crawlers/output/ocr_runs/unlimited_ocr_modal/raw")


def api_key_from_args(args: argparse.Namespace) -> str:
    if args.api_key:
        return args.api_key
    api_key = os.environ.get(args.api_key_env)
    if api_key:
        return api_key
    raise SystemExit(f"Set --api-key or environment variable {args.api_key_env}")


def normalize_base_url(url: str) -> str:
    return url.rstrip("/")


def slugify(value: str, max_length: int = 96) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return slug[:max_length] or "item"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return records


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(data, sort_keys=True) + "\n")


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
    response = request_json(method="GET", url=f"{base_url}/health", api_key=api_key, timeout=timeout)
    response.raise_for_status()
    return response.json()


def submit_pdf_window(
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


def page_windows(page_count: int, start: int, end: int | None, window_size: int) -> list[tuple[int, int]]:
    last_page = min(page_count, end or page_count)
    if start < 1 or start > last_page:
        return []
    windows: list[tuple[int, int]] = []
    current = start
    while current <= last_page:
        window_end = min(last_page, current + window_size - 1)
        windows.append((current, window_end))
        current = window_end + 1
    return windows


def response_complete(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return bool(data.get("id") and data.get("source"))


def summarize_raw_response(client_elapsed_ms: int, response: dict[str, Any]) -> dict[str, Any]:
    pages = response.get("pages") or []
    page_text_lengths = [len(page.get("text") or "") for page in pages if isinstance(page, dict)]
    return {
        "id": response.get("id"),
        "source": response.get("source", {}),
        "settings": response.get("settings", {}),
        "client_elapsed_ms": client_elapsed_ms,
        "timing_ms": response.get("timing_ms", {}),
        "usage": response.get("usage", {}),
        "throughput": response.get("throughput", {}),
        "text_length": len(response.get("text") or ""),
        "page_text_lengths": page_text_lengths,
        "nonempty_pages": sum(1 for length in page_text_lengths if length > 0),
        "warnings": response.get("warnings", []),
    }


def process_record(
    *,
    record: dict[str, Any],
    base_url: str,
    api_key: str,
    output_root: Path,
    page_start: int,
    page_end: int | None,
    page_window_size: int,
    mode: str,
    dpi: int,
    timeout: int,
    resume: bool,
    dry_run: bool,
    progress_path: Path,
) -> dict[str, Any]:
    pdf_path = Path(record.get("abs_path") or record.get("path") or "")
    pdf_id = record.get("pdf_id") or slugify(record.get("rel_path") or pdf_path.stem)
    chunk_id = record.get("chunk_id") or "chunk_unknown"
    safe_bucket = slugify(record.get("bucket") or "unknown_bucket", max_length=64)
    pdf_dir = output_root / chunk_id / safe_bucket / f"{pdf_id}_{slugify(pdf_path.stem, 64)}"
    page_count = record.get("page_count")

    base_status = {
        "pdf_id": pdf_id,
        "chunk_id": chunk_id,
        "rel_path": record.get("rel_path"),
        "abs_path": str(pdf_path),
        "bucket": record.get("bucket"),
        "page_count": page_count,
        "output_dir": str(pdf_dir),
    }

    if not pdf_path.exists():
        return {**base_status, "status": "error", "error": "PDF path does not exist"}
    if not isinstance(page_count, int) or page_count <= 0:
        return {**base_status, "status": "error", "error": "Missing or invalid page_count in chunk manifest"}

    windows = page_windows(page_count, page_start, page_end, page_window_size)
    if not windows:
        return {**base_status, "status": "skipped", "reason": "No selected pages in range"}

    if dry_run:
        return {**base_status, "status": "dry_run", "windows": windows, "window_count": len(windows)}

    pdf_dir.mkdir(parents=True, exist_ok=True)
    write_json_atomic(pdf_dir / "pdf_manifest.json", record)

    completed = 0
    skipped = 0
    errors: list[dict[str, Any]] = []
    window_summaries: list[dict[str, Any]] = []
    for window_start, window_end in windows:
        raw_path = pdf_dir / f"pages_{window_start:04d}_{window_end:04d}.raw.json"
        summary_path = pdf_dir / f"pages_{window_start:04d}_{window_end:04d}.summary.json"
        if resume and response_complete(raw_path):
            skipped += 1
            event = {
                **base_status,
                "status": "skipped_existing",
                "page_start": window_start,
                "page_end": window_end,
                "raw_path": str(raw_path),
            }
            append_jsonl(progress_path, event)
            continue

        event_base = {
            **base_status,
            "page_start": window_start,
            "page_end": window_end,
            "raw_path": str(raw_path),
        }
        try:
            client_elapsed_ms, response = submit_pdf_window(
                base_url=base_url,
                path=pdf_path,
                api_key=api_key,
                page_start=window_start,
                page_end=window_end,
                mode=mode,
                dpi=dpi,
                timeout=timeout,
            )
            summary = summarize_raw_response(client_elapsed_ms, response)
            write_json_atomic(raw_path, response)
            write_json_atomic(summary_path, summary)
            completed += 1
            window_summaries.append(summary)
            append_jsonl(progress_path, {**event_base, "status": "ok", "summary": summary})
        except Exception as exc:  # noqa: BLE001 - overnight runner should continue.
            error = {**event_base, "status": "error", "error": str(exc)}
            errors.append(error)
            append_jsonl(progress_path, error)

    pdf_status = {
        **base_status,
        "status": "ok" if not errors else "partial_error",
        "window_count": len(windows),
        "completed_windows": completed,
        "skipped_existing_windows": skipped,
        "error_count": len(errors),
        "errors": errors,
        "raw_files": [
            str(pdf_dir / f"pages_{window_start:04d}_{window_end:04d}.raw.json")
            for window_start, window_end in windows
            if (pdf_dir / f"pages_{window_start:04d}_{window_end:04d}.raw.json").exists()
        ],
        "total_text_length": sum(summary.get("text_length", 0) for summary in window_summaries),
        "total_client_elapsed_ms": sum(summary.get("client_elapsed_ms", 0) for summary in window_summaries),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    write_json_atomic(pdf_dir / "pdf_status.json", pdf_status)
    return pdf_status


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one OCR chunk and write raw JSON per PDF page window.")
    parser.add_argument("--url", required=True, help="Base URL from modal deploy or modal serve")
    parser.add_argument("--api-key", help="Bearer API key")
    parser.add_argument("--api-key-env", default="OCR_API_KEY")
    parser.add_argument("--chunk", type=Path, required=True, help="Chunk JSONL from ocr_pdf_make_chunks.py")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--page-start", type=int, default=1)
    parser.add_argument("--page-end", type=int)
    parser.add_argument("--page-window-size", type=int, default=4)
    parser.add_argument("--mode", choices=("pages", "document"), default="pages")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--limit", type=int, help="Process only the first N records from the chunk")
    parser.add_argument("--start-index", type=int, default=0, help="Zero-based chunk record offset")
    parser.add_argument("--max-errors", type=int, default=50)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--no-resume", action="store_true", help="Reprocess existing raw JSON files")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-health", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.page_start <= 0:
        raise SystemExit("--page-start must be positive")
    if args.page_end is not None and args.page_end < args.page_start:
        raise SystemExit("--page-end must be >= --page-start")
    if args.page_window_size <= 0:
        raise SystemExit("--page-window-size must be positive")
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")
    if args.start_index < 0:
        raise SystemExit("--start-index must be >= 0")

    records = load_jsonl(args.chunk)
    selected = records[args.start_index :]
    if args.limit is not None:
        selected = selected[: args.limit]
    if not selected:
        raise SystemExit("No records selected from chunk")

    base_url = normalize_base_url(args.url)
    api_key = "" if args.dry_run else api_key_from_args(args)
    args.output_root.mkdir(parents=True, exist_ok=True)
    chunk_id = selected[0].get("chunk_id") or args.chunk.stem
    progress_path = args.output_root / str(chunk_id) / "chunk_progress.jsonl"

    health = None
    if not args.skip_health and not args.dry_run:
        health = check_health(base_url, api_key, args.timeout)

    started_at = time.perf_counter()
    statuses: list[dict[str, Any]] = []
    hard_errors = 0
    for index, record in enumerate(selected, start=args.start_index):
        status = process_record(
            record=record,
            base_url=base_url,
            api_key=api_key,
            output_root=args.output_root,
            page_start=args.page_start,
            page_end=args.page_end,
            page_window_size=args.page_window_size,
            mode=args.mode,
            dpi=args.dpi,
            timeout=args.timeout,
            resume=not args.no_resume,
            dry_run=args.dry_run,
            progress_path=progress_path,
        )
        status["chunk_record_index"] = index
        statuses.append(status)
        if status.get("status") in {"error", "partial_error"}:
            hard_errors += 1
            if hard_errors >= args.max_errors:
                break
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    counts: dict[str, int] = {}
    for status in statuses:
        key = str(status.get("status", "unknown"))
        counts[key] = counts.get(key, 0) + 1

    summary = {
        "chunk": str(args.chunk),
        "chunk_id": chunk_id,
        "base_url": base_url,
        "health": health,
        "request": {
            "mode": args.mode,
            "dpi": args.dpi,
            "page_start": args.page_start,
            "page_end": args.page_end,
            "page_window_size": args.page_window_size,
        },
        "selected_record_count": len(selected),
        "processed_record_count": len(statuses),
        "status_counts": dict(sorted(counts.items())),
        "elapsed_ms": int((time.perf_counter() - started_at) * 1000),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "statuses": statuses,
    }

    summary_path = args.output_root / str(chunk_id) / "chunk_summary.json"
    write_json_atomic(summary_path, summary)
    summary["summary_path"] = str(summary_path)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
