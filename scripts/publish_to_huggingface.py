#!/usr/bin/env python3
"""Prepare and optionally upload local crawler outputs to Hugging Face datasets.

The default split is intentionally conservative:
- PDFs: all PDF files under crawlers/output
- CSVs: CSV files under crawlers/output/datasets only

Use --csv-source-root crawlers/output if you deliberately want every CSV file,
including cloned benchmark internals such as BugLog_*.csv.
"""

from __future__ import annotations

import argparse
import csv
import os
import shlex
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


PDF_PATTERN = "**/*.[pP][dD][fF]"
CSV_PATTERN = "**/*.[cC][sS][vV]"


@dataclass(frozen=True)
class FileRecord:
    source_root: Path
    relative_path: Path
    size_bytes: int

    @property
    def absolute_path(self) -> Path:
        return self.source_root / self.relative_path


def human_size(size_bytes: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(size_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.2f} {unit}"
        value /= 1024
    return f"{size_bytes} B"


def discover_files(source_root: Path, suffix: str) -> list[FileRecord]:
    source_root = source_root.resolve()
    if not source_root.exists():
        raise FileNotFoundError(f"Source root does not exist: {source_root}")

    records: list[FileRecord] = []
    wanted_suffix = suffix.lower()
    for path in source_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() != wanted_suffix:
            continue
        relative_path = path.relative_to(source_root)
        records.append(
            FileRecord(
                source_root=source_root,
                relative_path=relative_path,
                size_bytes=path.stat().st_size,
            )
        )
    return sorted(records, key=lambda item: str(item.relative_path))


def write_manifest(records: Iterable[FileRecord], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "size_bytes", "source_root"])
        for record in records:
            writer.writerow(
                [
                    record.relative_path.as_posix(),
                    record.size_bytes,
                    record.source_root.as_posix(),
                ]
            )


def write_dataset_card(
    destination: Path,
    *,
    title: str,
    description: str,
    records: list[FileRecord],
    source_root: Path,
    include_pattern: str,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    total_bytes = sum(record.size_bytes for record in records)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    destination.write_text(
        "\n".join(
            [
                "---",
                "license: other",
                "tags:",
                "- smart-contracts",
                "- security",
                "- audits",
                "- vulnerability-detection",
                "---",
                "",
                f"# {title}",
                "",
                description,
                "",
                "## Contents",
                "",
                f"- Files: {len(records)}",
                f"- Total size: {human_size(total_bytes)}",
                f"- Local source root: `{source_root.as_posix()}`",
                f"- Upload include pattern: `{include_pattern}`",
                f"- Manifest: `manifest.csv`",
                f"- Generated: {generated_at}",
                "",
                "## Notes",
                "",
                "This dataset card was generated from the local crawler output. "
                "Confirm licensing and redistribution terms for the original sources "
                "before making the dataset public.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def run_command(command: list[str], *, dry_run: bool) -> None:
    printable = " ".join(shlex.quote(part) for part in command)
    if dry_run:
        print(f"DRY RUN: {printable}")
        return
    print(f"RUN: {printable}")
    subprocess.run(command, check=True)


def upload_large_folder(
    *,
    repo_id: str,
    source_root: Path,
    include_pattern: str,
    private: bool,
    num_workers: int,
    token: str | None,
    dry_run: bool,
) -> None:
    command = [
        "hf",
        "upload-large-folder",
        repo_id,
        source_root.as_posix(),
        "--repo-type",
        "dataset",
        "--include",
        include_pattern,
        "--num-workers",
        str(num_workers),
        "--private" if private else "--no-private",
    ]
    if token:
        command.extend(["--token", token])
    run_command(command, dry_run=dry_run)


def upload_file(
    *,
    repo_id: str,
    local_path: Path,
    path_in_repo: str,
    private: bool,
    token: str | None,
    dry_run: bool,
) -> None:
    command = [
        "hf",
        "upload",
        repo_id,
        local_path.as_posix(),
        path_in_repo,
        "--repo-type",
        "dataset",
        "--private" if private else "--no-private",
    ]
    if token:
        command.extend(["--token", token])
    run_command(command, dry_run=dry_run)


def require_repo_id(repo_id: str | None, option_name: str) -> str:
    if repo_id:
        return repo_id
    raise SystemExit(f"{option_name} is required when --upload is set")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare and optionally upload PDF and CSV crawler outputs to Hugging Face."
    )
    parser.add_argument("--source-root", default="crawlers/output", type=Path)
    parser.add_argument("--csv-source-root", default="crawlers/output/datasets", type=Path)
    parser.add_argument("--export-root", default="hf_exports", type=Path)
    parser.add_argument("--pdf-repo", help="HF dataset repo for PDFs, e.g. username/audit-pdfs")
    parser.add_argument("--csv-repo", help="HF dataset repo for CSV data, e.g. username/sc-csv-data")
    parser.add_argument("--num-workers", default=8, type=int)
    parser.add_argument("--token-env", default="HF_TOKEN")
    parser.add_argument("--upload", action="store_true", help="Run hf upload commands")
    parser.add_argument("--public", action="store_true", help="Create repos as public if absent")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    private = not args.public
    dry_run = not args.upload
    token = os.environ.get(args.token_env)

    source_root = args.source_root.resolve()
    csv_source_root = args.csv_source_root.resolve()
    export_root = args.export_root.resolve()
    pdf_export = export_root / "pdf_dataset"
    csv_export = export_root / "csv_dataset"

    pdf_records = discover_files(source_root, ".pdf")
    csv_records = discover_files(csv_source_root, ".csv")

    write_manifest(pdf_records, pdf_export / "manifest.csv")
    write_manifest(csv_records, csv_export / "manifest.csv")
    write_dataset_card(
        pdf_export / "README.md",
        title="Smart Contract Security Audit PDFs",
        description="PDF audit reports collected by the local smart-contract-data crawler.",
        records=pdf_records,
        source_root=source_root,
        include_pattern=PDF_PATTERN,
    )
    write_dataset_card(
        csv_export / "README.md",
        title="Smart Contract Vulnerability CSV Datasets",
        description="CSV datasets collected by the local smart-contract-data crawler.",
        records=csv_records,
        source_root=csv_source_root,
        include_pattern=CSV_PATTERN,
    )

    print("Inventory")
    print(f"- PDFs: {len(pdf_records)} files, {human_size(sum(r.size_bytes for r in pdf_records))}")
    print(f"- CSVs: {len(csv_records)} files, {human_size(sum(r.size_bytes for r in csv_records))}")
    print(f"- Export metadata: {export_root}")
    print(f"- Upload mode: {'enabled' if args.upload else 'dry run'}")

    if not args.upload:
        print("")
        print("Set --upload with --pdf-repo and/or --csv-repo to push to Hugging Face.")

    if args.pdf_repo or args.upload:
        pdf_repo = require_repo_id(args.pdf_repo, "--pdf-repo")
        upload_large_folder(
            repo_id=pdf_repo,
            source_root=source_root,
            include_pattern=PDF_PATTERN,
            private=private,
            num_workers=args.num_workers,
            token=token,
            dry_run=dry_run,
        )
        upload_file(
            repo_id=pdf_repo,
            local_path=pdf_export / "README.md",
            path_in_repo="README.md",
            private=private,
            token=token,
            dry_run=dry_run,
        )
        upload_file(
            repo_id=pdf_repo,
            local_path=pdf_export / "manifest.csv",
            path_in_repo="manifest.csv",
            private=private,
            token=token,
            dry_run=dry_run,
        )

    if args.csv_repo or args.upload:
        csv_repo = require_repo_id(args.csv_repo, "--csv-repo")
        upload_large_folder(
            repo_id=csv_repo,
            source_root=csv_source_root,
            include_pattern=CSV_PATTERN,
            private=private,
            num_workers=args.num_workers,
            token=token,
            dry_run=dry_run,
        )
        upload_file(
            repo_id=csv_repo,
            local_path=csv_export / "README.md",
            path_in_repo="README.md",
            private=private,
            token=token,
            dry_run=dry_run,
        )
        upload_file(
            repo_id=csv_repo,
            local_path=csv_export / "manifest.csv",
            path_in_repo="manifest.csv",
            private=private,
            token=token,
            dry_run=dry_run,
        )


if __name__ == "__main__":
    main()
