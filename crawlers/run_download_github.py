#!/usr/bin/env python3
"""
GitHub Repository Downloader
Downloads all GitHub repositories or specific categories based on priority.
"""
import sys
from pathlib import Path

# Add crawlers to path
sys.path.insert(0, str(Path(__file__).parent))

from cloners.clone_all import clone_all_repos
from sources.source_types import Priority
from utils.logger import log


def main():
    """Download GitHub repositories."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Download GitHub repositories for smart contract data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all high-priority repos (recommended for first run)
  python run_download_github.py --priority high

  # Download specific categories
  python run_download_github.py --categories vulnerability_datasets audit_repos

  # Download everything
  python run_download_github.py

  # Dry run to see what would be downloaded
  python run_download_github.py --priority high --dry-run

  # List available categories
  python run_download_github.py --list-categories
        """
    )

    parser.add_argument(
        "--categories",
        nargs="+",
        choices=["aggregators", "audit_repos", "vulnerability_datasets", "educational"],
        help="Specific GitHub categories to download"
    )
    parser.add_argument(
        "--priority",
        choices=["high", "medium", "low"],
        help="Filter by priority level (high recommended)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading"
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available categories and exit"
    )

    args = parser.parse_args()

    # List categories
    if args.list_categories:
        from sources.source_registry import SourceRegistry
        registry = SourceRegistry()
        categories = registry.get_github_categories()

        print("\n" + "="*60)
        print("AVAILABLE GITHUB CATEGORIES")
        print("="*60)
        for cat in categories:
            sources = registry.get_github_sources(category=cat)
            high_priority = len([s for s in sources if s.priority == Priority.HIGH])
            print(f"\n{cat}:")
            print(f"  Total repositories: {len(sources)}")
            print(f"  High priority: {high_priority}")
            print(f"  Medium priority: {len(sources) - high_priority}")
        print("\n" + "="*60 + "\n")
        return

    # Convert priority to enum
    priority_enum = Priority(args.priority.upper()) if args.priority else None

    # Run clone
    log.info("Starting GitHub repository download")
    if args.dry_run:
        log.info("DRY RUN MODE - No actual downloads will occur")

    results, summary = clone_all_repos(
        categories=args.categories,
        priority_filter=priority_enum,
        dry_run=args.dry_run
    )

    if not args.dry_run:
        # Save summary to file
        import json
        from config.settings import OUTPUT_DIR
        summary_file = OUTPUT_DIR / "github_download_summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        log.success(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
