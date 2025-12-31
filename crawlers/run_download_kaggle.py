#!/usr/bin/env python3
"""
Kaggle Dataset Downloader
Downloads datasets from Kaggle for smart contract vulnerability analysis.
"""
import sys
from pathlib import Path

# Add crawlers to path
sys.path.insert(0, str(Path(__file__).parent))

from downloaders.kaggle_downloader import KaggleDownloader
from utils.logger import log


def main():
    """Download Kaggle datasets."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download Kaggle datasets for smart contract data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
IMPORTANT: Before running this script, set up Kaggle credentials:
  1. Create a Kaggle API token at https://www.kaggle.com/settings
  2. Either:
     - Set environment variables: KAGGLE_USERNAME and KAGGLE_KEY
     - Or place kaggle.json in ~/.kaggle/

Default datasets that will be downloaded:
  - tranduongminhdai/smart-contract-vulnerability-datset (12K+ contracts)
  - bcccdatasets/bccc-vulscs-2023 (36,670 samples)

Examples:
  # Download all default datasets
  python run_download_kaggle.py

  # Download specific dataset
  python run_download_kaggle.py --dataset tranduongminhdai/smart-contract-vulnerability-datset

  # Force re-download
  python run_download_kaggle.py --force

  # Check download status
  python run_download_kaggle.py --status
        """
    )

    parser.add_argument(
        "--dataset",
        type=str,
        help="Download specific dataset by ID (owner/dataset-name)"
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

    args = parser.parse_args()

    # Initialize downloader
    downloader = KaggleDownloader()

    # Show status
    if args.status:
        status = downloader.get_status()
        print("\n" + "="*60)
        print("KAGGLE DATASETS STATUS")
        print("="*60)
        for dataset_id, info in status.items():
            print(f"\n{dataset_id}:")
            print(f"  Description: {info['description']}")
            print(f"  Priority: {info['priority']}")
            print(f"  Downloaded: {'✓ Yes' if info['downloaded'] else '✗ No'}")
            if info['downloaded']:
                print(f"  Path: {info['path']}")
                if 'file_count' in info:
                    print(f"  Files: {info['file_count']}")
        print("\n" + "="*60 + "\n")
        return

    # Download specific dataset
    if args.dataset:
        log.info(f"Downloading dataset: {args.dataset}")
        try:
            path = downloader.download_dataset(args.dataset, force=args.force)
            log.success(f"Downloaded to: {path}")
        except Exception as e:
            log.error(f"Failed to download {args.dataset}: {e}")
            sys.exit(1)
        return

    # Download all default datasets
    log.info("Downloading all default Kaggle datasets")
    log.info("This may take a while depending on dataset sizes...")

    results = downloader.download_all_defaults(force=args.force)

    # Print summary
    print("\n" + "="*60)
    print("KAGGLE DOWNLOAD SUMMARY")
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
    summary_file = OUTPUT_DIR / "kaggle_download_summary.json"
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
