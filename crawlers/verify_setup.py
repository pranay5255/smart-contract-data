#!/usr/bin/env python3
"""
Setup Verification Script

Verifies that all modules are correctly configured and ready to use.
"""
import sys
from pathlib import Path

# Add crawlers to path
sys.path.insert(0, str(Path(__file__).parent))

from sources.source_registry import SourceRegistry
from sources.source_types import Priority, SourceType
from cloners.github_cloner import GitHubCloner
from config.settings import GITHUB_TOKEN, REPOS_DIR
from utils.logger import log


def check_environment():
    """Check environment variables and configuration."""
    print("\n" + "="*60)
    print("ENVIRONMENT CHECK")
    print("="*60)

    checks = {
        "GITHUB_TOKEN": GITHUB_TOKEN is not None,
        "REPOS_DIR exists": REPOS_DIR.exists(),
    }

    for check, status in checks.items():
        status_icon = "✓" if status else "✗"
        print(f"  {status_icon} {check}")

    all_passed = all(checks.values())

    if not all_passed:
        print("\n⚠ Some environment checks failed!")
        print("  Make sure you have:")
        print("  1. Created .env file with GITHUB_TOKEN")
        print("  2. Run the setup from the project root")
    else:
        print("\n✓ All environment checks passed!")

    print("="*60)

    return all_passed


def check_source_registry():
    """Check source registry loads correctly."""
    print("\n" + "="*60)
    print("SOURCE REGISTRY CHECK")
    print("="*60)

    try:
        registry = SourceRegistry()
        summary = registry.get_summary()

        print(f"  ✓ Registry loaded successfully")
        print(f"  ✓ GitHub repos: {summary['github']['total']}")
        print(f"  ✓ Web scrapers: {summary['web_scrapers']['total']}")
        print(f"  ✓ Kaggle datasets: {summary['datasets']['kaggle']}")
        print(f"  ✓ HuggingFace datasets: {summary['datasets']['huggingface']}")

        # Test category access
        categories = registry.get_github_categories()
        print(f"\n  GitHub categories ({len(categories)}):")
        for cat in categories:
            sources = registry.get_github_sources(category=cat)
            high_count = len([s for s in sources if s.priority == Priority.HIGH])
            print(f"    - {cat}: {len(sources)} repos ({high_count} high priority)")

        # Test priority filtering
        high_priority = registry.get_github_sources(priority=Priority.HIGH)
        print(f"\n  ✓ High priority GitHub repos: {len(high_priority)}")

        print("\n✓ Source registry working correctly!")
        print("="*60)

        return True

    except Exception as e:
        print(f"  ✗ Error loading source registry: {e}")
        print("="*60)
        return False


def check_github_cloner():
    """Check GitHub cloner initialization."""
    print("\n" + "="*60)
    print("GITHUB CLONER CHECK")
    print("="*60)

    try:
        cloner = GitHubCloner()
        print(f"  ✓ Cloner initialized")
        print(f"  ✓ Output directory: {cloner.output_dir}")

        # Test repo info (without cloning)
        test_url = "https://github.com/smartbugs/smartbugs-curated"

        if GITHUB_TOKEN:
            info = cloner.get_repo_info(test_url)
            if info:
                print(f"  ✓ GitHub API access working")
                print(f"    Test repo: {info.get('full_name', 'N/A')}")
                print(f"    Stars: {info.get('stars', 'N/A')}")
            else:
                print(f"  ⚠ Could not fetch repo info (rate limit?)")
        else:
            print(f"  ⚠ GITHUB_TOKEN not set - API access limited")

        print("\n✓ GitHub cloner working correctly!")
        print("="*60)

        return True

    except Exception as e:
        print(f"  ✗ Error with GitHub cloner: {e}")
        print("="*60)
        return False


def check_source_types():
    """Check source type classes."""
    print("\n" + "="*60)
    print("SOURCE TYPES CHECK")
    print("="*60)

    try:
        from sources.source_types import (
            GitHubSource,
            WebScraperSource,
            KaggleSource,
            HuggingFaceSource
        )

        # Test creating source instances
        gh_source = GitHubSource(
            name="Test Repo",
            url="https://github.com/test/repo",
            data_types=["solidity"],
            priority=Priority.HIGH
        )

        web_source = WebScraperSource(
            name="Test Scraper",
            base_url="https://example.com",
            data_types=["html"],
            priority=Priority.MEDIUM
        )

        kg_source = KaggleSource(
            name="Test Dataset",
            dataset_id="user/dataset",
            data_types=["csv"],
            priority=Priority.LOW
        )

        hf_source = HuggingFaceSource(
            name="Test HF Dataset",
            dataset_id="org/dataset",
            data_types=["json"],
            priority=Priority.HIGH
        )

        print(f"  ✓ GitHubSource: {gh_source.name}")
        print(f"  ✓ WebScraperSource: {web_source.name}")
        print(f"  ✓ KaggleSource: {kg_source.name}")
        print(f"  ✓ HuggingFaceSource: {hf_source.name}")

        # Test to_dict conversion
        gh_dict = gh_source.to_dict()
        assert gh_dict['source_type'] == SourceType.GITHUB_REPO.value
        print(f"  ✓ Source serialization working")

        print("\n✓ Source types working correctly!")
        print("="*60)

        return True

    except Exception as e:
        print(f"  ✗ Error with source types: {e}")
        import traceback
        traceback.print_exc()
        print("="*60)
        return False


def main():
    """Run all verification checks."""
    print("\n" + "="*70)
    print("SMART CONTRACT DATA CRAWLER - SETUP VERIFICATION")
    print("="*70)

    results = {
        "Environment": check_environment(),
        "Source Types": check_source_types(),
        "Source Registry": check_source_registry(),
        "GitHub Cloner": check_github_cloner(),
    }

    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)

    for check, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {check}")

    all_passed = all(results.values())

    if all_passed:
        print("\n✓✓✓ All checks passed! System is ready to use. ✓✓✓")
        print("\nNext steps:")
        print("  1. Run: python crawlers/run_cloner.py --summary")
        print("  2. Run: python crawlers/run_cloner.py clone-github --dry-run")
        print("  3. Run: python crawlers/run_cloner.py clone-github --priority high")
    else:
        print("\n✗✗✗ Some checks failed. Please fix the issues above. ✗✗✗")
        sys.exit(1)

    print("="*70 + "\n")


if __name__ == "__main__":
    main()
