"""
Kaggle dataset downloader.

Downloads datasets from Kaggle for smart contract vulnerability analysis.
Uses the Kaggle CLI, which reads credentials from ~/.kaggle/kaggle.json
or KAGGLE_USERNAME/KAGGLE_KEY environment variables.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from config.settings import DATASETS_DIR, KAGGLE_USERNAME, KAGGLE_KEY
from utils.helpers import ensure_dir, sanitize_filename, load_sources_config
from utils.logger import log
from utils.rate_limiter import get_rate_limiter


class KaggleDownloader:
    """
    Download datasets from Kaggle.

    Target datasets from TASKS.md:
    - tranduongminhdai/smart-contract-vulnerability-datset (12K contracts)
    - bcccdatasets/bccc-vulscs-2023 (36,670 samples)
    """

    SERVICE_NAME = "kaggle"

    # Target datasets for this project
    DEFAULT_DATASETS = [
        {
            "dataset_id": "tranduongminhdai/smart-contract-vulnerability-datset",
            "description": "Smart Contract Vulnerability Dataset with 12K+ contracts",
            "priority": "high",
        },
        {
            "dataset_id": "bcccdatasets/bccc-vulscs-2023",
            "description": "BCCC-VulSCs-2023 with 36,670 samples",
            "priority": "high",
        },
    ]

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        datasets: Optional[list[dict]] = None,
    ):
        """
        Initialize Kaggle downloader.

        Args:
            output_dir: Directory to save datasets. Defaults to settings.DATASETS_DIR/kaggle
            datasets: Optional list of dataset configs overriding defaults.
        """
        self.output_dir = ensure_dir(output_dir or DATASETS_DIR / "kaggle")
        self.rate_limiter = get_rate_limiter()
        self.default_datasets = datasets or self._load_default_datasets()
        self.kaggle_cli = shutil.which("kaggle")
        self.cli_available = self.kaggle_cli is not None

        if not self.cli_available:
            log.warning("Kaggle CLI not found in PATH. Install `kaggle` to enable downloads.")

        if not self._has_credentials():
            log.warning(
                "Kaggle credentials not found. Set KAGGLE_USERNAME and KAGGLE_KEY "
                "or create ~/.kaggle/kaggle.json via `kaggle config set`."
            )

    def _has_credentials(self) -> bool:
        """Check for Kaggle credentials in env or ~/.kaggle/kaggle.json."""
        if KAGGLE_USERNAME and KAGGLE_KEY:
            return True
        return (Path.home() / ".kaggle" / "kaggle.json").exists()

    def _ensure_cli(self) -> str:
        """Ensure the Kaggle CLI is available."""
        if not self.kaggle_cli:
            raise RuntimeError("kaggle CLI not found. Install `kaggle` and ensure it is in PATH.")
        return self.kaggle_cli

    def _run_kaggle(self, args: list[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a Kaggle CLI command."""
        cmd = [self._ensure_cli(), *args]
        env = os.environ.copy()
        if KAGGLE_USERNAME and KAGGLE_KEY:
            env.setdefault("KAGGLE_USERNAME", KAGGLE_USERNAME)
            env.setdefault("KAGGLE_KEY", KAGGLE_KEY)
        try:
            return subprocess.run(
                cmd,
                check=True,
                text=True,
                capture_output=capture_output,
                env=env,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else ""
            if stderr:
                log.error(f"Kaggle CLI error: {stderr}")
            raise RuntimeError(f"Kaggle CLI command failed: {' '.join(cmd)}") from exc

    def _load_default_datasets(self) -> list[dict]:
        """Load default datasets from config/sources.yaml, with fallback defaults."""
        try:
            config = load_sources_config()
        except Exception:
            return self.DEFAULT_DATASETS

        datasets = []
        for entry in config.get("dataset_downloads", {}).get("kaggle", []):
            dataset_id = entry.get("dataset_id")
            if not dataset_id:
                continue
            datasets.append(
                {
                    "dataset_id": dataset_id,
                    "description": entry.get("stats") or entry.get("name") or dataset_id,
                    "priority": entry.get("priority", "medium"),
                }
            )

        return datasets or self.DEFAULT_DATASETS

    def list_datasets(self, search_term: str = "smart contract") -> list[dict]:
        """
        Search for datasets on Kaggle.

        Args:
            search_term: Search query

        Returns:
            List of dataset metadata dicts
        """
        with self.rate_limiter.limit(self.SERVICE_NAME):
            result = self._run_kaggle(["datasets", "list", "-s", search_term])

        datasets = self._parse_dataset_list_output(result.stdout)

        log.info(f"Found {len(datasets)} datasets matching '{search_term}'")
        return datasets

    def get_dataset_info(self, dataset_id: str) -> dict:
        """
        Get detailed info about a dataset.

        Args:
            dataset_id: Dataset identifier (owner/dataset-name)

        Returns:
            Dataset metadata dict
        """
        dataset_dir = self._dataset_dir(dataset_id)
        if not dataset_dir.exists():
            return {"id": dataset_id, "files": [], "file_count": 0, "total_size": 0}

        file_list = []
        total_size = 0
        for file_path in dataset_dir.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.name == ".download_complete":
                continue
            size = file_path.stat().st_size
            file_list.append(
                {
                    "name": str(file_path.relative_to(dataset_dir)),
                    "size": size,
                }
            )
            total_size += size

        return {
            "id": dataset_id,
            "files": file_list,
            "file_count": len(file_list),
            "total_size": total_size,
        }

    def _dataset_dir(self, dataset_id: str) -> Path:
        """Resolve the output directory for a dataset."""
        safe_name = sanitize_filename(dataset_id.replace("/", "_"))
        return self.output_dir / safe_name

    @staticmethod
    def _parse_dataset_list_output(output: str) -> list[dict]:
        """Parse `kaggle datasets list` output into minimal metadata."""
        lines = [line.strip() for line in output.splitlines() if line.strip()]
        if not lines:
            return []
        if lines[0].lower().startswith("ref"):
            lines = lines[1:]
        datasets = []
        for line in lines:
            parts = line.split()
            if not parts:
                continue
            datasets.append(
                {
                    "id": parts[0],
                    "title": None,
                    "size": None,
                    "last_updated": None,
                    "download_count": None,
                }
            )
        return datasets

    def download_dataset(
        self,
        dataset_id: str,
        unzip: bool = True,
        force: bool = False,
    ) -> Path:
        """
        Download a dataset from Kaggle.

        Args:
            dataset_id: Dataset identifier (owner/dataset-name)
            unzip: Whether to unzip the downloaded file
            force: Force re-download even if exists

        Returns:
            Path to downloaded dataset directory
        """
        # Create dataset directory
        dataset_dir = self._dataset_dir(dataset_id)
        if force and dataset_dir.exists():
            shutil.rmtree(dataset_dir)
        dataset_dir = ensure_dir(dataset_dir)

        # Check if already downloaded
        marker_file = dataset_dir / ".download_complete"
        if marker_file.exists() and not force:
            log.info(f"Dataset already downloaded: {dataset_id}")
            return dataset_dir

        log.info(f"Downloading dataset: {dataset_id}")

        try:
            with self.rate_limiter.limit(self.SERVICE_NAME):
                cmd = ["datasets", "download", "-d", dataset_id, "-p", str(dataset_dir)]
                if unzip:
                    cmd.append("--unzip")
                self._run_kaggle(cmd, capture_output=False)

            # Create completion marker
            marker_file.touch()

            # Save metadata
            self._save_metadata(dataset_id, dataset_dir)

            log.info(f"Successfully downloaded: {dataset_id} -> {dataset_dir}")
            return dataset_dir

        except Exception as exc:
            log.error(f"Failed to download {dataset_id}: {exc}")
            raise

    def _save_metadata(self, dataset_id: str, dataset_dir: Path) -> None:
        """Save dataset metadata to JSON file."""
        try:
            info = self.get_dataset_info(dataset_id)
            metadata_path = dataset_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(info, f, indent=2)
            log.debug(f"Saved metadata: {metadata_path}")
        except Exception as exc:
            log.warning(f"Failed to save metadata for {dataset_id}: {exc}")

    def download_all_defaults(self, force: bool = False) -> dict[str, Path]:
        """
        Download all default datasets for this project.

        Args:
            force: Force re-download even if exists

        Returns:
            Dict mapping dataset_id to download path
        """
        results = {}

        for dataset_info in self.default_datasets:
            dataset_id = dataset_info["dataset_id"]
            try:
                path = self.download_dataset(dataset_id, force=force)
                results[dataset_id] = path
            except Exception as exc:
                log.error(f"Failed to download {dataset_id}: {exc}")
                results[dataset_id] = None

        return results

    def get_status(self) -> dict:
        """
        Get download status for all default datasets.

        Returns:
            Dict with status info for each dataset
        """
        status = {}

        for dataset_info in self.default_datasets:
            dataset_id = dataset_info["dataset_id"]
            safe_name = sanitize_filename(dataset_id.replace("/", "_"))
            dataset_dir = self.output_dir / safe_name
            marker_file = dataset_dir / ".download_complete"

            status[dataset_id] = {
                "description": dataset_info["description"],
                "priority": dataset_info["priority"],
                "downloaded": marker_file.exists(),
                "path": str(dataset_dir) if dataset_dir.exists() else None,
            }

            # Count files if downloaded
            if dataset_dir.exists():
                files = list(dataset_dir.rglob("*"))
                status[dataset_id]["file_count"] = len([f for f in files if f.is_file()])

        return status


def download_kaggle_datasets(force: bool = False) -> dict[str, Path]:
    """
    Convenience function to download all Kaggle datasets.

    Args:
        force: Force re-download

    Returns:
        Dict mapping dataset_id to path
    """
    downloader = KaggleDownloader()
    return downloader.download_all_defaults(force=force)
