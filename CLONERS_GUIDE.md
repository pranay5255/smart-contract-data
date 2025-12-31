# Cloners Module Guide

This guide shows you how to use the GitHub cloners for collecting smart contract security data.

## Quick Start

```bash
# 1. Verify setup is correct
python crawlers/verify_setup.py

# 2. See all configured data sources
python crawlers/run_cloner.py --summary

# 3. See GitHub categories
python crawlers/run_cloner.py --github-categories

# 4. Dry run to see what would be cloned
python crawlers/run_cloner.py clone-github --dry-run

# 5. Clone high-priority repos only
python crawlers/run_cloner.py clone-github --priority high

# 6. Clone specific categories
python crawlers/run_cloner.py clone-github --categories audit_repos vulnerability_datasets

# 7. Clone all GitHub repos
python crawlers/run_cloner.py clone-github
```

## Project Structure

```
crawlers/
├── sources/                          # NEW: Source definitions
│   ├── __init__.py                   # Exports source types and registry
│   ├── source_types.py               # GitHubSource, WebScraperSource, etc.
│   └── source_registry.py            # Central registry for all sources
│
├── cloners/                          # GitHub repository cloners
│   ├── __init__.py                   # Exports GitHubCloner
│   ├── github_cloner.py              # Core cloning logic
│   ├── clone_all.py                  # Master script - clone all repos
│   ├── clone_audits.py               # Clone audit repos only
│   ├── clone_vulnerabilities.py      # Clone vulnerability datasets only
│   ├── clone_educational.py          # Clone educational repos only
│   └── clone_aggregators.py          # Clone aggregator repos only
│
├── config/
│   ├── settings.py                   # Environment variables, paths
│   └── sources.yaml                  # 40+ data source definitions
│
├── utils/
│   ├── helpers.py                    # Common utilities
│   └── logger.py                     # Logging setup
│
├── run_cloner.py                     # NEW: Unified CLI runner
└── verify_setup.py                   # NEW: Setup verification
```

## Individual Cloner Scripts

Each category has its own script for focused data collection:

### 1. Clone Audit Repositories

```bash
# Clone all audit repos (Sherlock, Cyfrin, Pashov, etc.)
python crawlers/cloners/clone_audits.py

# High-priority only
python crawlers/cloners/clone_audits.py --priority high
```

**Output:** `output/repos/audit_repos/`

### 2. Clone Vulnerability Datasets

```bash
# Clone all vulnerability datasets (SmartBugs, SolidiFI, etc.)
python crawlers/cloners/clone_vulnerabilities.py

# High-priority only
python crawlers/cloners/clone_vulnerabilities.py --priority high
```

**Output:** `output/repos/vulnerability_datasets/`

### 3. Clone Educational Repositories

```bash
# Clone educational repos (RareSkills, OpenZeppelin, etc.)
python crawlers/cloners/clone_educational.py

# High-priority only
python crawlers/cloners/clone_educational.py --priority high
```

**Output:** `output/repos/educational/`

### 4. Clone Aggregator Repositories

```bash
# Clone awesome lists and aggregators
python crawlers/cloners/clone_aggregators.py

# High-priority only
python crawlers/cloners/clone_aggregators.py --priority high
```

**Output:** `output/repos/aggregators/`

## Programmatic Usage

### Using the Source Registry

```python
import sys
sys.path.insert(0, 'crawlers')

from sources.source_registry import SourceRegistry
from sources.source_types import Priority

# Initialize registry
registry = SourceRegistry()

# Get all GitHub sources
all_github = registry.get_github_sources()

# Get sources by category
audits = registry.get_github_sources(category="audit_repos")
vulns = registry.get_github_sources(category="vulnerability_datasets")

# Get high-priority sources
high_priority = registry.get_github_sources(priority=Priority.HIGH)

# Get sources by category AND priority
high_priority_audits = registry.get_github_sources(
    category="audit_repos",
    priority=Priority.HIGH
)

# Print summary
registry.print_summary()
```

### Using the GitHub Cloner

```python
import sys
sys.path.insert(0, 'crawlers')

from cloners.github_cloner import GitHubCloner
from sources.source_registry import SourceRegistry
from sources.source_types import Priority

# Initialize
cloner = GitHubCloner()
registry = SourceRegistry()

# Clone a specific repo
result = cloner.clone_repo(
    url="https://github.com/smartbugs/smartbugs-curated",
    category="vulnerability_datasets",
    priority="high"
)

print(f"Status: {result.status}")
print(f"Path: {result.local_path}")

# Clone all high-priority vulnerability datasets
vuln_sources = registry.get_github_sources(
    category="vulnerability_datasets",
    priority=Priority.HIGH
)

results = []
for source in vuln_sources:
    result = cloner.clone_repo(
        url=source.url,
        category=source.category,
        priority=source.priority.value
    )
    results.append(result)

# Get summary
summary = cloner.get_status_summary(results)
print(f"Total: {summary['total']}")
print(f"Cloned: {summary['cloned']}")
print(f"Failed: {summary['failed']}")
```

## GitHub Repository Categories

The system organizes GitHub repos into 4 categories:

### 1. **aggregators** (4 repos)
Awesome lists and resource compilations
- Awesome Smart Contract Security (Saeidshirazi)
- Awesome Smart Contract Security (Moeinfatehi)
- Awesome Ethereum Security (Crytic)
- Awesome Smart Contract Datasets

### 2. **audit_repos** (12 repos)
Audit report repositories
- Sherlock Reports
- Cyfrin Audit Reports
- Pashov Audits
- SigP Public Audits
- Hexens Public Reports
- TechRate Audits
- ImmuneBytes Reports
- MixBytes Public Audits
- EthereumCommonwealth Auditing
- Nethermind Public Reports
- Halborn Public Reports
- Credshields Audit Reports

### 3. **vulnerability_datasets** (4 repos)
Labeled vulnerability datasets
- SmartBugs Curated (143 contracts, 208 vulnerabilities)
- SmartBugs Wild (47,398 contracts)
- SolidiFI Benchmark (9,369 bugs in 7 types)
- Tintinweb VulnDB

### 4. **educational** (5 repos)
Educational resources and reference implementations
- RareSkills Huff Puzzles
- RareSkills Solidity Riddles
- RareSkills Gas Puzzles
- Cyfrin Foundry Course
- OpenZeppelin Contracts

## Priority Levels

Sources are categorized by priority:

- **HIGH**: Critical datasets for model training (SmartBugs, major audit repos)
- **MEDIUM**: Important but secondary sources
- **LOW**: Nice-to-have supplementary data

## Output Directory Structure

```
output/
└── repos/
    ├── aggregators/
    │   ├── Awesome-Smart-Contract-Security/
    │   ├── Awesome-Smart-Contract-Security/
    │   └── ...
    ├── audit_repos/
    │   ├── sherlock-reports/
    │   ├── cyfrin-audit-reports/
    │   ├── audits/                    # Pashov
    │   └── ...
    ├── vulnerability_datasets/
    │   ├── smartbugs-curated/
    │   ├── smartbugs-wild/
    │   ├── SolidiFI-benchmark/
    │   └── ...
    └── educational/
        ├── huff-puzzles/
        ├── solidity-riddles/
        ├── openzeppelin-contracts/
        └── ...
```

## Next Steps

After cloning repositories, you can:

1. **Process the data**: Use processors module (TODO) to normalize data to JSONL
2. **Extract vulnerabilities**: Use extractors module (TODO) to identify patterns
3. **Web scraping**: Collect audit reports from Code4rena, Sherlock, etc. (TODO)
4. **Dataset downloads**: Download from Kaggle and HuggingFace (TODO)

## Troubleshooting

### Rate Limiting

If you hit GitHub rate limits:
- Add `GITHUB_TOKEN` to your `.env` file (increases limit to 5000 req/hr)
- Use `--priority high` to clone fewer repos
- Clone specific categories instead of all

### Clone Failures

If clones fail:
- Check internet connection
- Verify repository URLs are still valid
- Check disk space in `output/` directory
- Review error messages in the summary

### Verification Failures

If `verify_setup.py` fails:
- Ensure you're in the project root directory
- Check that `.env` file exists with `GITHUB_TOKEN`
- Verify `output/repos/` directory was created
- Check Python version is >=3.11
