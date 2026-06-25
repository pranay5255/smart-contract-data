#!/usr/bin/env python3
"""Materialize page-level OCR JSONL records from raw Modal OCR responses."""

from __future__ import annotations

import argparse
import json
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RAW_ROOT = Path("crawlers/output/ocr_runs/unlimited_ocr_modal/raw")


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return data


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def write_jsonl_atomic(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    tmp_path.replace(path)


def default_artifact_root(raw_root: Path) -> Path:
    raw_root = raw_root.resolve()
    if raw_root.name == "raw":
        run_id = datetime.now(timezone.utc).strftime("materialized_%Y%m%dT%H%M%SZ")
        return raw_root.parent / "artifacts" / run_id
    return raw_root.parent.parent / "artifacts" / raw_root.name


def path_ref(path: Path, base: Path | None) -> str:
    if base is None:
        return str(path)
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return str(path)


def discover_pdf_dirs(raw_root: Path, chunk_ids: set[str] | None) -> list[Path]:
    if not raw_root.exists():
        raise FileNotFoundError(f"Raw root does not exist: {raw_root}")
    manifest_paths = sorted(raw_root.glob("chunk_*/**/pdf_manifest.json"))
    if chunk_ids:
        manifest_paths = [
            path for path in manifest_paths if path.relative_to(raw_root).parts[0] in chunk_ids
        ]
    return [path.parent for path in manifest_paths]


def page_record_from_raw(
    *,
    manifest: dict[str, Any],
    raw_response: dict[str, Any],
    raw_path: Path,
    raw_root: Path,
    created_at: str,
    page: dict[str, Any],
) -> dict[str, Any]:
    source = raw_response.get("source") if isinstance(raw_response.get("source"), dict) else {}
    settings = raw_response.get("settings") if isinstance(raw_response.get("settings"), dict) else {}
    page_number = page.get("page_number")
    if not isinstance(page_number, int):
        raise ValueError(f"Missing integer page_number in {raw_path}")

    warnings = raw_response.get("warnings")
    if not isinstance(warnings, list):
        warnings = []

    record = {
        "pdf_id": manifest.get("pdf_id"),
        "source_rel_path": manifest.get("rel_path"),
        "source_abs_path": manifest.get("abs_path"),
        "source_filename": source.get("filename") or manifest.get("filename"),
        "source_bucket": manifest.get("bucket"),
        "source_pdf_sha256": source.get("sha256") or manifest.get("sha256"),
        "source_page_count": source.get("page_count") or manifest.get("page_count"),
        "page_number": page_number,
        "page_image_sha256": page.get("image_sha256"),
        "ocr_text": page.get("text") or "",
        "ocr_model": raw_response.get("model"),
        "ocr_model_version": raw_response.get("model_id") or raw_response.get("model"),
        "ocr_backend": raw_response.get("backend"),
        "ocr_endpoint_version": raw_response.get("endpoint_version"),
        "ocr_settings": settings,
        "confidence": None,
        "warnings": warnings,
        "layout_blocks": [],
        "tables": [],
        "code_blocks": [],
        "timing_ms": page.get("timing_ms") or raw_response.get("timing_ms") or {},
        "usage": page.get("usage") or {},
        "throughput": page.get("throughput") or {},
        "raw_response_ref": path_ref(raw_path, raw_root),
        "created_at": created_at,
    }
    if not record["pdf_id"]:
        raise ValueError(f"Missing pdf_id in manifest for {raw_path}")
    return record


def materialize_pdf_dir(
    *,
    pdf_dir: Path,
    raw_root: Path,
    artifact_root: Path,
    created_at: str,
) -> dict[str, Any]:
    manifest_path = pdf_dir / "pdf_manifest.json"
    manifest = load_json(manifest_path)
    pdf_id = manifest.get("pdf_id")
    if not isinstance(pdf_id, str) or not pdf_id:
        raise ValueError(f"Missing pdf_id in {manifest_path}")

    page_records: dict[int, dict[str, Any]] = {}
    raw_files = sorted(pdf_dir.glob("pages_*.raw.json"))
    errors: list[str] = []
    for raw_path in raw_files:
        try:
            raw_response = load_json(raw_path)
            pages = raw_response.get("pages") or []
            if not isinstance(pages, list):
                raise ValueError(f"Expected list pages in {raw_path}")
            for page in pages:
                if not isinstance(page, dict):
                    continue
                record = page_record_from_raw(
                    manifest=manifest,
                    raw_response=raw_response,
                    raw_path=raw_path,
                    raw_root=raw_root,
                    created_at=created_at,
                    page=page,
                )
                page_records[int(record["page_number"])] = record
        except Exception as exc:  # noqa: BLE001 - preserve other PDFs in batch materialization.
            errors.append(str(exc))

    output_path = artifact_root / "extracted_pages" / f"{pdf_id}.jsonl"
    records = [page_records[page_number] for page_number in sorted(page_records)]
    if records:
        write_jsonl_atomic(output_path, records)

    return {
        "pdf_id": pdf_id,
        "chunk_id": manifest.get("chunk_id"),
        "rel_path": manifest.get("rel_path"),
        "pdf_dir": str(pdf_dir),
        "output_path": str(output_path) if records else None,
        "raw_file_count": len(raw_files),
        "page_record_count": len(records),
        "nonempty_page_count": sum(1 for record in records if record.get("ocr_text")),
        "errors": errors,
        "status": "ok" if records and not errors else "error" if errors else "skipped",
    }


def materialize_pages(
    *,
    raw_root: Path,
    artifact_root: Path,
    chunk_ids: set[str] | None = None,
) -> dict[str, Any]:
    raw_root = raw_root.resolve()
    artifact_root = artifact_root.resolve()
    created_at = datetime.now(timezone.utc).isoformat()
    pdf_dirs = discover_pdf_dirs(raw_root, chunk_ids)

    pdf_summaries = [
        materialize_pdf_dir(
            pdf_dir=pdf_dir,
            raw_root=raw_root,
            artifact_root=artifact_root,
            created_at=created_at,
        )
        for pdf_dir in pdf_dirs
    ]
    status_counts = Counter(summary["status"] for summary in pdf_summaries)
    chunk_counts = Counter(str(summary.get("chunk_id") or "unknown") for summary in pdf_summaries)
    summary = {
        "created_at": created_at,
        "raw_root": str(raw_root),
        "artifact_root": str(artifact_root),
        "chunk_ids": sorted(chunk_ids) if chunk_ids else None,
        "pdf_count": len(pdf_summaries),
        "status_counts": dict(sorted(status_counts.items())),
        "chunk_counts": dict(sorted(chunk_counts.items())),
        "page_record_count": sum(summary["page_record_count"] for summary in pdf_summaries),
        "nonempty_page_count": sum(summary["nonempty_page_count"] for summary in pdf_summaries),
        "pdfs": pdf_summaries,
    }
    write_json_atomic(artifact_root / "materialize_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write extracted_pages/<pdf_id>.jsonl from raw Modal OCR responses."
    )
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=DEFAULT_RAW_ROOT,
        help="Raw OCR root, usually crawlers/output/.../raw/<run_id>",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="Artifact root. Defaults to sibling artifacts/<raw_root.name>.",
    )
    parser.add_argument(
        "--chunk-id",
        action="append",
        dest="chunk_ids",
        help="Only materialize one chunk id. May be repeated.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    raw_root = args.raw_root
    artifact_root = args.artifact_root or default_artifact_root(raw_root)
    summary = materialize_pages(
        raw_root=raw_root,
        artifact_root=artifact_root,
        chunk_ids=set(args.chunk_ids) if args.chunk_ids else None,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
