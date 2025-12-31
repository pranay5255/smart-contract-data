#!/usr/bin/env python3
"""
HuggingFace Dataset Downloader
Downloads datasets from HuggingFace Hub for smart contract analysis.
"""
import sys
from pathlib import Path

# Add crawlers to path
sys.path.insert(0, str(Path(__file__).parent))

from downloaders.hf_downloader import HuggingFaceDownloader
from utils.logger import log


def main():
    """Download HuggingFace datasets."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download HuggingFace datasets for smart contract data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
IMPORTANT: Before running this script:
  1. Install required packages: pip install datasets huggingface-hub
  2. Optional: Set HUGGINGFACE_TOKEN environment variable for private datasets
     (Get token from https://huggingface.co/settings/tokens)

Default datasets that will be downloaded:
  - Zellic/smart-contract-fiesta (514K deduplicated Solidity contracts)

WARNING: The Zellic dataset is VERY LARGE (~50GB+).
Make sure you have sufficient disk space before downloading.

Examples:
  # Download all default datasets
  python run_download_huggingface.py

  # Download specific dataset
  python run_download_huggingface.py --dataset Zellic/smart-contract-fiesta

  # Force re-download
  python run_download_huggingface.py --force

  # Check download status
  python run_download_huggingface.py --status

  # Use streaming mode (doesn't download full dataset)
  python run_download_huggingface.py --dataset Zellic/smart-contract-fiesta --streaming
        """
    )

    parser.add_argument(
        "--dataset",
        type=str,
        help="Download specific dataset by ID (org/name)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if already exists"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show download status and exit"
    )
    parser.add_argument(
        "--streaming",
        action="store_true",
        help="Use streaming mode (don't download full dataset)"
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Dataset configuration name"
    )
    parser.add_argument(
        "--split",
        type=str,
        help="Specific split to download (train, test, etc.)"
    )

    args = parser.parse_args()

    # Initialize downloader
    downloader = HuggingFaceDownloader()

    # Show status
    if args.status:
        status = downloader.get_status()
        print("\n" + "="*60)
        print("HUGGINGFACE DATASETS STATUS")
        print("="*60)
        for dataset_id, info in status.items():
            print(f"\n{dataset_id}:")
            print(f"  Description: {info['description']}")
            print(f"  Priority: {info['priority']}")
            print(f"  Downloaded: {'✓ Yes' if info['downloaded'] else '✗ No'}")
            if info['downloaded']:
                print(f"  Path: {info['path']}")
                if 'size_mb' in info:
                    print(f"  Size: {info['size_mb']} MB")
        print("\n" + "="*60 + "\n")
        return

    # Download specific dataset
    if args.dataset:
        log.info(f"Downloading dataset: {args.dataset}")
        if args.streaming:
            log.info("Using streaming mode (dataset will not be fully downloaded)")
        else:
            log.warning("This may take a long time for large datasets...")

        try:
            path = downloader.download_dataset(
                args.dataset,
                config=args.config,
                split=args.split,
                streaming=args.streaming,
                force=args.force
            )
            log.success(f"Downloaded to: {path}")
        except Exception as e:
            log.error(f"Failed to download {args.dataset}: {e}")
            sys.exit(1)
        return

    # Download all default datasets
    log.info("Downloading all default HuggingFace datasets")
    log.warning("The Zellic dataset is VERY LARGE (~50GB+)")
    log.info("This will take a significant amount of time...")

    results = downloader.download_all_defaults(force=args.force)

    # Print summary
    print("\n" + "="*60)
    print("HUGGINGFACE DOWNLOAD SUMMARY")
    print("="*60)

    successful = sum(1 for path in results.values() if path is not None)
    failed = sum(1 for path in results.values() if path is None)

    print(f"Total datasets: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    if successful > 0:
        print("\nDownloaded datasets:")
        for dataset_id, path in results.items():
            if path:
                print(f"  ✓ {dataset_id}")
                print(f"    Path: {path}")

    if failed > 0:
        print("\nFailed datasets:")
        for dataset_id, path in results.items():
            if path is None:
                print(f"  ✗ {dataset_id}")

    print("="*60 + "\n")

    # Save summary
    import json
    from config.settings import OUTPUT_DIR
    summary_file = OUTPUT_DIR / "huggingface_download_summary.json"
    summary_data = {
        "total": len(results),
        "successful": successful,
        "failed": failed,
        "datasets": {k: str(v) if v else None for k, v in results.items()}
    }
    with open(summary_file, "w") as f:
        json.dump(summary_data, f, indent=2)
    log.success(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
