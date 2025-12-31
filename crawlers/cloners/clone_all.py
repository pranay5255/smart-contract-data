#!/usr/bin/env python3
"""
Master GitHub Cloner

Clones all GitHub repositories or specific categories.
"""
import sys
from pathlib import Path
from typing import Optional

# Add crawlers to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cloners.github_cloner import GitHubCloner
from sources.source_registry import SourceRegistry
from sources.source_types import Priority
from utils.logger import log


def clone_all_repos(
    categories: Optional[list[str]] = None,
    priority_filter: Optional[Priority] = None,
    dry_run: bool = False
):
    """
    Clone all GitHub repositories from configured sources.

    Args:
        categories: Optional list of categories to clone. If None, clones all.
        priority_filter: Optional priority filter (HIGH, MEDIUM, LOW)
        dry_run: If True, only list what would be cloned without cloning
    """
    log.info("Starting GitHub repositories cloning")

    # Load sources
    registry = SourceRegistry()

    # Determine categories to process
    if categories:
        available_categories = registry.get_github_categories()
        invalid_categories = set(categories) - set(available_categories)
        if invalid_categories:
            log.error(f"Invalid categories: {invalid_categories}")
            log.info(f"Available categories: {available_categories}")
            return

        process_categories = categories
    else:
        process_categories = registry.get_github_categories()

    log.info(f"Processing categories: {process_categories}")

    # Initialize cloner
    cloner = GitHubCloner()

    # Collect all sources
    all_sources = []
    for category in process_categories:
        sources = registry.get_github_sources(category=category, priority=priority_filter)
        all_sources.extend(sources)

    if not all_sources:
        log.warning("No sources found matching criteria")
        return

    log.info(f"Found {len(all_sources)} repositories to clone")

    # Dry run - just list
    if dry_run:
        print("\n" + "="*60)
        print("DRY RUN - Would clone the following repositories:")
        print("="*60)
        for source in all_sources:
            print(f"  [{source.priority.value.upper()}] {source.name} ({source.category})")
            print(f"    URL: {source.url}")
        print("="*60 + "\n")
        return

    # Clone each repository
    results = []
    for idx, source in enumerate(all_sources, 1):
        log.info(f"[{idx}/{len(all_sources)}] Processing: {source.name}")
        log.info(f"  Category: {source.category} | Priority: {source.priority.value}")

        result = cloner.clone_repo(
            url=source.url,
            category=source.category,
            priority=source.priority.value
        )
        results.append(result)

        # Print status
        if result.status in ["cloned", "updated"]:
            log.success(f"✓ {result.name}: {result.status}")
        else:
            log.error(f"✗ {result.name}: {result.error}")

    # Print summary
    summary = cloner.get_status_summary(results)
    print("\n" + "="*60)
    print("GITHUB REPOSITORIES CLONING SUMMARY")
    print("="*60)
    print(f"Total: {summary['total']}")
    print(f"Cloned: {summary['cloned']}")
    print(f"Updated: {summary['updated']}")
    print(f"Failed: {summary['failed']}")

    print("\nBy Category:")
    for category, stats in summary['by_category'].items():
        print(f"  {category}:")
        print(f"    Success: {stats['success']}")
        print(f"    Failed: {stats['failed']}")

    print("\nBy Priority:")
    for priority, stats in summary['by_priority'].items():
        print(f"  {priority}:")
        print(f"    Success: {stats['success']}")
        print(f"    Failed: {stats['failed']}")

    if summary['errors']:
        print("\nErrors:")
        for error in summary['errors']:
            print(f"  - {error['repo']}: {error['error']}")

    print("="*60 + "\n")

    return results, summary


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Clone all GitHub repositories")
    parser.add_argument(
        "--categories",
        nargs="+",
        help="Specific categories to clone (e.g., audit_repos vulnerability_datasets)"
    )
    parser.add_argument(
        "--priority",
        choices=["high", "medium", "low"],
        help="Filter by priority level"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List repositories without cloning"
    )
    parser.add_argument(
        "--list-categories",
        action="store_true",
        help="List available categories and exit"
    )

    args = parser.parse_args()

    # List categories
    if args.list_categories:
        registry = SourceRegistry()
        categories = registry.get_github_categories()
        print("\nAvailable GitHub repository categories:")
        for cat in categories:
            sources = registry.get_github_sources(category=cat)
            print(f"  - {cat}: {len(sources)} repositories")
        print()
        return

    priority = Priority(args.priority.upper()) if args.priority else None

    clone_all_repos(
        categories=args.categories,
        priority_filter=priority,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
