"""
Pytest configuration and fixtures for the crawler test suite.
"""
import os
import sys
import tempfile
import shutil
from pathlib import Path

import pytest
import yaml

# Add crawlers to path
sys.path.insert(0, str(Path(__file__).parent.parent / "crawlers"))


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def crawlers_dir(project_root):
    """Return the crawlers package directory."""
    return project_root / "crawlers"


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    temp = tempfile.mkdtemp(prefix="crawler_test_")
    yield Path(temp)
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def sample_sources_config():
    """Return a minimal sources configuration for testing."""
    return {
        "github_repos": {
            "test_repos": [
                {
                    "name": "Test Repo",
                    "url": "https://github.com/smartbugs/smartbugs-curated",
                    "data_types": ["solidity"],
                    "priority": "high",
                }
            ]
        },
        "web_scrapers": {
            "test_scrapers": [
                {
                    "name": "Test Scraper",
                    "base_url": "https://example.com",
                    "endpoints": ["/"],
                    "data_types": ["html"],
                    "priority": "medium",
                }
            ]
        },
        "dataset_downloads": {
            "kaggle": [],
            "huggingface": [],
        },
    }


@pytest.fixture
def mock_github_url():
    """Return a valid GitHub URL for testing."""
    return "https://github.com/OpenZeppelin/openzeppelin-contracts"


@pytest.fixture
def mock_invalid_url():
    """Return an invalid URL for testing error handling."""
    return "https://github.com/nonexistent-user-12345/nonexistent-repo-67890"


@pytest.fixture
def sample_solidity_code():
    """Return sample Solidity code for testing."""
    return '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Vulnerable {
    mapping(address => uint256) public balances;

    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }

    // Vulnerable to reentrancy
    function withdraw() public {
        uint256 balance = balances[msg.sender];
        require(balance > 0);

        (bool success, ) = msg.sender.call{value: balance}("");
        require(success);

        balances[msg.sender] = 0;
    }
}
'''


@pytest.fixture
def sample_audit_report():
    """Return sample audit report content."""
    return """
# Security Audit Report

## Project: Test Protocol
## Auditor: Test Auditor
## Date: 2024-01-15

### Findings

#### H-01: Reentrancy Vulnerability
**Severity**: High
**Location**: contracts/Vault.sol:45

The withdraw function is vulnerable to reentrancy attacks.

**Recommendation**: Use ReentrancyGuard or checks-effects-interactions pattern.
"""


@pytest.fixture(scope="session")
def sources_yaml_path(crawlers_dir):
    """Return path to sources.yaml."""
    return crawlers_dir / "config" / "sources.yaml"


@pytest.fixture
def loaded_sources_config(sources_yaml_path):
    """Load and return the actual sources configuration."""
    with open(sources_yaml_path, "r") as f:
        return yaml.safe_load(f)
