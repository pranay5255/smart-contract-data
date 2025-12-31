#!/usr/bin/env python3
"""
Setup Verification Script

Verifies that all required dependencies, credentials, and configurations
are properly set up before running data download scripts.
"""
import sys
import os
from pathlib import Path

# Add crawlers to path
sys.path.insert(0, str(Path(__file__).parent / "crawlers"))


def print_section(title: str):
    """Print a section header."""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)


def check_status(condition: bool, success_msg: str, failure_msg: str) -> bool:
    """Print status and return result."""
    if condition:
        print(f"  ✓ {success_msg}")
        return True
    else:
        print(f"  ✗ {failure_msg}")
        return False


def verify_python_version() -> bool:
    """Verify Python version is 3.10+."""
    print_section("Python Version")
    version = sys.version_info
    current = f"{version.major}.{version.minor}.{version.micro}"

    success = version >= (3, 10)
    return check_status(
        success,
        f"Python {current} (3.10+ required)",
        f"Python {current} - UPGRADE REQUIRED (need 3.10+)"
    )


def verify_required_packages() -> dict:
    """Verify required Python packages are installed."""
    print_section("Required Python Packages")

    required_packages = {
        "Core": [
            ("requests", "HTTP requests"),
            ("pyyaml", "YAML parsing"),
            ("loguru", "Logging"),
        ],
        "GitHub": [
            ("gitpython", "Git operations (GitPython)"),
        ],
        "Kaggle": [
            ("kaggle", "Kaggle API"),
        ],
        "HuggingFace": [
            ("datasets", "HuggingFace datasets"),
            ("huggingface_hub", "HuggingFace Hub API"),
        ],
        "Optional": [
            ("pytest", "Testing framework"),
            ("ratelimit", "Rate limiting"),
        ]
    }

    results = {}

    for category, packages in required_packages.items():
        print(f"\n{category}:")
        category_results = {}

        for package_name, description in packages:
            try:
                __import__(package_name)
                check_status(True, f"{package_name} - {description}", "")
                category_results[package_name] = True
            except ImportError:
                check_status(False, "", f"{package_name} - NOT INSTALLED ({description})")
                category_results[package_name] = False

        results[category] = category_results

    return results


def verify_environment_variables() -> dict:
    """Verify environment variables are set."""
    print_section("Environment Variables")

    env_vars = {
        "GitHub": {
            "GITHUB_TOKEN": {
                "required": False,
                "description": "GitHub API token (recommended, 5000 req/hr)"
            }
        },
        "Kaggle": {
            "KAGGLE_USERNAME": {
                "required": True,
                "description": "Kaggle username"
            },
            "KAGGLE_KEY": {
                "required": True,
                "description": "Kaggle API key"
            }
        },
        "HuggingFace": {
            "HUGGINGFACE_TOKEN": {
                "required": False,
                "description": "HuggingFace token (for private datasets)"
            }
        }
    }

    results = {}

    for category, vars_dict in env_vars.items():
        print(f"\n{category}:")
        category_results = {}

        for var_name, var_info in vars_dict.items():
            value = os.getenv(var_name)
            is_set = bool(value)

            if var_info["required"]:
                status = check_status(
                    is_set,
                    f"{var_name} - {var_info['description']}",
                    f"{var_name} - NOT SET (REQUIRED) - {var_info['description']}"
                )
            else:
                if is_set:
                    status = check_status(
                        True,
                        f"{var_name} - {var_info['description']}",
                        ""
                    )
                else:
                    print(f"  ⚠ {var_name} - NOT SET (optional) - {var_info['description']}")
                    status = True  # Optional, so still counts as success

            category_results[var_name] = is_set

        results[category] = category_results

    return results


def verify_directories() -> bool:
    """Verify required directories exist or can be created."""
    print_section("Directories")

    from config.settings import OUTPUT_DIR, REPOS_DIR, DATASETS_DIR

    dirs_to_check = [
        (OUTPUT_DIR, "Main output directory"),
        (REPOS_DIR, "GitHub repositories"),
        (DATASETS_DIR, "Downloaded datasets"),
    ]

    all_good = True
    for dir_path, description in dirs_to_check:
        if dir_path.exists():
            check_status(True, f"{description}: {dir_path}", "")
        else:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                check_status(True, f"{description}: {dir_path} (created)", "")
            except Exception as e:
                check_status(False, "", f"{description}: Cannot create {dir_path} - {e}")
                all_good = False

    return all_good


def verify_git_installation() -> bool:
    """Verify git is installed."""
    print_section("Git Installation")

    import shutil
    git_path = shutil.which("git")

    if git_path:
        # Get git version
        import subprocess
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            version = result.stdout.strip()
            return check_status(True, f"Git installed: {version}", "")
        except Exception as e:
            return check_status(False, "", f"Git found but error running: {e}")
    else:
        return check_status(False, "", "Git not found in PATH - INSTALL REQUIRED")


def verify_config_files() -> bool:
    """Verify configuration files exist and are valid."""
    print_section("Configuration Files")

    all_good = True

    # Check sources.yaml
    config_file = Path(__file__).parent / "crawlers" / "config" / "sources.yaml"
    if config_file.exists():
        try:
            import yaml
            with open(config_file) as f:
                config = yaml.safe_load(f)

            # Count sources
            github_count = sum(
                len(repos)
                for category, repos in config.get("github_repos", {}).items()
            )
            kaggle_count = len(config.get("dataset_downloads", {}).get("kaggle", []))
            hf_count = len(config.get("dataset_downloads", {}).get("huggingface", []))

            check_status(
                True,
                f"sources.yaml valid ({github_count} GitHub repos, {kaggle_count} Kaggle, {hf_count} HF)",
                ""
            )
        except Exception as e:
            check_status(False, "", f"sources.yaml invalid: {e}")
            all_good = False
    else:
        check_status(False, "", f"sources.yaml not found at {config_file}")
        all_good = False

    return all_good


def print_final_summary(results: dict):
    """Print final summary and recommendations."""
    print_section("SUMMARY")

    all_critical_passed = True
    warnings = []
    errors = []

    # Check critical requirements
    if not results["python_version"]:
        errors.append("Python 3.10+ required")
        all_critical_passed = False

    if not results["git_installed"]:
        errors.append("Git installation required")
        all_critical_passed = False

    # Check package requirements
    core_packages = results["packages"]["Core"]
    if not all(core_packages.values()):
        missing = [k for k, v in core_packages.items() if not v]
        errors.append(f"Missing core packages: {', '.join(missing)}")
        all_critical_passed = False

    # Check optional but recommended
    if not results["env_vars"]["GitHub"]["GITHUB_TOKEN"]:
        warnings.append("GITHUB_TOKEN not set - rate limit will be 60 req/hr instead of 5000")

    kaggle_vars = results["env_vars"]["Kaggle"]
    if not all(kaggle_vars.values()):
        missing_kaggle = [k for k, v in kaggle_vars.items() if not v]
        warnings.append(f"Kaggle credentials not set: {', '.join(missing_kaggle)} - Kaggle downloads will fail")

    # Print status
    if all_critical_passed and not errors:
        print("\n✓ All critical requirements met!")
    else:
        print("\n✗ Some critical requirements missing:")
        for error in errors:
            print(f"  - {error}")

    if warnings:
        print("\n⚠ Warnings:")
        for warning in warnings:
            print(f"  - {warning}")

    # Print next steps
    print_section("NEXT STEPS")

    if errors:
        print("\n1. Fix the errors listed above")
        print("2. Install missing packages:")
        print("   pip install -r crawlers/requirements.txt")
        print("3. Set up environment variables in .env file")
        print("4. Run this script again to verify")
    else:
        print("\n✓ Setup is ready!")
        print("\nYou can now run:")
        print("  1. python download_all_data.py --dry-run  # See what would be downloaded")
        print("  2. python download_all_data.py             # Download everything")
        print("\nOr run individual downloaders:")
        print("  - python crawlers/run_download_github.py --priority high")
        print("  - python crawlers/run_download_kaggle.py")
        print("  - python crawlers/run_download_huggingface.py")

    print("\n" + "="*60 + "\n")

    return all_critical_passed


def main():
    """Main verification function."""
    print("\n" + "="*60)
    print("  SMART CONTRACT DATA COLLECTION - SETUP VERIFICATION")
    print("="*60)

    results = {}

    # Run all checks
    results["python_version"] = verify_python_version()
    results["git_installed"] = verify_git_installation()
    results["packages"] = verify_required_packages()
    results["env_vars"] = verify_environment_variables()
    results["directories"] = verify_directories()
    results["config_files"] = verify_config_files()

    # Print final summary
    success = print_final_summary(results)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
