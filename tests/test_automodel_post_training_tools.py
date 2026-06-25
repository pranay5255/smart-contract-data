from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def load_script(project_root: Path, script_name: str):
    module_path = project_root / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(script_name.removesuffix(".py"), module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_prepare_sft_resolves_message_content_refs(project_root, temp_dir):
    prepare = load_script(project_root, "automodel_prepare_datasets.py")
    (temp_dir / "prompts").mkdir()
    (temp_dir / "findings").mkdir()
    (temp_dir / "records").mkdir()
    (temp_dir / "prompts" / "system.md").write_text("You are an audit model.", encoding="utf-8")
    (temp_dir / "findings" / "gold.md").write_text("H-01: loss of funds finding", encoding="utf-8")

    input_path = temp_dir / "records" / "detect_sft.jsonl"
    input_path.write_text(
        json.dumps(
            {
                "record_id": "sft-1",
                "task_id": "evmbench:test:detect",
                "source": "gold_audit",
                "split": "train",
                "messages": [
                    {"role": "system", "content_ref": "prompts/system.md"},
                    {"role": "user", "content": "Audit this repository."},
                    {"role": "assistant", "content_ref": "findings/gold.md"},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    output_path = temp_dir / "out" / "sft.jsonl"
    count = prepare.convert_file(
        kind="sft",
        input_path=input_path,
        output_path=output_path,
        repo_root=temp_dir,
    )

    records = read_jsonl(output_path)
    assert count == 1
    assert records[0]["record_id"] == "sft-1"
    assert records[0]["context"] == "You are an audit model."
    assert records[0]["question"] == "Audit this repository."
    assert records[0]["answer"] == "H-01: loss of funds finding"


def test_prepare_dpo_resolves_prompt_and_report_refs(project_root, temp_dir):
    prepare = load_script(project_root, "automodel_prepare_datasets.py")
    (temp_dir / "prompts").mkdir()
    (temp_dir / "reports").mkdir()
    (temp_dir / "records").mkdir()
    (temp_dir / "prompts" / "task.json").write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "system", "content": "Write an audit report."},
                    {"role": "user", "content": "Find the bug."},
                    {"role": "assistant", "content": "Do not include this old answer."},
                ]
            }
        ),
        encoding="utf-8",
    )
    (temp_dir / "reports" / "chosen.md").write_text("Correct report", encoding="utf-8")
    (temp_dir / "reports" / "rejected.md").write_text("Incorrect report", encoding="utf-8")

    input_path = temp_dir / "records" / "detect_dpo.jsonl"
    input_path.write_text(
        json.dumps(
            {
                "record_id": "dpo-1",
                "task_id": "evmbench:test:detect",
                "prompt_ref": "prompts/task.json",
                "chosen_ref": "reports/chosen.md",
                "rejected_ref": "reports/rejected.md",
                "chosen_score": 1,
                "rejected_score": 0,
                "split": "train",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    output_path = temp_dir / "out" / "dpo.jsonl"
    count = prepare.convert_file(
        kind="dpo",
        input_path=input_path,
        output_path=output_path,
        repo_root=temp_dir,
    )

    records = read_jsonl(output_path)
    assert count == 1
    assert records[0]["chosen"] == "Correct report"
    assert records[0]["rejected"] == "Incorrect report"
    assert "Find the bug." in records[0]["prompt"]
    assert "old answer" not in records[0]["prompt"]


def test_b200_budget_plan_computes_reserve_from_rate(project_root):
    budget = load_script(project_root, "automodel_b200_budget.py")
    plan = budget.load_plan(project_root / "configs" / "automodel_b200" / "budget.yaml")
    summary = budget.summarize_budget(plan)

    assert summary.hourly_rate_per_b200 == 6.2496
    assert summary.planned_b200_hours == 144
    assert summary.planned_cost_usd == pytest.approx(899.9424)
    assert summary.purchased_b200_hours == pytest.approx(192.0123, rel=1e-4)
    assert summary.reserve_b200_hours == pytest.approx(48.0123, rel=1e-4)
