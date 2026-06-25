"""Prepare EVMBench audit records for AutoModel SFT and TRL DPO runs.

The source schemas are documented in
docs/audit-pdf-to-evmbench/5_POST_TRAINING_DATASETS_AND_RECIPES.md. This
script flattens those provenance-rich JSONL records into the simple local JSONL
columns consumed by NeMo AutoModel's ColumnMappedTextInstructionDataset and by
TRL's DPOTrainer.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any


SFT_METADATA_FIELDS = (
    "record_id",
    "task_id",
    "audit_id",
    "source",
    "split",
    "provenance_ref",
    "review_state",
)

DPO_METADATA_FIELDS = (
    "record_id",
    "task_id",
    "audit_id",
    "split",
    "chosen_score",
    "rejected_score",
    "preference_reason",
    "judge_results_ref",
)


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSONL row: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected a JSON object")
            yield value


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def resolve_ref(ref: str, *, input_path: Path, repo_root: Path) -> Path:
    ref_path = Path(ref).expanduser()
    candidates = [ref_path] if ref_path.is_absolute() else [
        input_path.parent / ref_path,
        repo_root / ref_path,
        Path.cwd() / ref_path,
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    searched = ", ".join(str(candidate) for candidate in candidates)
    raise FileNotFoundError(f"Could not resolve content ref {ref!r}; searched {searched}")


def normalize_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
                else:
                    parts.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return json.dumps(content, ensure_ascii=False, sort_keys=True)


def render_messages(messages: list[dict[str, Any]], *, include_assistant: bool = True) -> str:
    rendered: list[str] = []
    for message in messages:
        role = str(message.get("role", "user"))
        if role == "assistant" and not include_assistant:
            continue
        content = normalize_content(message.get("content"))
        if content:
            rendered.append(f"{role}: {content}")
    return "\n\n".join(rendered)


def load_ref_value(ref: str, *, input_path: Path, repo_root: Path) -> Any:
    path = resolve_ref(ref, input_path=input_path, repo_root=repo_root)
    text = path.read_text(encoding="utf-8")

    if path.suffix.lower() in {".json", ".jsonl"}:
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(parsed, dict):
            if "content" in parsed:
                return parsed["content"]
            if isinstance(parsed.get("messages"), list):
                return render_messages(parsed["messages"], include_assistant=False)
            if "prompt" in parsed:
                return parsed["prompt"]
        return parsed

    return text


def message_content(
    message: dict[str, Any],
    *,
    input_path: Path,
    repo_root: Path,
) -> str:
    if "content" in message:
        return normalize_content(message["content"])
    if "content_ref" in message:
        return normalize_content(
            load_ref_value(str(message["content_ref"]), input_path=input_path, repo_root=repo_root)
        )
    raise ValueError(f"Message is missing content/content_ref: {message}")


def metadata_subset(record: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: record[field] for field in fields if field in record}


def convert_sft_record(
    record: dict[str, Any],
    *,
    input_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    output = metadata_subset(record, SFT_METADATA_FIELDS)

    if {"context", "question", "answer"}.issubset(record):
        output.update(
            {
                "context": normalize_content(record["context"]),
                "question": normalize_content(record["question"]),
                "answer": normalize_content(record["answer"]),
            }
        )
        return output

    messages = record.get("messages")
    if not isinstance(messages, list):
        prompt = record.get("prompt") or record.get("instruction") or record.get("question")
        answer = record.get("answer") or record.get("output") or record.get("completion")
        if prompt is None or answer is None:
            raise ValueError(
                "SFT record must contain messages, context/question/answer, or prompt/answer fields"
            )
        output.update(
            {
                "context": "",
                "question": normalize_content(prompt),
                "answer": normalize_content(answer),
            }
        )
        return output

    context_parts: list[str] = []
    question_parts: list[str] = []
    answer_parts: list[str] = []

    for message in messages:
        role = str(message.get("role", "user"))
        content = message_content(message, input_path=input_path, repo_root=repo_root)
        if not content:
            continue
        if role in {"system", "developer"}:
            context_parts.append(content)
        elif role == "assistant":
            answer_parts.append(content)
        else:
            question_parts.append(content)

    if not answer_parts:
        raise ValueError(
            f"SFT record {record.get('record_id', '<unknown>')} has no assistant answer"
        )
    if not context_parts and not question_parts:
        raise ValueError(f"SFT record {record.get('record_id', '<unknown>')} has no prompt content")

    output.update(
        {
            "context": "\n\n".join(context_parts),
            "question": "\n\n".join(question_parts),
            "answer": "\n\n".join(answer_parts),
        }
    )
    return output


def preference_value(
    record: dict[str, Any],
    field: str,
    *,
    input_path: Path,
    repo_root: Path,
) -> Any:
    if field in record:
        value = record[field]
    else:
        ref_field = f"{field}_ref"
        if ref_field not in record:
            raise ValueError(f"DPO record is missing {field!r} or {ref_field!r}")
        value = load_ref_value(str(record[ref_field]), input_path=input_path, repo_root=repo_root)

    if isinstance(value, list):
        return value
    return normalize_content(value)


def convert_dpo_record(
    record: dict[str, Any],
    *,
    input_path: Path,
    repo_root: Path,
) -> dict[str, Any]:
    output = metadata_subset(record, DPO_METADATA_FIELDS)
    output.update(
        {
            "prompt": preference_value(
                record, "prompt", input_path=input_path, repo_root=repo_root
            ),
            "chosen": preference_value(
                record, "chosen", input_path=input_path, repo_root=repo_root
            ),
            "rejected": preference_value(
                record, "rejected", input_path=input_path, repo_root=repo_root
            ),
        }
    )
    return output


def convert_file(
    *,
    kind: str,
    input_path: Path,
    output_path: Path,
    repo_root: Path,
    limit: int | None = None,
) -> int:
    converter = convert_sft_record if kind == "sft" else convert_dpo_record

    def converted() -> Iterable[dict[str, Any]]:
        for index, record in enumerate(iter_jsonl(input_path)):
            if limit is not None and index >= limit:
                break
            try:
                yield converter(record, input_path=input_path, repo_root=repo_root)
            except Exception as exc:
                record_id = record.get("record_id", f"row-{index + 1}")
                raise ValueError(f"Failed to convert {record_id}: {exc}") from exc

    return write_jsonl(output_path, converted())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["sft", "dpo"], help="Source record type to convert.")
    parser.add_argument("--input", required=True, type=Path, help="Input JSONL path.")
    parser.add_argument("--output", required=True, type=Path, help="Output JSONL path.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root used to resolve relative *_ref fields.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum records to convert.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    count = convert_file(
        kind=args.kind,
        input_path=args.input,
        output_path=args.output,
        repo_root=args.repo_root,
        limit=args.limit,
    )
    print(f"Wrote {count} {args.kind.upper()} records to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
