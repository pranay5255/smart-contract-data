#!/usr/bin/env python3
"""
Data Source Runner

Unified CLI for running all data collection modules:
- GitHub cloners
- Web scrapers (TODO)
- Dataset downloaders (TODO)
"""
import sys
from pathlib import Path

# Add crawlers to path
sys.path.insert(0, str(Path(__file__).parent))

from sources.source_registry import SourceRegistry
from sources.source_types import Priority
from utils.logger import log


def show_sources_summary():
    """Show summary of all configured data sources."""
    registry = SourceRegistry()
    registry.print_summary()


def show_github_categories():
    """Show available GitHub repository categories."""
    registry = SourceRegistry()
    categories = registry.get_github_categories()

    print("\n" + "="*60)
    print("GITHUB REPOSITORY CATEGORIES")
    print("="*60)

    for cat in categories:
        sources = registry.get_github_sources(category=cat)
        high_priority = len([s for s in sources if s.priority == Priority.HIGH])
        print(f"\n{cat} ({len(sources)} repositories)")
        print(f"  High priority: {high_priority}")

        for source in sources[:3]:  # Show first 3
            print(f"  - {source.name} [{source.priority.value}]")

        if len(sources) > 3:
            print(f"  ... and {len(sources) - 3} more")

    print("\n" + "="*60 + "\n")


def clone_github_repos(categories=None, priority=None, dry_run=False):
    """Clone GitHub repositories."""
    from cloners.clone_all import clone_all_repos

    priority_enum = Priority(priority.upper()) if priority else None

    clone_all_repos(
        categories=categories,
        priority_filter=priority_enum,
        dry_run=dry_run
    )


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Smart Contract Security Data Collector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show all configured data sources
  %(prog)s --summary

  # Show GitHub categories
  %(prog)s --github-categories

  # Clone all high-priority GitHub repos (dry run)
  %(prog)s clone-github --priority high --dry-run

  # Clone specific categories
  %(prog)s clone-github --categories audit_repos vulnerability_datasets

  # Clone all GitHub repos
  %(prog)s clone-github

  # Clone just audits
  %(prog)s clone-github --categories audit_repos
        """
    )

    # Global options
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show summary of all configured data sources"
    )
    parser.add_argument(
        "--github-categories",
        action="store_true",
        help="Show available GitHub repository categories"
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Clone GitHub repos
    github_parser = subparsers.add_parser(
        "clone-github",
        help="Clone GitHub repositories"
    )
    github_parser.add_argument(
        "--categories",
        nargs="+",
        help="Specific categories to clone"
    )
    github_parser.add_argument(
        "--priority",
        choices=["high", "medium", "low"],
        help="Filter by priority level"
    )
    github_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List repositories without cloning"
    )

    # TODO: Add scrapers and downloaders subcommands

    args = parser.parse_args()

    # Handle global options
    if args.summary:
        show_sources_summary()
        return

    if args.github_categories:
        show_github_categories()
        return

    # Handle commands
    if args.command == "clone-github":
        clone_github_repos(
            categories=args.categories,
            priority=args.priority,
            dry_run=args.dry_run
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
