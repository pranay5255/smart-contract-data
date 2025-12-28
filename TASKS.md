# Implementation Tasks

**Last Updated:** 2025-12-29
**Repository Purpose:** Data collection + Experiment planning (no training code)

---

## Phase Overview

| Phase | Status | Description |
|-------|--------|-------------|
| 1. Data Collection Infrastructure | 🟡 In Progress | Crawlers, scrapers, downloaders |
| 2. Data Processing Pipeline | ⚪ Not Started | Normalization, deduplication |
| 3. Synthetic Data Generation | ⚪ Not Started | HexaCoder + mini-swe-agent |
| 4. Experiment Configuration | ⚪ Not Started | Ablation configs, eval harness |

---

## Phase 1: Data Collection Infrastructure

### 1.1 GitHub Cloners ✅ DONE

- [x] `config/settings.py` - Environment variables, paths, rate limits
- [x] `config/sources.yaml` - 40+ data source definitions
- [x] `cloners/github_cloner.py` - Clone/update repos with rate limiting
- [x] `utils/helpers.py` - Common utility functions
- [x] `utils/logger.py` - Loguru logging setup
- [x] `tests/conftest.py` - Pytest fixtures

### 1.2 Web Scrapers ⚪ TODO

| Task | File | Est. Lines | Priority |
|------|------|------------|----------|
| Base scraper class | `scrapers/base_scraper.py` | ~150 | HIGH |
| Code4rena scraper | `scrapers/audit_scrapers.py` | ~100 | HIGH |
| Sherlock scraper | `scrapers/audit_scrapers.py` | ~100 | HIGH |
| CodeHawks scraper | `scrapers/audit_scrapers.py` | ~100 | HIGH |
| Solodit scraper | `scrapers/audit_scrapers.py` | ~100 | MEDIUM |
| Rekt News scraper | `scrapers/exploit_scrapers.py` | ~100 | HIGH |
| Trail of Bits scraper | `scrapers/exploit_scrapers.py` | ~80 | MEDIUM |
| Immunefi scraper | `scrapers/exploit_scrapers.py` | ~80 | MEDIUM |
| SWC Registry scraper | `scrapers/docs_scrapers.py` | ~60 | LOW |
| OWASP scraper | `scrapers/docs_scrapers.py` | ~60 | LOW |

**Specification for `base_scraper.py`:**
```python
from abc import ABC, abstractmethod

class BaseScraper(ABC):
    def __init__(self, base_url: str, output_dir: Path, requires_js: bool = False)

    @abstractmethod
    def scrape(self) -> list[dict]

    def fetch_page(self, url: str, headers: dict = None) -> str
    def fetch_page_js(self, url: str) -> str  # Selenium/Playwright
    def parse_html(self, html: str) -> BeautifulSoup
    def save_report(self, data: dict, filename: str)
    def handle_pagination(self, base_url: str, max_pages: int = 100) -> list[str]
```

### 1.3 Dataset Downloaders ⚪ TODO

| Task | File | Est. Lines | Priority |
|------|------|------------|----------|
| Kaggle downloader | `downloaders/kaggle_downloader.py` | ~120 | HIGH |
| HuggingFace downloader | `downloaders/hf_downloader.py` | ~100 | HIGH |

**Target datasets:**
- Kaggle: `tranduongminhdai/smart-contract-vulnerability-datset` (12K contracts)
- Kaggle: `bcccdatasets/bccc-vulscs-2023` (36,670 samples)
- HuggingFace: `Zellic/smart-contract-fiesta` (514K deduplicated)

### 1.4 Utilities ⚪ TODO

| Task | File | Est. Lines | Priority |
|------|------|------------|----------|
| Rate limiter | `utils/rate_limiter.py` | ~80 | MEDIUM |
| Submodule handler | `cloners/submodule_handler.py` | ~80 | LOW |

---

## Phase 2: Data Processing Pipeline

### 2.1 Normalizer ⚪ TODO

**File:** `processors/normalizer.py` (~200 lines)

```python
class DataNormalizer:
    def normalize_solidity(self, file_path: Path) -> dict
    def normalize_audit_md(self, file_path: Path) -> dict
    def normalize_audit_pdf(self, file_path: Path) -> dict
    def normalize_exploit_html(self, html: str, source: str) -> dict
    def normalize_json_dataset(self, file_path: Path) -> list[dict]
    def process_directory(self, dir_path: Path, source_type: str) -> list[dict]
    def write_jsonl(self, records: list[dict], output_file: Path)
```

**Output schema:**
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
  "tags": ["reentrancy", "defi"],
  "timestamp": "2024-01-15T00:00:00Z"
}
```

### 2.2 Extractor ⚪ TODO

**File:** `processors/extractor.py` (~250 lines)

```python
class VulnerabilityExtractor:
    VULNERABILITY_PATTERNS = {
        "reentrancy": [...],
        "overflow": [...],
        "access_control": [...],
        # All 37 SWC types
    }

    def extract_from_solidity(self, code: str) -> list[dict]
    def extract_from_audit(self, report: dict) -> list[dict]
    def extract_severity(self, text: str) -> str
    def extract_code_snippets(self, text: str) -> list[str]
    def tag_vulnerability(self, finding: dict) -> list[str]
```

### 2.3 Deduplicator ⚪ TODO

**File:** `processors/deduplicator.py` (~100 lines)

```python
class Deduplicator:
    def hash_content(self, content: str) -> str  # MD5
    def hash_file(self, file_path: Path) -> str
    def find_duplicates(self, records: list[dict]) -> dict[str, list]
    def deduplicate(self, records: list[dict], key: str = "content") -> list[dict]
    def deduplicate_files(self, directory: Path) -> dict
```

### 2.4 Indexer ⚪ TODO

**File:** `processors/indexer.py` (~150 lines)

```python
class SQLiteIndexer:
    def create_tables(self)
    def index_vulnerability(self, record: dict)
    def index_audit(self, record: dict)
    def build_fts_index(self)  # Full-text search
    def search(self, query: str, filters: dict = None) -> list[dict]
    def get_stats(self) -> dict
```

---

## Phase 3: Synthetic Data Generation

### 3.1 HexaCoder Pipeline ⚪ TODO

**File:** `synthetic/hexacoder_pipeline.py` (~300 lines)

```python
class HexaCoderPipeline:
    def __init__(self, api_key: str, model: str = "gpt-4"):
        self.client = OpenAI(api_key=api_key)

    def generate_vulnerable_code(self, swc_type: str, complexity: str) -> str
        """Generate vulnerable Solidity code for given SWC type."""

    def validate_with_slither(self, code: str, expected_swc: str) -> bool
        """Validate that code has expected vulnerability."""

    def generate_fix(self, vulnerable_code: str, swc_type: str) -> str
        """Generate fixed version of vulnerable code."""

    def validate_fix_with_foundry(self, original: str, fixed: str) -> bool
        """Run forge tests to verify fix works."""

    def create_training_pair(self, code: str, swc_type: str) -> dict
        """Create (input, output) pair for SFT training."""

    def run_pipeline(self, n_samples: int, swc_types: list) -> list[dict]
        """Generate n validated training pairs."""
```

**SWC types to generate:**
1. SWC-107: Reentrancy (target: 2000 samples)
2. SWC-101: Integer Overflow (target: 1500 samples)
3. SWC-115: Access Control (target: 1500 samples)
4. SWC-104: Unchecked Calls (target: 1000 samples)
5. SWC-114: Front-Running (target: 500 samples)

### 3.2 Mini-SWE-Agent Runner ⚪ TODO

**File:** `synthetic/mini_swe_agent_runner.py` (~200 lines)

```python
class MiniSWEAgentRunner:
    def __init__(self, model: str = "claude-3-opus"):
        self.agent = MiniSWEAgent(model=model)

    def generate_fix_with_reasoning(self, vulnerable_code: str, swc_type: str) -> dict
        """Use mini-swe-agent to generate fix with reasoning trace."""

    def create_dpo_pair(self, vulnerable_code: str) -> dict
        """Create (chosen, rejected) pair for DPO training."""

    def batch_generate(self, codes: list[str], batch_size: int = 10) -> list[dict]
```

### 3.3 Foundry Validator ⚪ TODO

**File:** `synthetic/foundry_validator.py` (~150 lines)

```python
class FoundryValidator:
    def __init__(self, foundry_path: str = "forge"):
        self.forge = foundry_path

    def create_test_template(self, swc_type: str, vulnerable_code: str, fixed_code: str) -> str
        """Generate Forge test script for vulnerability."""

    def run_test(self, test_file: Path) -> bool
        """Execute forge test and return pass/fail."""

    def validate_pair(self, vulnerable: str, fixed: str, swc_type: str) -> bool
        """Validate that vulnerable code fails and fixed code passes."""
```

---

## Phase 4: Experiment Configuration

### 4.1 Ablation Configs ⚪ TODO

Create YAML configs for each ablation experiment:

**File:** `experiments/ablations/smollm2_135m.yaml`
```yaml
model:
  name: HuggingFaceTB/SmolLM2-135M
  tokenizer: HuggingFaceTB/SmolLM2-135M

training:
  type: continued_pretraining
  tokens: 2_000_000_000
  batch_size: 32
  gradient_accumulation_steps: 8
  learning_rate: 3e-4
  warmup_steps: 2000
  lr_scheduler: cosine

data:
  mix:
    - source: dolma_code
      weight: 0.50
    - source: zellic_solidity
      weight: 0.30
    - source: audit_reports
      weight: 0.10
    - source: math_reasoning
      weight: 0.10

evaluation:
  dataset: smartbugs_curated
  metrics: [precision, recall, f1]
  eval_steps: 1000

hardware:
  target: rtx_4090
  precision: bf16
  use_lora: true
  lora_rank: 16
```

**Additional configs to create:**
- `experiments/ablations/smollm2_360m.yaml`
- `experiments/ablations/qwen_0.5b.yaml`
- `experiments/ablations/baguettotron_321m.yaml`
- `experiments/ablations/smollm2_1.7b.yaml`
- `experiments/ablations/qwen_coder_1.5b.yaml`
- `experiments/final/qwen_coder_3b.yaml`

### 4.2 Evaluation Harness ⚪ TODO

**File:** `experiments/evaluation/smartbugs_eval.py` (~200 lines)

```python
class SmartBugsEvaluator:
    def __init__(self, model, tokenizer, dataset_path: str):
        self.model = model
        self.tokenizer = tokenizer
        self.dataset = load_smartbugs(dataset_path)

    def evaluate(self) -> dict:
        """Run full evaluation on SmartBugs-curated."""
        results = {
            "precision": {},
            "recall": {},
            "f1": {}
        }
        for swc_type in SWC_TYPES:
            results["precision"][swc_type] = self.precision_for_type(swc_type)
            results["recall"][swc_type] = self.recall_for_type(swc_type)
            results["f1"][swc_type] = self.f1_for_type(swc_type)
        return results

    def generate_report(self, results: dict) -> str:
        """Generate markdown report of evaluation results."""
```

**File:** `experiments/evaluation/defihacklabs_eval.py` (~250 lines)

```python
class DeFiHackLabsEvaluator:
    def __init__(self, model, repo_path: str):
        self.model = model
        self.exploits = load_exploits(repo_path)

    def evaluate_detection(self, exploit: dict) -> dict:
        """Test if model detects vulnerability in pre-exploit code."""

    def compute_reward(self, model_output: str, ground_truth: dict) -> float:
        """Compute GRPO-style reward for detection."""

    def run_full_eval(self) -> dict:
        """Evaluate on all DeFiHackLabs exploits."""
```

### 4.3 Data Mix Variants ⚪ TODO

Create 5 data mix configurations for ablation:

| Mix ID | Code % | Solidity % | Audit % | Math % | Description |
|--------|--------|------------|---------|--------|-------------|
| mix_v1 | 50 | 30 | 10 | 10 | Baseline (OLMo3-style) |
| mix_v2 | 40 | 40 | 10 | 10 | More Solidity |
| mix_v3 | 60 | 20 | 10 | 10 | More general code |
| mix_v4 | 50 | 30 | 15 | 5 | More audit reports |
| mix_v5 | 50 | 35 | 10 | 5 | Solidity-heavy |

---

## Phase 5: CLI & Orchestration

### 5.1 CLI ⚪ TODO

**File:** `cli.py` (~200 lines)

```python
import click

@click.group()
def cli():
    """Smart Contract Security Data Crawler"""

@cli.command()
@click.option('--all', is_flag=True)
@click.option('--category', type=str)
def clone(all, category):
    """Clone GitHub repositories"""

@cli.command()
@click.option('--source', type=str)
def scrape(source):
    """Scrape web platforms"""

@cli.command()
@click.option('--platform', type=click.Choice(['kaggle', 'huggingface']))
def download(platform):
    """Download datasets"""

@cli.command()
def process():
    """Process and normalize data"""

@cli.command()
def generate_synthetic():
    """Run synthetic data generation pipeline"""

@cli.command()
def status():
    """Show collection status"""
```

### 5.2 Orchestrator ⚪ TODO

**File:** `orchestrator.py` (~250 lines)

```python
class PipelineOrchestrator:
    def run_data_collection(self) -> dict
    def run_processing(self) -> dict
    def run_synthetic_generation(self) -> dict
    def get_pipeline_status(self) -> dict
    def resume_from_checkpoint(self, phase: str) -> dict
```

---

## Testing Tasks

### Unit Tests ⚪ TODO

| Test File | Covers | Priority |
|-----------|--------|----------|
| `tests/test_config.py` | settings.py, sources.yaml | HIGH |
| `tests/test_cloners.py` | github_cloner.py | HIGH |
| `tests/test_scrapers.py` | All scraper classes | MEDIUM |
| `tests/test_downloaders.py` | Kaggle/HF downloaders | MEDIUM |
| `tests/test_processors.py` | normalizer, extractor, etc. | HIGH |
| `tests/test_synthetic.py` | HexaCoder pipeline | HIGH |

### Verification Scripts ⚪ TODO

| Script | Purpose |
|--------|---------|
| `scripts/verify_cloner.sh` | Test GitHub cloning |
| `scripts/verify_scraper.sh` | Test web scraping |
| `scripts/verify_synthetic.sh` | Test synthetic generation |
| `scripts/verify_all.sh` | Full system test |

---

## Files to Delete/Archive

These files are now superseded by this consolidated plan:

| File | Action | Reason |
|------|--------|--------|
| `SplitPlan.md` | DELETE | Merged into PRD.md |
| `dataSorucesReport.md` | ARCHIVE | Reference only, sources in sources.yaml |
| `10_key_decisions.md` | DELETE | Decisions captured in PRD.md |
| `compass_artifact_*.md` | ARCHIVE | Research reference |

---

## Success Criteria

### Data Collection Complete When:
- [ ] All 26 GitHub repos cloned
- [ ] All 4 audit platforms scraped (Code4rena, Sherlock, CodeHawks, Solodit)
- [ ] All 3 dataset platform sources downloaded
- [ ] All data normalized to JSONL format
- [ ] SQLite index with full-text search operational

### Synthetic Generation Complete When:
- [ ] 5K+ validated vulnerability pairs generated
- [ ] All 5 primary SWC types covered
- [ ] Slither validation passing for all pairs
- [ ] Foundry tests passing for all fixes

### Experiment Config Complete When:
- [ ] All ablation YAML configs created
- [ ] SmartBugs evaluation harness tested
- [ ] DeFiHackLabs evaluation harness tested
- [ ] Data mix variants defined and validated

---

## Quick Reference Commands

```bash
# Setup
cd smart-contract-data
python -m venv venv && source venv/bin/activate
pip install -r crawlers/requirements.txt

# Clone all repos
python -c "
import sys; sys.path.insert(0, 'crawlers')
from cloners.github_cloner import GitHubCloner
from utils.helpers import load_sources_config
cloner = GitHubCloner()
results = cloner.clone_all_from_config(load_sources_config())
print(cloner.get_status_summary(results))
"

# Run tests
pytest tests/ -v
pytest tests/ -v --cov=crawlers

# Verify YAML config
python3 -c "import yaml; yaml.safe_load(open('crawlers/config/sources.yaml'))" && echo "OK"

# Future CLI (after implementation)
python -m crawlers.cli clone --all
python -m crawlers.cli scrape --source code4rena
python -m crawlers.cli download --platform kaggle
python -m crawlers.cli process
python -m crawlers.cli generate_synthetic
python -m crawlers.cli status
```
