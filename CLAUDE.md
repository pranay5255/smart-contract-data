# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Purpose:** Data collection + experiment planning for a smart contract vulnerability detection model (1B-3B parameters).

**Scope:** This repo handles data gathering and experiment configuration ONLY. No actual training code - training runs on separate infrastructure.

**Key Documents:**
- `PRD.md` - Complete project requirements, model architecture, training pipeline
- `TASKS.md` - Implementation tasks with specifications
- `archive/` - Reference documents (dataSorucesReport.md, compass research)

## Project Goals

Train a model achieving:
- **>35% precision** (vs GPT-4 baseline: 22%)
- **>70% recall** (vs GPT-4 baseline: 88%)
- **>0.45 F1 macro** across 5 primary SWC vulnerability types

## Commands

```bash
# Setup (from project root)
python -m venv venv && source venv/bin/activate
pip install -r crawlers/requirements.txt
cp .env.example .env  # Add API keys

# Run tests
pytest tests/ -v
pytest -m "not slow"

# Verify YAML config
python3 -c "import yaml; yaml.safe_load(open('crawlers/config/sources.yaml'))" && echo "OK"

# Clone all repos
python3 -c "
import sys; sys.path.insert(0, 'crawlers')
from cloners.github_cloner import GitHubCloner
from utils.helpers import load_sources_config
cloner = GitHubCloner()
results = cloner.clone_all_from_config(load_sources_config())
print(cloner.get_status_summary(results))
"
```

## Architecture

```
smart-contract-data/
├── crawlers/                    # Data collection package
│   ├── config/
│   │   ├── settings.py          # Env vars, paths, rate limits
│   │   └── sources.yaml         # 40+ data source definitions
│   ├── cloners/                 # GitHub repo handlers [DONE]
│   ├── scrapers/                # Web scraping [TODO]
│   ├── downloaders/             # Kaggle/HuggingFace [TODO]
│   ├── processors/              # Normalize to JSONL [TODO]
│   └── utils/                   # Helpers, logging [DONE]
│
├── experiments/                 # Experiment configs [TODO]
│   ├── ablations/               # YAML configs for ablation runs
│   ├── final/                   # Final training configs
│   └── evaluation/              # Eval harness scripts
│
├── synthetic/                   # Synthetic data generation [TODO]
│   ├── hexacoder_pipeline.py
│   ├── mini_swe_agent_runner.py
│   └── foundry_validator.py
│
├── output/                      # Collected data
├── archive/                     # Reference documents
├── PRD.md                       # Project requirements
├── TASKS.md                     # Implementation tasks
└── CLAUDE.md                    # This file
```

## Key Decisions (from PRD.md)

| Decision | Choice |
|----------|--------|
| Task | Hybrid: Multi-label + Generative explanation |
| Vulnerabilities | 5 primary SWC types (107, 101, 115, 104, 114) |
| Ablation Models | SmolLM2-135M/360M, Qwen2.5-0.5B, Baguettotron-321M |
| Final Model | Qwen2.5-Coder-3B |
| Pipeline | Continued Pretraining → SFT → DPO → GRPO |
| Training Libs | LLaMA-Factory (CPT), Unsloth+TRL (SFT), TRL (DPO/GRPO) |

## Key Patterns

**Import pattern** (required because package isn't installed):
```python
import sys
sys.path.insert(0, 'crawlers')
from config.settings import REPOS_DIR, GITHUB_TOKEN
from cloners.github_cloner import GitHubCloner
from utils.helpers import load_sources_config
```

**Config loading**:
```python
config = load_sources_config()  # Returns dict from sources.yaml
# config['github_repos']['audits'] -> list of repo dicts
# config['web_scrapers']['audit_platforms'] -> list of scraper configs
```

## Implementation Status

| Component | Status | Next Steps |
|-----------|--------|------------|
| config/, utils/ | ✅ Done | - |
| cloners/ | ✅ Done | Add submodule_handler.py |
| scrapers/ | ⚪ TODO | See TASKS.md Phase 1.2 |
| downloaders/ | ⚪ TODO | See TASKS.md Phase 1.3 |
| processors/ | ⚪ TODO | See TASKS.md Phase 2 |
| synthetic/ | ⚪ TODO | See TASKS.md Phase 3 |
| experiments/ | ⚪ TODO | See TASKS.md Phase 4 |

## Environment Variables

Required in `.env`:
- `GITHUB_TOKEN` - GitHub API token (5000 req/hr authenticated)
- `KAGGLE_USERNAME`, `KAGGLE_KEY` - For Kaggle dataset downloads
- `HUGGINGFACE_TOKEN` - For HuggingFace dataset access
- `OPENAI_API_KEY` - For synthetic data generation (HexaCoder)
- `LOG_LEVEL` - Optional, defaults to INFO

## Output Schema

```json
{
  "id": "sha256-hash",
  "source": "smartbugs-curated",
  "type": "vulnerability",
  "swc_id": "SWC-107",
  "cwe_id": "CWE-841",
  "severity": "high",
  "title": "Reentrancy in withdraw()",
  "description": "...",
  "code_snippet": "function withdraw() { ... }",
  "file_path": "contracts/Vault.sol",
  "line_numbers": [45, 52],
  "tags": ["reentrancy", "defi"]
}
```

## Data Sources (Priority)

| Source | Type | Size | Priority |
|--------|------|------|----------|
| SmartBugs-curated | Labeled vulns | 143 contracts | HIGH |
| Zellic/smart-contract-fiesta | Solidity code | 514K contracts | HIGH |
| DeFiHackLabs | Exploits | 550+ incidents | HIGH |
| Code4rena, Sherlock | Audit reports | 1000+ | HIGH |
| Kaggle SC Vulnerability | Labeled | 12K+ | HIGH |
