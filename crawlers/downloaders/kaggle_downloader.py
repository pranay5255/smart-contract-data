"""
Kaggle dataset downloader.

Downloads datasets from Kaggle for smart contract vulnerability analysis.
Requires KAGGLE_USERNAME and KAGGLE_KEY environment variables.
"""
from __future__ import annotations

import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Optional

from config.settings import DATASETS_DIR, KAGGLE_USERNAME, KAGGLE_KEY
from utils.helpers import ensure_dir, sanitize_filename
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

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize Kaggle downloader.

        Args:
            output_dir: Directory to save datasets. Defaults to settings.DATASETS_DIR/kaggle
        """
        self.output_dir = ensure_dir(output_dir or DATASETS_DIR / "kaggle")
        self.rate_limiter = get_rate_limiter()
        self._api = None

        # Validate credentials
        if not KAGGLE_USERNAME or not KAGGLE_KEY:
            log.warning(
                "Kaggle credentials not found. Set KAGGLE_USERNAME and KAGGLE_KEY "
                "environment variables or create ~/.kaggle/kaggle.json"
            )

    def _get_api(self):
        """
        Get or create Kaggle API client.

        Returns:
            KaggleApi instance
        """
        if self._api is not None:
            return self._api

        try:
            from kaggle.api.kaggle_api_extended import KaggleApi
        except ImportError as exc:
            log.error("kaggle package not installed. Run: pip install kaggle")
            raise RuntimeError("kaggle package required") from exc

        # Set up authentication
        if KAGGLE_USERNAME and KAGGLE_KEY:
            # Set environment variables for Kaggle
            os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME
            os.environ["KAGGLE_KEY"] = KAGGLE_KEY

        try:
            self._api = KaggleApi()
            self._api.authenticate()
            log.info("Kaggle API authenticated successfully")
            return self._api
        except Exception as exc:
            log.error(f"Failed to authenticate with Kaggle: {exc}")
            raise

    def list_datasets(self, search_term: str = "smart contract") -> list[dict]:
        """
        Search for datasets on Kaggle.

        Args:
            search_term: Search query

        Returns:
            List of dataset metadata dicts
        """
        api = self._get_api()

        with self.rate_limiter.limit(self.SERVICE_NAME):
            results = api.dataset_list(search=search_term)

        datasets = []
        for dataset in results:
            datasets.append({
                "id": str(dataset),
                "title": dataset.title if hasattr(dataset, "title") else str(dataset),
                "size": dataset.size if hasattr(dataset, "size") else None,
                "last_updated": str(dataset.lastUpdated) if hasattr(dataset, "lastUpdated") else None,
                "download_count": dataset.downloadCount if hasattr(dataset, "downloadCount") else None,
            })

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
        api = self._get_api()
        owner, name = dataset_id.split("/")

        with self.rate_limiter.limit(self.SERVICE_NAME):
            files = api.dataset_list_files(owner, name)

        file_list = []
        total_size = 0
        for f in files.files:
            size = f.size if hasattr(f, "size") else 0
            file_list.append({
                "name": f.name,
                "size": size,
            })
            total_size += size

        return {
            "id": dataset_id,
            "files": file_list,
            "file_count": len(file_list),
            "total_size": total_size,
        }

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
        api = self._get_api()

        # Create dataset directory
        safe_name = sanitize_filename(dataset_id.replace("/", "_"))
        dataset_dir = ensure_dir(self.output_dir / safe_name)

        # Check if already downloaded
        marker_file = dataset_dir / ".download_complete"
        if marker_file.exists() and not force:
            log.info(f"Dataset already downloaded: {dataset_id}")
            return dataset_dir

        log.info(f"Downloading dataset: {dataset_id}")

        try:
            with self.rate_limiter.limit(self.SERVICE_NAME):
                api.dataset_download_files(
                    dataset_id,
                    path=str(dataset_dir),
                    unzip=unzip,
                )

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

        for dataset_info in self.DEFAULT_DATASETS:
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

        for dataset_info in self.DEFAULT_DATASETS:
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

