"""
HuggingFace dataset downloader.

Downloads datasets from HuggingFace Hub for smart contract analysis.
Optionally uses HUGGINGFACE_TOKEN for private datasets.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Union

from config.settings import DATASETS_DIR, HUGGINGFACE_TOKEN
from utils.helpers import ensure_dir, sanitize_filename, load_sources_config
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

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        token: Optional[str] = None,
        datasets: Optional[list[dict]] = None,
    ):
        """
        Initialize HuggingFace downloader.

        Args:
            output_dir: Directory to save datasets. Defaults to settings.DATASETS_DIR/huggingface
            token: HuggingFace API token. Defaults to HUGGINGFACE_TOKEN env var.
            datasets: Optional list of dataset configs overriding defaults.
        """
        self.output_dir = ensure_dir(output_dir or DATASETS_DIR / "huggingface")
        self.token = token or HUGGINGFACE_TOKEN
        self.rate_limiter = get_rate_limiter()
        self.default_datasets = datasets or self._load_default_datasets()
        self.hf_cli = shutil.which("hf") or shutil.which("huggingface-cli")
        self.cli_available = self.hf_cli is not None

        if not self.cli_available:
            log.warning(
                "HuggingFace CLI not found in PATH. Install `huggingface-hub` to enable CLI downloads."
            )

        if self.token:
            os.environ["HF_TOKEN"] = self.token
            log.debug("HuggingFace token configured")

    def _ensure_cli(self) -> str:
        """Ensure the HuggingFace CLI is available."""
        if not self.hf_cli:
            raise RuntimeError(
                "HuggingFace CLI not found. Install `huggingface-hub` and ensure `hf` is in PATH."
            )
        return self.hf_cli

    def _run_hf(
        self,
        args: list[str],
        capture_output: bool = True,
        extra_env: Optional[dict[str, str]] = None,
    ) -> subprocess.CompletedProcess:
        """Run a HuggingFace CLI command."""
        cmd = [self._ensure_cli(), *args]
        env = os.environ.copy()
        if self.token:
            env.setdefault("HF_TOKEN", self.token)
            env.setdefault("HUGGINGFACE_HUB_TOKEN", self.token)
        if extra_env:
            env.update(extra_env)
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
                log.error(f"HuggingFace CLI error: {stderr}")
            raise RuntimeError(f"HuggingFace CLI command failed: {' '.join(cmd)}") from exc

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

    def _load_default_datasets(self) -> list[dict]:
        """Load default datasets from config/sources.yaml, with fallback defaults."""
        try:
            config = load_sources_config()
        except Exception:
            return self.DEFAULT_DATASETS

        datasets = []
        for entry in config.get("dataset_downloads", {}).get("huggingface", []):
            dataset_id = entry.get("dataset_id")
            if not dataset_id:
                continue
            datasets.append(
                {
                    "dataset_id": dataset_id,
                    "description": entry.get("stats") or entry.get("name") or dataset_id,
                    "priority": entry.get("priority", "medium"),
                    "config": entry.get("config"),
                    "split": entry.get("split"),
                }
            )

        return datasets or self.DEFAULT_DATASETS

    def _dataset_dir(self, dataset_id: str, force: bool = False) -> Path:
        """Resolve the output directory for a dataset."""
        safe_name = sanitize_filename(dataset_id.replace("/", "_"))
        dataset_dir = self.output_dir / safe_name
        if force and dataset_dir.exists():
            shutil.rmtree(dataset_dir)
        return ensure_dir(dataset_dir)

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

    def _download_via_cli(
        self,
        dataset_id: str,
        dataset_dir: Path,
        config: Optional[str],
        split: Optional[str],
    ) -> Path:
        """Download a dataset repo snapshot using the HuggingFace CLI."""
        log.info(f"Using HuggingFace CLI for: {dataset_id}")
        with self.rate_limiter.limit(self.SERVICE_NAME):
            cmd = [
                "download",
                dataset_id,
                "--repo-type",
                "dataset",
                "--local-dir",
                str(dataset_dir),
            ]
            extra_env = None
            if self._cli_supports_local_dir_use_symlinks():
                cmd.extend(["--local-dir-use-symlinks", "False"])
            else:
                extra_env = {"HF_HUB_DISABLE_SYMLINKS": "1"}
            self._run_hf(cmd, capture_output=False, extra_env=extra_env)

        # Create completion marker
        marker_file = dataset_dir / ".download_complete"
        marker_file.touch()

        # Save metadata
        self._save_metadata(dataset_id, dataset_dir, config, split)

        log.info(f"Successfully downloaded: {dataset_id} -> {dataset_dir}")
        return dataset_dir

    def _download_via_datasets(
        self,
        dataset_id: str,
        dataset_dir: Path,
        config: Optional[str],
        split: Optional[str],
        streaming: bool,
    ) -> Path:
        """Download a dataset using the datasets library."""
        datasets = self._get_datasets_library()

        with self.rate_limiter.limit(self.SERVICE_NAME):
            dataset = datasets.load_dataset(
                dataset_id,
                name=config,
                split=split,
                token=self.token,
                streaming=streaming,
                trust_remote_code=True,
            )

        if streaming:
            log.info(f"Streaming dataset verified: {dataset_id}")
            return dataset_dir

        if isinstance(dataset, datasets.DatasetDict):
            for split_name, split_data in dataset.items():
                split_path = dataset_dir / split_name
                log.info(f"Saving {split_name} split: {len(split_data)} examples")
                split_data.save_to_disk(str(split_path))
        else:
            log.info(f"Saving dataset: {len(dataset)} examples")
            dataset.save_to_disk(str(dataset_dir / "data"))

        marker_file = dataset_dir / ".download_complete"
        marker_file.touch()
        self._save_metadata(dataset_id, dataset_dir, config, split)
        log.info(f"Successfully downloaded: {dataset_id} -> {dataset_dir}")
        return dataset_dir

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
        # Create dataset directory
        dataset_dir = self._dataset_dir(dataset_id, force=force)

        # Check if already downloaded
        marker_file = dataset_dir / ".download_complete"
        if marker_file.exists() and not force:
            log.info(f"Dataset already downloaded: {dataset_id}")
            return dataset_dir

        log.info(f"Downloading dataset: {dataset_id}")

        try:
            if streaming:
                return self._download_via_datasets(
                    dataset_id,
                    dataset_dir,
                    config,
                    split,
                    streaming=True,
                )

            if self.cli_available and not config and not split:
                return self._download_via_cli(dataset_id, dataset_dir, config, split)

            if not self.cli_available:
                log.warning("HuggingFace CLI not available; falling back to datasets.")
            elif config or split:
                log.info("Dataset config/split requested; using datasets library.")

            return self._download_via_datasets(
                dataset_id,
                dataset_dir,
                config,
                split,
                streaming=False,
            )

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

        dataset_dir = self._dataset_dir(dataset_id, force=False)

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

        for dataset_info in self.default_datasets:
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

        # Fallback for CLI-downloaded repo snapshots
        return datasets.load_dataset(
            str(dataset_dir),
            name=config,
            split=split,
            token=self.token,
            trust_remote_code=True,
        )

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

            # Get size if downloaded
            if dataset_dir.exists():
                total_size = sum(
                    f.stat().st_size for f in dataset_dir.rglob("*") if f.is_file()
                )
                status[dataset_id]["size_bytes"] = total_size
                status[dataset_id]["size_mb"] = round(total_size / (1024 * 1024), 2)

        return status

    def _cli_supports_local_dir_use_symlinks(self) -> bool:
        """Check if the HuggingFace CLI supports --local-dir-use-symlinks."""
        cached = getattr(self, "_supports_local_dir_use_symlinks", None)
        if cached is not None:
            return cached
        try:
            result = self._run_hf(["download", "--help"], capture_output=True)
        except Exception:
            self._supports_local_dir_use_symlinks = False
            return False
        output = "\n".join([result.stdout or "", result.stderr or ""])
        supported = "--local-dir-use-symlinks" in output
        self._supports_local_dir_use_symlinks = supported
        return supported


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
