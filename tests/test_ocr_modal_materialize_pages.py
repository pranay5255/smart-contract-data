from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def load_materializer_module(project_root: Path):
    module_path = project_root / "scripts" / "ocr_modal_materialize_pages.py"
    spec = importlib.util.spec_from_file_location("ocr_modal_materialize_pages", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_materialize_pages_writes_extracted_page_jsonl(project_root, temp_dir):
    materializer = load_materializer_module(project_root)
    raw_root = temp_dir / "raw" / "test_run"
    pdf_dir = raw_root / "chunk_0000" / "sherlock_reports_audits" / "pdf_000001_report"
    artifact_root = temp_dir / "artifacts" / "test_run"

    write_json(
        pdf_dir / "pdf_manifest.json",
        {
            "pdf_id": "pdf_000001_deadbeef",
            "chunk_id": "chunk_0000",
            "rel_path": "sherlock-reports/audits/report.pdf",
            "abs_path": "/tmp/report.pdf",
            "filename": "report.pdf",
            "bucket": "sherlock_reports/audits",
            "page_count": 12,
        },
    )
    write_json(
        pdf_dir / "pages_0001_0002.raw.json",
        {
            "id": "ocr_123",
            "model": "Unlimited-OCR",
            "backend": "sglang",
            "endpoint_version": "modal-sglang-unlimited-ocr-v1",
            "source": {
                "filename": "report.pdf",
                "sha256": "pdfsha",
                "page_count": 12,
                "selected_pages": [1, 2],
            },
            "settings": {"mode": "pages", "dpi": 300},
            "warnings": [],
            "pages": [
                {
                    "page_number": 1,
                    "image_sha256": "imagesha1",
                    "text": "First page text",
                    "timing_ms": {"sglang_total": 10},
                    "usage": {"completion_tokens": 4},
                },
                {
                    "page_number": 2,
                    "image_sha256": "imagesha2",
                    "text": "Second page text",
                    "throughput": {"output_units_per_second": 1.5},
                },
            ],
        },
    )

    summary = materializer.materialize_pages(raw_root=raw_root, artifact_root=artifact_root)

    output_path = artifact_root / "extracted_pages" / "pdf_000001_deadbeef.jsonl"
    records = read_jsonl(output_path)
    assert summary["pdf_count"] == 1
    assert summary["page_record_count"] == 2
    assert records[0]["pdf_id"] == "pdf_000001_deadbeef"
    assert records[0]["page_number"] == 1
    assert records[0]["ocr_text"] == "First page text"
    assert records[0]["source_rel_path"] == "sherlock-reports/audits/report.pdf"
    assert records[0]["source_bucket"] == "sherlock_reports/audits"
    assert records[0]["source_pdf_sha256"] == "pdfsha"
    assert records[0]["page_image_sha256"] == "imagesha1"
    assert records[0]["ocr_model"] == "Unlimited-OCR"
    assert records[0]["ocr_backend"] == "sglang"
    assert records[0]["ocr_endpoint_version"] == "modal-sglang-unlimited-ocr-v1"
    assert records[0]["raw_response_ref"] == (
        "chunk_0000/sherlock_reports_audits/pdf_000001_report/pages_0001_0002.raw.json"
    )
    assert records[1]["page_number"] == 2
    assert records[1]["ocr_text"] == "Second page text"

