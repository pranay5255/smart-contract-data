#!/usr/bin/env python3
"""Progress-enabled wrapper for Modal OCR chunk and PDF runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OCR_ROOT = Path("crawlers/output/ocr_runs/unlimited_ocr_modal")
DEFAULT_CHUNK_RUN_ID = "audit_pdf_chunks_target2500_20260624"
DEFAULT_PDF_RUN_ID = "ad_hoc_pdf_runs"
DEFAULT_URL = "https://pranay5255-80470--unlimited-ocr-sglang-create-asgi-app.modal.run"
DEFAULT_SECRET_PATH = Path("/tmp/unlimited_ocr_secret.json")


def project_path(path: Path | str) -> Path:
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def path_arg(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


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
                data = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(data, dict):
                raise SystemExit(f"Expected JSON object at {path}:{line_number}")
            records.append(data)
    return records


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


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


def count_windows(
    records: list[dict[str, Any]],
    *,
    page_start: int,
    page_end: int | None,
    page_window_size: int,
) -> int:
    total = 0
    for record in records:
        page_count = record.get("page_count")
        if isinstance(page_count, int) and page_count > 0:
            total += len(page_windows(page_count, page_start, page_end, page_window_size))
    return total


def normalize_chunk_id(value: str | int) -> str:
    text = str(value).strip()
    if re.fullmatch(r"\d+", text):
        return f"chunk_{int(text):04d}"
    if re.fullmatch(r"chunk_\d{1,}", text):
        return f"chunk_{int(text.split('_', 1)[1]):04d}"
    raise ValueError(f"Invalid chunk id: {value!r}")


def plan_root(run_id: str) -> Path:
    return project_path(OCR_ROOT / run_id)


def default_raw_root(run_id: str) -> Path:
    return project_path(OCR_ROOT / "raw" / run_id)


def default_artifact_root(run_id: str) -> Path:
    return project_path(OCR_ROOT / "artifacts" / run_id)


def default_logs_dir() -> Path:
    return project_path(OCR_ROOT / "logs")


def resolve_chunk_path(chunk: str, *, run_id: str) -> tuple[str, Path]:
    chunk_path = Path(chunk)
    if chunk_path.suffix == ".jsonl" or "/" in chunk or "\\" in chunk:
        resolved = project_path(chunk_path)
        chunk_id = resolved.stem
        return chunk_id, resolved

    chunk_id = normalize_chunk_id(chunk)
    return chunk_id, plan_root(run_id) / "chunks" / f"{chunk_id}.jsonl"


def chunk_summary_path(chunk_id: str, *, raw_root: Path) -> Path:
    return raw_root / chunk_id / "chunk_summary.json"


def chunk_is_complete(chunk_id: str, *, chunk_path: Path, raw_root: Path) -> bool:
    summary_path = chunk_summary_path(chunk_id, raw_root=raw_root)
    if not summary_path.exists():
        return False
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if not isinstance(summary, dict):
        return False

    expected_records = len(load_jsonl(chunk_path))
    processed_records = summary.get("processed_record_count")
    status_counts = summary.get("status_counts")
    if processed_records != expected_records or not isinstance(status_counts, dict):
        return False
    failing = {"error", "partial_error", "unknown"}
    return not any(int(status_counts.get(status, 0) or 0) > 0 for status in failing)


def resolve_next_chunk(*, after: str, run_id: str, raw_root: Path) -> tuple[str, Path]:
    start = int(normalize_chunk_id(after).split("_", 1)[1]) + 1
    chunks_dir = plan_root(run_id) / "chunks"
    for chunk_path in sorted(chunks_dir.glob("chunk_*.jsonl")):
        chunk_id = chunk_path.stem
        index = int(chunk_id.split("_", 1)[1])
        if index < start:
            continue
        if not chunk_is_complete(chunk_id, chunk_path=chunk_path, raw_root=raw_root):
            return chunk_id, chunk_path
    raise SystemExit(f"No incomplete chunks found after {normalize_chunk_id(after)}")


def pdfinfo_page_count(path: Path, timeout: int = 30) -> int:
    try:
        completed = subprocess.run(
            ["pdfinfo", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise SystemExit("pdfinfo not found; install poppler-utils to use PDF mode") from exc
    except subprocess.TimeoutExpired as exc:
        raise SystemExit(f"pdfinfo timed out after {timeout}s for {path}") from exc

    output = completed.stdout + "\n" + completed.stderr
    match = re.search(r"^Pages:\s+(\d+)\s*$", output, re.MULTILINE)
    if not match:
        message = output.strip().splitlines()[-1] if output.strip() else f"pdfinfo exited {completed.returncode}"
        raise SystemExit(f"Could not read page count for {path}: {message}")
    return int(match.group(1))


def make_single_pdf_record(
    *,
    pdf_path: Path,
    chunk_id: str,
    pdf_id: str,
    page_count: int,
    bucket: str,
) -> dict[str, Any]:
    resolved = pdf_path.resolve()
    stat = resolved.stat()
    try:
        rel_path = resolved.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        rel_path = resolved.name
    return {
        "pdf_id": pdf_id,
        "rel_path": rel_path,
        "abs_path": str(resolved),
        "filename": resolved.name,
        "stem": resolved.stem,
        "bucket": bucket,
        "excluded": False,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "page_count": page_count,
        "page_count_error": None,
        "chunk_id": chunk_id,
    }


def prepare_single_pdf_chunk(
    *,
    pdf_path: Path,
    run_id: str,
    chunk_id: str | None,
    pdf_id: str | None,
    bucket: str,
) -> tuple[str, Path]:
    resolved = project_path(pdf_path).resolve()
    if not resolved.exists():
        raise SystemExit(f"PDF does not exist: {resolved}")
    if resolved.suffix.lower() != ".pdf":
        raise SystemExit(f"Expected a PDF path, got: {resolved}")

    digest = hashlib.sha1(str(resolved).encode("utf-8")).hexdigest()[:12]
    final_chunk_id = chunk_id or f"single_{slugify(resolved.stem, 48)}_{digest}"
    final_pdf_id = pdf_id or f"pdf_ad_hoc_{digest}"
    page_count = pdfinfo_page_count(resolved)
    record = make_single_pdf_record(
        pdf_path=resolved,
        chunk_id=final_chunk_id,
        pdf_id=final_pdf_id,
        page_count=page_count,
        bucket=bucket,
    )
    chunk_path = plan_root(run_id) / "chunks" / f"{final_chunk_id}.jsonl"
    write_jsonl(chunk_path, [record])
    return final_chunk_id, chunk_path


def read_api_key(args: argparse.Namespace) -> str:
    if args.api_key:
        return args.api_key
    env_key = os.environ.get(args.api_key_env)
    if env_key:
        return env_key
    secret_path = project_path(args.secret_path)
    if secret_path.exists():
        try:
            data = json.loads(secret_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid OCR secret JSON at {secret_path}: {exc}") from exc
        if isinstance(data, dict) and data.get("OCR_API_KEY"):
            return str(data["OCR_API_KEY"])
    raise SystemExit(f"Set --api-key, {args.api_key_env}, or provide {secret_path}")


def build_runner_command(
    *,
    args: argparse.Namespace,
    chunk_path: Path,
    output_root: Path,
) -> list[str]:
    command = [
        sys.executable,
        "scripts/ocr_modal_run_chunk.py",
        "--url",
        args.url,
        "--api-key-env",
        "OCR_API_KEY",
        "--chunk",
        path_arg(chunk_path),
        "--output-root",
        path_arg(output_root),
        "--page-start",
        str(args.page_start),
        "--page-window-size",
        str(args.page_window_size),
        "--mode",
        args.mode,
        "--dpi",
        str(args.dpi),
        "--timeout",
        str(args.timeout),
        "--max-errors",
        str(args.max_errors),
    ]
    if args.page_end is not None:
        command.extend(["--page-end", str(args.page_end)])
    if args.sleep_seconds > 0:
        command.extend(["--sleep-seconds", str(args.sleep_seconds)])
    if args.no_resume:
        command.append("--no-resume")
    if args.skip_health:
        command.append("--skip-health")
    return command


def build_materializer_command(
    *,
    raw_root: Path,
    artifact_root: Path,
    chunk_id: str,
) -> list[str]:
    return [
        sys.executable,
        "scripts/ocr_modal_materialize_pages.py",
        "--raw-root",
        path_arg(raw_root),
        "--artifact-root",
        path_arg(artifact_root),
        "--chunk-id",
        chunk_id,
    ]


def open_progress_file(path: Path, offset: int) -> tuple[Any | None, int]:
    if not path.exists():
        return None, offset
    handle = path.open("r", encoding="utf-8")
    handle.seek(offset)
    return handle, offset


def read_new_progress_events(handle: Any | None) -> list[dict[str, Any]]:
    if handle is None:
        return []
    events: list[dict[str, Any]] = []
    while True:
        line = handle.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            events.append(data)
    return events


def short_text(value: Any, max_length: int = 72) -> str:
    text = str(value or "")
    if len(text) <= max_length:
        return text
    return "..." + text[-(max_length - 3) :]


def log_header(log_handle: Any, *, title: str, command: list[str]) -> None:
    log_handle.write("\n")
    log_handle.write("=" * 80 + "\n")
    log_handle.write(f"{title} started_at={datetime.now(timezone.utc).isoformat()}\n")
    log_handle.write("command=" + " ".join(command) + "\n")
    log_handle.write("=" * 80 + "\n")
    log_handle.flush()


def run_command_with_progress(
    *,
    args: argparse.Namespace,
    chunk_id: str,
    chunk_path: Path,
    raw_root: Path,
    artifact_root: Path,
    log_file: Path,
) -> int:
    records = load_jsonl(chunk_path)
    total_windows = count_windows(
        records,
        page_start=args.page_start,
        page_end=args.page_end,
        page_window_size=args.page_window_size,
    )
    progress_path = raw_root / chunk_id / "chunk_progress.jsonl"
    progress_offset = progress_path.stat().st_size if progress_path.exists() else 0
    runner_command = build_runner_command(args=args, chunk_path=chunk_path, output_root=raw_root)
    env = os.environ.copy()
    env["OCR_API_KEY"] = read_api_key(args)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as log_handle:
        log_header(log_handle, title=f"ocr runner {chunk_id}", command=runner_command)
        process = subprocess.Popen(
            runner_command,
            cwd=PROJECT_ROOT,
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )

        console = Console()
        counts: Counter[str] = Counter()
        latest = ""
        progress_handle = None
        completed_events = 0

        with Progress(
            TextColumn("[bold cyan]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total} windows"),
            TextColumn("ok={task.fields[ok]} skip={task.fields[skip]} err={task.fields[err]}"),
            TimeElapsedColumn(),
            TextColumn("{task.fields[latest]}"),
            console=console,
        ) as progress:
            task_id = progress.add_task(
                chunk_id,
                total=total_windows,
                ok=0,
                skip=0,
                err=0,
                latest="",
            )
            while process.poll() is None:
                if progress_handle is None and progress_path.exists():
                    progress_handle, _ = open_progress_file(progress_path, progress_offset)
                events = read_new_progress_events(progress_handle)
                if events:
                    completed_events += len(events)
                    for event in events:
                        status = str(event.get("status") or "unknown")
                        counts[status] += 1
                        latest = short_text(event.get("rel_path") or event.get("pdf_id"))
                    progress.update(
                        task_id,
                        completed=min(completed_events, total_windows),
                        ok=counts["ok"],
                        skip=counts["skipped_existing"],
                        err=counts["error"],
                        latest=latest,
                    )
                time.sleep(1)

            if progress_handle is None and progress_path.exists():
                progress_handle, _ = open_progress_file(progress_path, progress_offset)
            events = read_new_progress_events(progress_handle)
            if events:
                completed_events += len(events)
                for event in events:
                    status = str(event.get("status") or "unknown")
                    counts[status] += 1
                    latest = short_text(event.get("rel_path") or event.get("pdf_id"))
            progress.update(
                task_id,
                completed=min(completed_events, total_windows),
                ok=counts["ok"],
                skip=counts["skipped_existing"],
                err=counts["error"],
                latest=latest,
            )

        if progress_handle is not None:
            progress_handle.close()

        return_code = process.wait()
        log_handle.write(f"\nrunner_exit={return_code} finished_at={datetime.now(timezone.utc).isoformat()}\n")
        log_handle.flush()
        if return_code != 0:
            return return_code

        if not args.no_materialize:
            materializer_command = build_materializer_command(
                raw_root=raw_root,
                artifact_root=artifact_root,
                chunk_id=chunk_id,
            )
            log_header(log_handle, title=f"materialize {chunk_id}", command=materializer_command)
            materializer = subprocess.run(
                materializer_command,
                cwd=PROJECT_ROOT,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
            log_handle.write(
                f"\nmaterializer_exit={materializer.returncode} "
                f"finished_at={datetime.now(timezone.utc).isoformat()}\n"
            )
            log_handle.flush()
            return materializer.returncode

    return 0


def finalize_common_args(args: argparse.Namespace) -> argparse.Namespace:
    args.run_id = args.run_id or (DEFAULT_PDF_RUN_ID if args.command == "pdf" else DEFAULT_CHUNK_RUN_ID)
    args.url = args.url or os.environ.get("OCR_URL") or DEFAULT_URL
    args.output_root = project_path(args.output_root) if args.output_root else default_raw_root(args.run_id)
    args.artifact_root = (
        project_path(args.artifact_root) if args.artifact_root else default_artifact_root(args.run_id)
    )
    return args


def default_log_file(chunk_id: str) -> Path:
    return default_logs_dir() / f"ocr_modal_run_{chunk_id}.log"


def run_chunk(args: argparse.Namespace) -> int:
    chunk_id, chunk_path = resolve_chunk_path(args.chunk, run_id=args.run_id)
    if not chunk_path.exists():
        raise SystemExit(f"Chunk file does not exist: {chunk_path}")
    log_file = project_path(args.log_file) if args.log_file else default_log_file(chunk_id)
    return run_command_with_progress(
        args=args,
        chunk_id=chunk_id,
        chunk_path=chunk_path,
        raw_root=args.output_root,
        artifact_root=args.artifact_root,
        log_file=log_file,
    )


def run_next(args: argparse.Namespace) -> int:
    chunk_id, chunk_path = resolve_next_chunk(
        after=args.after,
        run_id=args.run_id,
        raw_root=args.output_root,
    )
    print(f"Selected {chunk_id}: {path_arg(chunk_path)}")
    log_file = project_path(args.log_file) if args.log_file else default_log_file(chunk_id)
    return run_command_with_progress(
        args=args,
        chunk_id=chunk_id,
        chunk_path=chunk_path,
        raw_root=args.output_root,
        artifact_root=args.artifact_root,
        log_file=log_file,
    )


def run_pdf(args: argparse.Namespace) -> int:
    chunk_id, chunk_path = prepare_single_pdf_chunk(
        pdf_path=args.pdf,
        run_id=args.run_id,
        chunk_id=args.chunk_id,
        pdf_id=args.pdf_id,
        bucket=args.bucket,
    )
    log_file = project_path(args.log_file) if args.log_file else default_log_file(chunk_id)
    return run_command_with_progress(
        args=args,
        chunk_id=chunk_id,
        chunk_path=chunk_path,
        raw_root=args.output_root,
        artifact_root=args.artifact_root,
        log_file=log_file,
    )


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--run-id", help="OCR run id. Defaults depend on command.")
    parser.add_argument("--url", help="Modal OCR base URL. Defaults to OCR_URL or the deployed endpoint.")
    parser.add_argument("--api-key", help="Bearer API key. Prefer OCR_API_KEY or the secret JSON file.")
    parser.add_argument("--api-key-env", default="OCR_API_KEY")
    parser.add_argument("--secret-path", type=Path, default=DEFAULT_SECRET_PATH)
    parser.add_argument("--output-root", type=Path, help="Raw OCR output root.")
    parser.add_argument("--artifact-root", type=Path, help="Materialized artifact root.")
    parser.add_argument("--page-start", type=int, default=1)
    parser.add_argument("--page-end", type=int)
    parser.add_argument("--page-window-size", type=int, default=4)
    parser.add_argument("--mode", choices=("pages", "document"), default="pages")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--max-errors", type=int, default=50)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--no-materialize", action="store_true")
    parser.add_argument("--skip-health", action="store_true")
    parser.add_argument("--log-file", type=Path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Modal OCR chunks or PDFs with a live tmux-friendly progress bar.",
        epilog=(
            "Examples:\n"
            "  python3 scripts/ocr_modal_run.py chunk 3\n"
            "  python3 scripts/ocr_modal_run.py next --after 2\n"
            "  python3 scripts/ocr_modal_run.py pdf crawlers/output/repos/audit_repos/report.pdf"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    chunk_parser = subparsers.add_parser("chunk", help="Run one planned chunk.")
    add_common_args(chunk_parser)
    chunk_parser.add_argument("chunk", help="Chunk id like 3, 0003, chunk_0003, or a chunk JSONL path.")

    next_parser = subparsers.add_parser("next", help="Run the next incomplete chunk after a chunk id.")
    add_common_args(next_parser)
    next_parser.add_argument("--after", default="2", help="Start scanning after this chunk id. Default: 2.")

    pdf_parser = subparsers.add_parser("pdf", help="Run one PDF through the resumable raw layout.")
    add_common_args(pdf_parser)
    pdf_parser.add_argument("pdf", type=Path)
    pdf_parser.add_argument("--chunk-id")
    pdf_parser.add_argument("--pdf-id")
    pdf_parser.add_argument("--bucket", default="ad_hoc_pdf")

    args = parser.parse_args()
    if args.page_start <= 0:
        raise SystemExit("--page-start must be positive")
    if args.page_end is not None and args.page_end < args.page_start:
        raise SystemExit("--page-end must be >= --page-start")
    if args.page_window_size <= 0:
        raise SystemExit("--page-window-size must be positive")
    if args.timeout <= 0:
        raise SystemExit("--timeout must be positive")
    if args.max_errors <= 0:
        raise SystemExit("--max-errors must be positive")
    if args.sleep_seconds < 0:
        raise SystemExit("--sleep-seconds must be >= 0")
    return finalize_common_args(args)


def main() -> None:
    args = parse_args()
    if args.command == "chunk":
        raise SystemExit(run_chunk(args))
    if args.command == "next":
        raise SystemExit(run_next(args))
    if args.command == "pdf":
        raise SystemExit(run_pdf(args))
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
