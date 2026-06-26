from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_runner_module(project_root: Path):
    module_path = project_root / "scripts" / "ocr_modal_run.py"
    spec = importlib.util.spec_from_file_location("ocr_modal_run", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


def test_resolve_chunk_path_accepts_numeric_and_direct_paths(project_root, temp_dir):
    runner = load_runner_module(project_root)
    runner.PROJECT_ROOT = temp_dir
    runner.OCR_ROOT = Path("ocr_runs")

    chunk_id, chunk_path = runner.resolve_chunk_path("3", run_id="run_a")
    assert chunk_id == "chunk_0003"
    assert chunk_path == temp_dir / "ocr_runs" / "run_a" / "chunks" / "chunk_0003.jsonl"

    chunk_id, chunk_path = runner.resolve_chunk_path("chunk_7", run_id="run_a")
    assert chunk_id == "chunk_0007"
    assert chunk_path == temp_dir / "ocr_runs" / "run_a" / "chunks" / "chunk_0007.jsonl"

    direct = temp_dir / "custom" / "chunk_custom.jsonl"
    chunk_id, chunk_path = runner.resolve_chunk_path(str(direct), run_id="run_a")
    assert chunk_id == "chunk_custom"
    assert chunk_path == direct


def test_count_windows_respects_page_range(project_root):
    runner = load_runner_module(project_root)
    records = [{"page_count": 10}, {"page_count": 3}, {"page_count": None}]

    assert (
        runner.count_windows(
            records,
            page_start=2,
            page_end=9,
            page_window_size=4,
        )
        == 3
    )


def test_resolve_next_chunk_skips_complete_summaries(project_root, temp_dir):
    runner = load_runner_module(project_root)
    runner.PROJECT_ROOT = temp_dir
    runner.OCR_ROOT = Path("ocr_runs")
    raw_root = temp_dir / "raw" / "run_a"

    complete_records = [{"page_count": 1, "pdf_id": "a"}, {"page_count": 1, "pdf_id": "b"}]
    write_jsonl(
        temp_dir / "ocr_runs" / "run_a" / "chunks" / "chunk_0003.jsonl",
        complete_records,
    )
    write_jsonl(
        temp_dir / "ocr_runs" / "run_a" / "chunks" / "chunk_0004.jsonl",
        [{"page_count": 1, "pdf_id": "c"}],
    )
    write_json(
        raw_root / "chunk_0003" / "chunk_summary.json",
        {
            "processed_record_count": 2,
            "status_counts": {"ok": 2},
        },
    )

    chunk_id, chunk_path = runner.resolve_next_chunk(after="2", run_id="run_a", raw_root=raw_root)

    assert chunk_id == "chunk_0004"
    assert chunk_path == temp_dir / "ocr_runs" / "run_a" / "chunks" / "chunk_0004.jsonl"


def test_read_new_progress_events_starts_from_existing_offset(project_root, temp_dir):
    runner = load_runner_module(project_root)
    progress_path = temp_dir / "chunk_progress.jsonl"
    progress_path.write_text(json.dumps({"status": "old"}) + "\n", encoding="utf-8")
    offset = progress_path.stat().st_size

    handle, _ = runner.open_progress_file(progress_path, offset)
    with progress_path.open("a", encoding="utf-8") as writer:
        writer.write(json.dumps({"status": "ok", "rel_path": "a.pdf"}) + "\n")
        writer.write(json.dumps({"status": "skipped_existing", "rel_path": "b.pdf"}) + "\n")

    events = runner.read_new_progress_events(handle)
    handle.close()

    assert [event["status"] for event in events] == ["ok", "skipped_existing"]
    assert events[0]["rel_path"] == "a.pdf"


def test_prepare_single_pdf_chunk_writes_resumable_manifest(project_root, temp_dir, monkeypatch):
    runner = load_runner_module(project_root)
    runner.PROJECT_ROOT = temp_dir
    runner.OCR_ROOT = Path("ocr_runs")
    monkeypatch.setattr(runner, "pdfinfo_page_count", lambda path: 7)

    pdf_path = temp_dir / "reports" / "sample audit.pdf"
    pdf_path.parent.mkdir(parents=True)
    pdf_path.write_bytes(b"%PDF-1.4\n")

    chunk_id, chunk_path = runner.prepare_single_pdf_chunk(
        pdf_path=pdf_path,
        run_id="ad_hoc",
        chunk_id=None,
        pdf_id=None,
        bucket="ad_hoc_pdf",
    )

    records = [json.loads(line) for line in chunk_path.read_text(encoding="utf-8").splitlines()]
    assert chunk_id.startswith("single_sample_audit_")
    assert chunk_path == temp_dir / "ocr_runs" / "ad_hoc" / "chunks" / f"{chunk_id}.jsonl"
    assert records[0]["chunk_id"] == chunk_id
    assert records[0]["pdf_id"].startswith("pdf_ad_hoc_")
    assert records[0]["page_count"] == 7
    assert records[0]["bucket"] == "ad_hoc_pdf"
    assert records[0]["abs_path"] == str(pdf_path.resolve())
