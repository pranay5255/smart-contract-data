#!/usr/bin/env python3
"""Create deterministic OCR work chunks for audit PDFs."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path("crawlers/output/repos/audit_repos")
DEFAULT_OUTPUT_ROOT = Path("crawlers/output/ocr_runs/unlimited_ocr_modal")
DEFAULT_TARGET_PAGES_PER_CHUNK = 2500


def slugify(value: str, max_length: int = 96) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")
    return slug[:max_length] or "item"


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


def pdfinfo_page_count(path: Path, timeout: int) -> tuple[int | None, str | None]:
    try:
        completed = subprocess.run(
            ["pdfinfo", str(path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return None, "pdfinfo not found; install poppler-utils or provide page counts another way"
    except subprocess.TimeoutExpired:
        return None, f"pdfinfo timed out after {timeout}s"

    output = completed.stdout + "\n" + completed.stderr
    match = re.search(r"^Pages:\s+(\d+)\s*$", output, re.MULTILINE)
    if match:
        return int(match.group(1)), None
    message = output.strip().splitlines()[-1] if output.strip() else f"pdfinfo exited {completed.returncode}"
    return None, message


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(block_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def make_record(
    *,
    path: Path,
    root: Path,
    ordinal: int,
    pdfinfo_timeout: int,
    compute_sha256: bool,
) -> dict[str, Any]:
    rel_path = path.relative_to(root).as_posix()
    stat = path.stat()
    bucket = classify_pdf(path, root)
    page_count, page_count_error = pdfinfo_page_count(path, pdfinfo_timeout)
    record = {
        "pdf_id": f"pdf_{ordinal:06d}_{hashlib.sha1(rel_path.encode('utf-8')).hexdigest()[:12]}",
        "rel_path": rel_path,
        "abs_path": str(path.resolve()),
        "filename": path.name,
        "stem": path.stem,
        "bucket": bucket,
        "excluded": bucket.startswith("excluded/"),
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "page_count": page_count,
        "page_count_error": page_count_error,
    }
    if compute_sha256:
        record["sha256"] = sha256_file(path)
    return record


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def determine_chunk_count(records: list[dict[str, Any]], args: argparse.Namespace) -> int:
    if args.chunk_count:
        return args.chunk_count
    known_pages = [record["page_count"] for record in records if isinstance(record.get("page_count"), int)]
    total_pages = sum(known_pages)
    if total_pages <= 0:
        return max(1, math.ceil(len(records) / args.max_pdfs_per_chunk))
    return max(1, math.ceil(total_pages / args.target_pages_per_chunk))


def assign_chunks(records: list[dict[str, Any]], chunk_count: int, max_pdfs_per_chunk: int) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = [[] for _ in range(chunk_count)]
    chunk_pages = [0 for _ in range(chunk_count)]
    chunk_sizes = [0 for _ in range(chunk_count)]

    def sort_key(record: dict[str, Any]) -> tuple[int, int, str]:
        page_count = record.get("page_count") if isinstance(record.get("page_count"), int) else 0
        return (-page_count, -int(record.get("size_bytes") or 0), record["rel_path"])

    for record in sorted(records, key=sort_key):
        eligible = [index for index, chunk in enumerate(chunks) if len(chunk) < max_pdfs_per_chunk]
        if not eligible:
            chunks.append([])
            chunk_pages.append(0)
            chunk_sizes.append(0)
            eligible = [len(chunks) - 1]
        target_index = min(eligible, key=lambda i: (chunk_pages[i], len(chunks[i]), chunk_sizes[i], i))
        chunks[target_index].append(record)
        chunk_pages[target_index] += record.get("page_count") if isinstance(record.get("page_count"), int) else 1
        chunk_sizes[target_index] += int(record.get("size_bytes") or 0)

    return chunks


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    bucket_counts = Counter(record["bucket"] for record in records)
    known_page_counts = [record["page_count"] for record in records if isinstance(record.get("page_count"), int)]
    return {
        "pdf_count": len(records),
        "known_page_count_pdfs": len(known_page_counts),
        "unknown_page_count_pdfs": len(records) - len(known_page_counts),
        "total_known_pages": sum(known_page_counts),
        "total_size_bytes": sum(int(record.get("size_bytes") or 0) for record in records),
        "bucket_counts": dict(sorted(bucket_counts.items())),
    }


def chunk_summary(chunk_id: str, records: list[dict[str, Any]], path: Path) -> dict[str, Any]:
    summary = summarize_records(records)
    summary.update(
        {
            "chunk_id": chunk_id,
            "chunk_path": str(path),
            "first_rel_path": records[0]["rel_path"] if records else None,
            "last_rel_path": records[-1]["rel_path"] if records else None,
        }
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create balanced OCR chunks for audit PDFs.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", help="Output subdirectory name. Defaults to UTC timestamp.")
    parser.add_argument("--chunk-count", type=int, help="Fixed number of chunks to create.")
    parser.add_argument(
        "--target-pages-per-chunk",
        type=int,
        default=DEFAULT_TARGET_PAGES_PER_CHUNK,
        help="Used when --chunk-count is omitted.",
    )
    parser.add_argument("--max-pdfs-per-chunk", type=int, default=300)
    parser.add_argument("--include-excluded", action="store_true", help="Include coverage agreements in run chunks.")
    parser.add_argument("--compute-sha256", action="store_true", help="Hash every PDF while planning.")
    parser.add_argument("--pdfinfo-timeout", type=int, default=30)
    parser.add_argument("--force", action="store_true", help="Allow writing into an existing run directory.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = args.root.resolve()
    if not root.exists():
        raise SystemExit(f"PDF root does not exist: {root}")
    if args.chunk_count is not None and args.chunk_count <= 0:
        raise SystemExit("--chunk-count must be positive")
    if args.target_pages_per_chunk <= 0:
        raise SystemExit("--target-pages-per-chunk must be positive")
    if args.max_pdfs_per_chunk <= 0:
        raise SystemExit("--max-pdfs-per-chunk must be positive")

    run_id = args.run_id or datetime.now(timezone.utc).strftime("chunk_plan_%Y%m%dT%H%M%SZ")
    run_dir = args.output_root / run_id
    if run_dir.exists() and not args.force:
        raise SystemExit(f"Output directory already exists: {run_dir}; pass --force to overwrite files")
    chunks_dir = run_dir / "chunks"
    chunks_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths = sorted(path for path in root.rglob("*.pdf") if path.is_file())
    all_records = [
        make_record(
            path=path,
            root=root,
            ordinal=index,
            pdfinfo_timeout=args.pdfinfo_timeout,
            compute_sha256=args.compute_sha256,
        )
        for index, path in enumerate(pdf_paths, start=1)
    ]
    run_records = [record for record in all_records if args.include_excluded or not record["excluded"]]
    excluded_records = [record for record in all_records if record["excluded"] and not args.include_excluded]

    chunk_count = determine_chunk_count(run_records, args)
    chunks = assign_chunks(run_records, chunk_count, args.max_pdfs_per_chunk)

    manifest_path = run_dir / "manifest.jsonl"
    excluded_path = run_dir / "excluded.jsonl"
    write_jsonl(manifest_path, run_records)
    write_jsonl(excluded_path, excluded_records)

    chunk_index: list[dict[str, Any]] = []
    for index, records in enumerate(chunks):
        chunk_id = f"chunk_{index:04d}"
        chunk_path = chunks_dir / f"{chunk_id}.jsonl"
        for record in records:
            record["chunk_id"] = chunk_id
        records.sort(key=lambda record: record["rel_path"])
        write_jsonl(chunk_path, records)
        summary = chunk_summary(chunk_id, records, chunk_path)
        write_json(chunks_dir / f"{chunk_id}.summary.json", summary)
        chunk_index.append(summary)

    summary = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "run_dir": str(run_dir),
        "manifest_path": str(manifest_path),
        "excluded_path": str(excluded_path),
        "include_excluded": args.include_excluded,
        "chunk_count": len(chunks),
        "target_pages_per_chunk": args.target_pages_per_chunk if not args.chunk_count else None,
        "max_pdfs_per_chunk": args.max_pdfs_per_chunk,
        "all_pdfs": summarize_records(all_records),
        "run_pdfs": summarize_records(run_records),
        "excluded_pdfs": summarize_records(excluded_records),
        "chunks": chunk_index,
    }
    write_json(run_dir / "summary.json", summary)
    write_json(chunks_dir / "chunks_index.json", chunk_index)

    commands = (
        "# Fill in OCR_URL and OCR_API_KEY before running.\n"
        "export OCR_URL=\"https://YOUR-MODAL-APP.modal.run\"\n"
        "export OCR_API_KEY=\"...\"\n"
        f"export OCR_OUTPUT_ROOT=\"{run_dir}/raw\"\n\n"
        "# Run one chunk. The runner is resumable; rerun the same command after failures.\n"
        f"python scripts/ocr_modal_run_chunk.py --url \"$OCR_URL\" --chunk \"{chunks_dir}/chunk_0000.jsonl\" --output-root \"$OCR_OUTPUT_ROOT\" --page-window-size 4 --mode pages --dpi 300\n\n"
        "# Run all chunks sequentially on one Modal H100. Do not parallelize unless max_containers/GPU capacity is raised.\n"
        f"for chunk in \"{chunks_dir}\"/chunk_*.jsonl; do\n"
        "  python scripts/ocr_modal_run_chunk.py --url \"$OCR_URL\" --chunk \"$chunk\" --output-root \"$OCR_OUTPUT_ROOT\" --page-window-size 4 --mode pages --dpi 300\n"
        "done\n"
    )
    (run_dir / "commands.sh").write_text(commands, encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
