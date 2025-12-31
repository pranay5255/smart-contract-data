#!/usr/bin/env python3
"""
Educational Repositories Cloner

Clones educational and reference repositories from GitHub.
Includes: RareSkills puzzles, Cyfrin courses, OpenZeppelin contracts, etc.
"""
import sys
from pathlib import Path

# Add crawlers to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cloners.github_cloner import GitHubCloner
from sources.source_registry import SourceRegistry
from sources.source_types import Priority
from utils.logger import log


def clone_educational_repos(priority_filter: Priority = None):
    """
    Clone all educational repository sources.

    Args:
        priority_filter: Optional priority filter (HIGH, MEDIUM, LOW)
    """
    log.info("Starting educational repositories cloning")

    # Load sources
    registry = SourceRegistry()
    edu_sources = registry.get_github_sources(category="educational", priority=priority_filter)

    if not edu_sources:
        log.warning("No educational sources found")
        return

    log.info(f"Found {len(edu_sources)} educational repositories to clone")

    # Initialize cloner
    cloner = GitHubCloner()

    # Clone each repository
    results = []
    for source in edu_sources:
        log.info(f"Processing: {source.name} (Priority: {source.priority.value})")

        result = cloner.clone_repo(
            url=source.url,
            category="educational",
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
    print("EDUCATIONAL REPOSITORIES CLONING SUMMARY")
    print("="*60)
    print(f"Total: {summary['total']}")
    print(f"Cloned: {summary['cloned']}")
    print(f"Updated: {summary['updated']}")
    print(f"Failed: {summary['failed']}")

    if summary['errors']:
        print("\nErrors:")
        for error in summary['errors']:
            print(f"  - {error['repo']}: {error['error']}")

    print("="*60 + "\n")

    return results, summary


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Clone educational repositories from GitHub")
    parser.add_argument(
        "--priority",
        choices=["high", "medium", "low"],
        help="Filter by priority level"
    )

    args = parser.parse_args()

    priority = Priority(args.priority.upper()) if args.priority else None

    clone_educational_repos(priority_filter=priority)


if __name__ == "__main__":
    main()
