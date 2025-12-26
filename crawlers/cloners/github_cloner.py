"""
GitHub Repository Cloner Module

Handles cloning and updating of GitHub repositories for smart contract security data.
"""
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from github import Github, GithubException
from ratelimit import limits, sleep_and_retry

from config.settings import GITHUB_TOKEN, REPOS_DIR, RATE_LIMITS
from utils.helpers import extract_repo_info, sanitize_filename, ensure_dir
from utils.logger import log


@dataclass
class RepoInfo:
    """Information about a cloned repository."""
    name: str
    url: str
    local_path: Path
    category: str
    priority: str
    status: str  # 'cloned', 'updated', 'failed'
    error: Optional[str] = None


class GitHubCloner:
    """Handles cloning and updating GitHub repositories."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or REPOS_DIR
        self.github = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()
        ensure_dir(self.output_dir)

    @sleep_and_retry
    @limits(calls=RATE_LIMITS["github"]["calls"], period=RATE_LIMITS["github"]["period"])
    def _rate_limited_call(self, func, *args, **kwargs):
        """Wrapper for rate-limited GitHub API calls."""
        return func(*args, **kwargs)

    def get_repo_info(self, url: str) -> dict:
        """Get repository information from GitHub API."""
        try:
            owner, repo_name = extract_repo_info(url)
            repo = self._rate_limited_call(self.github.get_repo, f"{owner}/{repo_name}")
            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "description": repo.description,
                "stars": repo.stargazers_count,
                "last_updated": repo.updated_at.isoformat(),
                "default_branch": repo.default_branch,
                "size_kb": repo.size,
            }
        except GithubException as e:
            log.error(f"Failed to get repo info for {url}: {e}")
            return {}

    def clone_repo(self, url: str, category: str = "general", priority: str = "medium") -> RepoInfo:
        """Clone a repository to the local filesystem."""
        owner, repo_name = extract_repo_info(url)
        category_dir = ensure_dir(self.output_dir / sanitize_filename(category))
        local_path = category_dir / sanitize_filename(repo_name)

        if local_path.exists():
            return self.update_repo(url, category, priority)

        try:
            log.info(f"Cloning {url} to {local_path}")
            result = subprocess.run(
                ["git", "clone", "--depth", "1", url, str(local_path)],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                log.success(f"Successfully cloned {repo_name}")
                return RepoInfo(
                    name=repo_name,
                    url=url,
                    local_path=local_path,
                    category=category,
                    priority=priority,
                    status="cloned",
                )
            else:
                error_msg = result.stderr.strip()
                log.error(f"Failed to clone {repo_name}: {error_msg}")
                return RepoInfo(
                    name=repo_name,
                    url=url,
                    local_path=local_path,
                    category=category,
                    priority=priority,
                    status="failed",
                    error=error_msg,
                )

        except subprocess.TimeoutExpired:
            log.error(f"Timeout cloning {repo_name}")
            return RepoInfo(
                name=repo_name,
                url=url,
                local_path=local_path,
                category=category,
                priority=priority,
                status="failed",
                error="Clone timeout",
            )
        except Exception as e:
            log.error(f"Error cloning {repo_name}: {e}")
            return RepoInfo(
                name=repo_name,
                url=url,
                local_path=local_path,
                category=category,
                priority=priority,
                status="failed",
                error=str(e),
            )

    def update_repo(self, url: str, category: str = "general", priority: str = "medium") -> RepoInfo:
        """Update an existing repository."""
        owner, repo_name = extract_repo_info(url)
        category_dir = self.output_dir / sanitize_filename(category)
        local_path = category_dir / sanitize_filename(repo_name)

        if not local_path.exists():
            return self.clone_repo(url, category, priority)

        try:
            log.info(f"Updating {repo_name}")
            result = subprocess.run(
                ["git", "-C", str(local_path), "pull", "--ff-only"],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0:
                log.success(f"Successfully updated {repo_name}")
                return RepoInfo(
                    name=repo_name,
                    url=url,
                    local_path=local_path,
                    category=category,
                    priority=priority,
                    status="updated",
                )
            else:
                # Try a fresh clone if pull fails
                log.warning(f"Pull failed for {repo_name}, attempting fresh clone")
                import shutil
                shutil.rmtree(local_path)
                return self.clone_repo(url, category, priority)

        except Exception as e:
            log.error(f"Error updating {repo_name}: {e}")
            return RepoInfo(
                name=repo_name,
                url=url,
                local_path=local_path,
                category=category,
                priority=priority,
                status="failed",
                error=str(e),
            )

    def clone_all_from_config(self, config: dict) -> list[RepoInfo]:
        """Clone all repositories defined in the configuration."""
        results = []

        # Process each category of repos
        for category, repos in config.get("github_repos", {}).items():
            log.info(f"Processing category: {category}")
            for repo in repos:
                result = self.clone_repo(
                    url=repo["url"],
                    category=category,
                    priority=repo.get("priority", "medium"),
                )
                results.append(result)

        return results

    def get_status_summary(self, results: list[RepoInfo]) -> dict:
        """Generate a summary of cloning operations."""
        summary = {
            "total": len(results),
            "cloned": sum(1 for r in results if r.status == "cloned"),
            "updated": sum(1 for r in results if r.status == "updated"),
            "failed": sum(1 for r in results if r.status == "failed"),
            "by_category": {},
            "by_priority": {},
            "errors": [],
        }

        for result in results:
            # By category
            if result.category not in summary["by_category"]:
                summary["by_category"][result.category] = {"success": 0, "failed": 0}
            if result.status in ["cloned", "updated"]:
                summary["by_category"][result.category]["success"] += 1
            else:
                summary["by_category"][result.category]["failed"] += 1

            # By priority
            if result.priority not in summary["by_priority"]:
                summary["by_priority"][result.priority] = {"success": 0, "failed": 0}
            if result.status in ["cloned", "updated"]:
                summary["by_priority"][result.priority]["success"] += 1
            else:
                summary["by_priority"][result.priority]["failed"] += 1

            # Collect errors
            if result.error:
                summary["errors"].append({
                    "repo": result.name,
                    "error": result.error,
                })

        return summary
