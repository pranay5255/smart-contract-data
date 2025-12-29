"""
HuggingFace dataset downloader.

Downloads datasets from HuggingFace Hub for smart contract analysis.
Optionally uses HUGGINGFACE_TOKEN for private datasets.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional, Union

from config.settings import DATASETS_DIR, HUGGINGFACE_TOKEN
from utils.helpers import ensure_dir, sanitize_filename
from utils.logger import log
from utils.rate_limiter import get_rate_limiter


class HuggingFaceDownloader:
    """
    Download datasets from HuggingFace Hub.

    Target dataset from TASKS.md:
    - Zellic/smart-contract-fiesta (514K deduplicated contracts)
    """

    SERVICE_NAME = "huggingface"

    # Target datasets for this project
    DEFAULT_DATASETS = [
        {
            "dataset_id": "Zellic/smart-contract-fiesta",
            "description": "514K deduplicated Solidity contracts from Zellic",
            "priority": "high",
            "config": None,  # Default config
            "split": None,  # All splits
        },
    ]

    def __init__(self, output_dir: Optional[Path] = None, token: Optional[str] = None):
        """
        Initialize HuggingFace downloader.

        Args:
            output_dir: Directory to save datasets. Defaults to settings.DATASETS_DIR/huggingface
            token: HuggingFace API token. Defaults to HUGGINGFACE_TOKEN env var.
        """
        self.output_dir = ensure_dir(output_dir or DATASETS_DIR / "huggingface")
        self.token = token or HUGGINGFACE_TOKEN
        self.rate_limiter = get_rate_limiter()

        if self.token:
            os.environ["HF_TOKEN"] = self.token
            log.debug("HuggingFace token configured")

    def _get_datasets_library(self):
        """Import and return the datasets library."""
        try:
            import datasets
            return datasets
        except ImportError as exc:
            log.error("datasets package not installed. Run: pip install datasets")
            raise RuntimeError("datasets package required") from exc

    def _get_hub_library(self):
        """Import and return the huggingface_hub library."""
        try:
            from huggingface_hub import HfApi, hf_hub_download
            return HfApi, hf_hub_download
        except ImportError as exc:
            log.error("huggingface_hub not installed. Run: pip install huggingface-hub")
            raise RuntimeError("huggingface_hub package required") from exc

    def get_dataset_info(self, dataset_id: str) -> dict:
        """
        Get info about a dataset from HuggingFace Hub.

        Args:
            dataset_id: Dataset identifier (org/name or name)

        Returns:
            Dataset metadata dict
        """
        HfApi, _ = self._get_hub_library()
        api = HfApi(token=self.token)

        with self.rate_limiter.limit(self.SERVICE_NAME):
            info = api.dataset_info(dataset_id)

        return {
            "id": info.id,
            "author": info.author,
            "sha": info.sha,
            "last_modified": str(info.last_modified) if info.last_modified else None,
            "private": info.private,
            "downloads": info.downloads,
            "likes": info.likes,
            "tags": info.tags,
            "card_data": info.card_data.__dict__ if info.card_data else None,
        }

    def list_dataset_files(self, dataset_id: str) -> list[dict]:
        """
        List files in a dataset repository.

        Args:
            dataset_id: Dataset identifier

        Returns:
            List of file info dicts
        """
        HfApi, _ = self._get_hub_library()
        api = HfApi(token=self.token)

        with self.rate_limiter.limit(self.SERVICE_NAME):
            files = api.list_repo_files(dataset_id, repo_type="dataset")

        return [{"path": f} for f in files]

    def download_dataset(
        self,
        dataset_id: str,
        config: Optional[str] = None,
        split: Optional[str] = None,
        streaming: bool = False,
        force: bool = False,
    ) -> Path:
        """
        Download a dataset from HuggingFace.

        Args:
            dataset_id: Dataset identifier (org/name)
            config: Dataset configuration name
            split: Specific split to download (train, test, etc.)
            streaming: Use streaming mode (doesn't download full dataset)
            force: Force re-download even if exists

        Returns:
            Path to downloaded dataset directory
        """
        datasets = self._get_datasets_library()

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
                # Load dataset
                dataset = datasets.load_dataset(
                    dataset_id,
                    name=config,
                    split=split,
                    token=self.token,
                    streaming=streaming,
                    trust_remote_code=True,
                )

            if streaming:
                # For streaming, just verify it works
                log.info(f"Streaming dataset verified: {dataset_id}")
                return dataset_dir

            # Save to disk
            if isinstance(dataset, datasets.DatasetDict):
                # Multiple splits
                for split_name, split_data in dataset.items():
                    split_path = dataset_dir / split_name
                    log.info(f"Saving {split_name} split: {len(split_data)} examples")
                    split_data.save_to_disk(str(split_path))
            else:
                # Single split
                log.info(f"Saving dataset: {len(dataset)} examples")
                dataset.save_to_disk(str(dataset_dir / "data"))

            # Create completion marker
            marker_file.touch()

            # Save metadata
            self._save_metadata(dataset_id, dataset_dir, config, split)

            log.info(f"Successfully downloaded: {dataset_id} -> {dataset_dir}")
            return dataset_dir

        except Exception as exc:
            log.error(f"Failed to download {dataset_id}: {exc}")
            raise

    def download_dataset_files(
        self,
        dataset_id: str,
        patterns: Optional[list[str]] = None,
        force: bool = False,
    ) -> Path:
        """
        Download specific files from a dataset repository.

        Useful for large datasets where you only need certain files.

        Args:
            dataset_id: Dataset identifier
            patterns: File patterns to download (e.g., ["*.json", "data/*.parquet"])
            force: Force re-download

        Returns:
            Path to downloaded files directory
        """
        HfApi, hf_hub_download = self._get_hub_library()
        api = HfApi(token=self.token)

        safe_name = sanitize_filename(dataset_id.replace("/", "_"))
        dataset_dir = ensure_dir(self.output_dir / safe_name)

        # Get file list
        files = self.list_dataset_files(dataset_id)

        # Filter by patterns if specified
        if patterns:
            import fnmatch

            filtered_files = []
            for f in files:
                path = f["path"]
                if any(fnmatch.fnmatch(path, p) for p in patterns):
                    filtered_files.append(f)
            files = filtered_files

        log.info(f"Downloading {len(files)} files from {dataset_id}")

        downloaded = []
        for file_info in files:
            file_path = file_info["path"]
            local_path = dataset_dir / file_path

            if local_path.exists() and not force:
                log.debug(f"File exists: {file_path}")
                downloaded.append(local_path)
                continue

            try:
                with self.rate_limiter.limit(self.SERVICE_NAME):
                    hf_hub_download(
                        repo_id=dataset_id,
                        filename=file_path,
                        repo_type="dataset",
                        local_dir=str(dataset_dir),
                        token=self.token,
                    )
                downloaded.append(local_path)
                log.debug(f"Downloaded: {file_path}")
            except Exception as exc:
                log.warning(f"Failed to download {file_path}: {exc}")

        log.info(f"Downloaded {len(downloaded)} files to {dataset_dir}")
        return dataset_dir

    def _save_metadata(
        self,
        dataset_id: str,
        dataset_dir: Path,
        config: Optional[str],
        split: Optional[str],
    ) -> None:
        """Save dataset metadata."""
        try:
            info = self.get_dataset_info(dataset_id)
            info["download_config"] = {
                "config": config,
                "split": split,
            }
            metadata_path = dataset_dir / "metadata.json"
            with open(metadata_path, "w") as f:
                json.dump(info, f, indent=2, default=str)
            log.debug(f"Saved metadata: {metadata_path}")
        except Exception as exc:
            log.warning(f"Failed to save metadata for {dataset_id}: {exc}")

    def download_all_defaults(self, force: bool = False) -> dict[str, Path]:
        """
        Download all default datasets for this project.

        Args:
            force: Force re-download

        Returns:
            Dict mapping dataset_id to download path
        """
        results = {}

        for dataset_info in self.DEFAULT_DATASETS:
            dataset_id = dataset_info["dataset_id"]
            config = dataset_info.get("config")
            split = dataset_info.get("split")

            try:
                path = self.download_dataset(
                    dataset_id,
                    config=config,
                    split=split,
                    force=force,
                )
                results[dataset_id] = path
            except Exception as exc:
                log.error(f"Failed to download {dataset_id}: {exc}")
                results[dataset_id] = None

        return results

    def load_dataset(
        self,
        dataset_id: str,
        config: Optional[str] = None,
        split: Optional[str] = None,
    ):
        """
        Load a previously downloaded dataset.

        Args:
            dataset_id: Dataset identifier
            config: Dataset configuration
            split: Specific split

        Returns:
            datasets.Dataset or datasets.DatasetDict
        """
        datasets = self._get_datasets_library()

        safe_name = sanitize_filename(dataset_id.replace("/", "_"))
        dataset_dir = self.output_dir / safe_name

        if not dataset_dir.exists():
            raise FileNotFoundError(f"Dataset not downloaded: {dataset_id}")

        # Try to load from disk
        if (dataset_dir / "data").exists():
            return datasets.load_from_disk(str(dataset_dir / "data"))

        # Check for split directories
        split_dirs = [d for d in dataset_dir.iterdir() if d.is_dir() and d.name != "raw"]
        if split_dirs:
            dataset_dict = {}
            for split_dir in split_dirs:
                try:
                    dataset_dict[split_dir.name] = datasets.load_from_disk(str(split_dir))
                except Exception:
                    continue
            if dataset_dict:
                return datasets.DatasetDict(dataset_dict)

        raise ValueError(f"Could not load dataset from {dataset_dir}")

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

            # Get size if downloaded
            if dataset_dir.exists():
                total_size = sum(
                    f.stat().st_size for f in dataset_dir.rglob("*") if f.is_file()
                )
                status[dataset_id]["size_bytes"] = total_size
                status[dataset_id]["size_mb"] = round(total_size / (1024 * 1024), 2)

        return status


def download_huggingface_datasets(force: bool = False) -> dict[str, Path]:
    """
    Convenience function to download all HuggingFace datasets.

    Args:
        force: Force re-download

    Returns:
        Dict mapping dataset_id to path
    """
    downloader = HuggingFaceDownloader()
    return downloader.download_all_defaults(force=force)

