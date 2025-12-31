# Download Scripts Reference

Complete reference for all data download scripts in this repository.

---

## 📁 Script Locations

```
smart-contract-data/
├── verify_setup.py                          # Verify setup before downloading
├── download_all_data.py                     # Master script - downloads everything
├── QUICK_START.md                           # Quick reference guide
├── SETUP_GUIDE.md                           # Detailed setup instructions
└── crawlers/
    ├── run_download_github.py               # Download GitHub repositories
    ├── run_download_kaggle.py               # Download Kaggle datasets
    └── run_download_huggingface.py          # Download HuggingFace datasets
```

---

## 🔧 verify_setup.py

**Purpose:** Verify that all dependencies, credentials, and configurations are correct before running downloads.

**Usage:**
```bash
python verify_setup.py
```

**What it checks:**
- ✓ Python version (3.10+ required)
- ✓ Git installation
- ✓ Required Python packages
- ✓ Environment variables (GitHub, Kaggle, HuggingFace tokens)
- ✓ Directory permissions
- ✓ Configuration file validity

**Output:**
- Detailed report of what's configured correctly
- List of missing requirements
- Warnings for optional but recommended items
- Next steps to fix any issues

**When to run:**
- Before first download
- After changing credentials
- When troubleshooting download issues

---

## 🎯 download_all_data.py

**Purpose:** Master orchestration script that downloads all data sources in prioritized order.

**Basic Usage:**
```bash
# Download everything (will prompt before large HuggingFace download)
python download_all_data.py

# Skip HuggingFace (recommended for first run)
python download_all_data.py --skip-huggingface

# Dry run to see what would be downloaded
python download_all_data.py --dry-run
```

**All Options:**
```bash
python download_all_data.py [OPTIONS]

Options:
  --github-priority {high,medium,low}  GitHub priority filter (default: high)
  --skip-github                        Skip GitHub downloads
  --skip-kaggle                        Skip Kaggle downloads
  --skip-huggingface                   Skip HuggingFace downloads
  --force                              Force re-download existing data
  --dry-run                            Show what would be downloaded
  -h, --help                           Show help message
```

**Examples:**
```bash
# Download HIGH priority GitHub + Kaggle only
python download_all_data.py --skip-huggingface

# Include MEDIUM priority GitHub repos
python download_all_data.py --github-priority medium --skip-huggingface

# Only download Kaggle datasets
python download_all_data.py --skip-github --skip-huggingface

# Force re-download everything
python download_all_data.py --force
```

**Download Order:**
1. GitHub repositories (filtered by priority)
2. Kaggle datasets (if not skipped)
3. HuggingFace datasets (if not skipped, prompts first)

**Output:**
- Real-time progress logs
- Summary statistics for each phase
- `output/master_download_summary.json` with complete results

---

## 📦 crawlers/run_download_github.py

**Purpose:** Download GitHub repositories (smart contract code, audit reports, educational materials).

**Basic Usage:**
```bash
# Download HIGH priority repos (recommended)
python crawlers/run_download_github.py --priority high

# Download all repos
python crawlers/run_download_github.py
```

**All Options:**
```bash
python crawlers/run_download_github.py [OPTIONS]

Options:
  --categories CATEGORIES [CATEGORIES ...]
                        Specific categories to download
                        Choices: aggregators, audit_repos,
                                vulnerability_datasets, educational
  --priority {high,medium,low}
                        Filter by priority level
  --dry-run             Show what would be downloaded
  --list-categories     List available categories and exit
  -h, --help            Show help message
```

**Examples:**
```bash
# List available categories
python crawlers/run_download_github.py --list-categories

# Download only vulnerability datasets
python crawlers/run_download_github.py --categories vulnerability_datasets

# Download vulnerability datasets and audit repos (HIGH priority only)
python crawlers/run_download_github.py --categories vulnerability_datasets audit_repos --priority high

# See what HIGH priority repos would be downloaded
python crawlers/run_download_github.py --priority high --dry-run

# Download everything (all categories, all priorities)
python crawlers/run_download_github.py
```

**Categories:**
- `aggregators`: Awesome lists and curated collections
- `audit_repos`: Audit report repositories
- `vulnerability_datasets`: Labeled vulnerability datasets
- `educational`: Educational resources and tutorials

**Output:**
- Clones/updates repos to `output/repos/{category}/`
- `output/github_download_summary.json` with results

---

## 💾 crawlers/run_download_kaggle.py

**Purpose:** Download datasets from Kaggle (labeled smart contract vulnerabilities).

**Basic Usage:**
```bash
# Download all configured Kaggle datasets
python crawlers/run_download_kaggle.py

# Check download status
python crawlers/run_download_kaggle.py --status
```

**All Options:**
```bash
python crawlers/run_download_kaggle.py [OPTIONS]

Options:
  --dataset DATASET     Download specific dataset by ID (owner/dataset-name)
  --force               Force re-download even if exists
  --status              Show download status and exit
  -h, --help            Show help message
```

**Examples:**
```bash
# Download all default datasets
python crawlers/run_download_kaggle.py

# Download specific dataset
python crawlers/run_download_kaggle.py --dataset tranduongminhdai/smart-contract-vulnerability-datset

# Check what's already downloaded
python crawlers/run_download_kaggle.py --status

# Force re-download all datasets
python crawlers/run_download_kaggle.py --force
```

**Prerequisites:**
- Kaggle credentials set in `.env` OR `~/.kaggle/kaggle.json`
- `kaggle` package installed

**Default Datasets:**
1. `tranduongminhdai/smart-contract-vulnerability-datset` (12K+ contracts)
2. `bcccdatasets/bccc-vulscs-2023` (36,670 samples)

**Output:**
- Downloads to `output/datasets/kaggle/{dataset_name}/`
- `output/kaggle_download_summary.json` with results

---

## 🤗 crawlers/run_download_huggingface.py

**Purpose:** Download datasets from HuggingFace Hub (large-scale Solidity code).

**Basic Usage:**
```bash
# Download all configured HuggingFace datasets
# WARNING: Very large (~50GB+)
python crawlers/run_download_huggingface.py

# Check download status
python crawlers/run_download_huggingface.py --status
```

**All Options:**
```bash
python crawlers/run_download_huggingface.py [OPTIONS]

Options:
  --dataset DATASET     Download specific dataset by ID (org/name)
  --config CONFIG       Dataset configuration name
  --split SPLIT         Specific split to download (train, test, etc.)
  --force               Force re-download even if exists
  --streaming           Use streaming mode (don't download full dataset)
  --status              Show download status and exit
  -h, --help            Show help message
```

**Examples:**
```bash
# Download all default datasets
python crawlers/run_download_huggingface.py

# Download specific dataset
python crawlers/run_download_huggingface.py --dataset Zellic/smart-contract-fiesta

# Use streaming mode (doesn't download full dataset)
python crawlers/run_download_huggingface.py --dataset Zellic/smart-contract-fiesta --streaming

# Download specific split
python crawlers/run_download_huggingface.py --dataset Zellic/smart-contract-fiesta --split train

# Check what's already downloaded
python crawlers/run_download_huggingface.py --status

# Force re-download
python crawlers/run_download_huggingface.py --force
```

**Prerequisites:**
- `datasets` and `huggingface-hub` packages installed
- Optional: HuggingFace token in `.env` for private datasets

**Default Datasets:**
1. `Zellic/smart-contract-fiesta` (514K deduplicated Solidity contracts, ~50GB)

**Output:**
- Downloads to `output/datasets/huggingface/{dataset_name}/`
- `output/huggingface_download_summary.json` with results

---

## 🔄 Resumability

All scripts are designed to be resumable:

- **GitHub:** Detects existing repos, only updates or clones new ones
- **Kaggle:** Checks for `.download_complete` marker, skips if exists
- **HuggingFace:** Checks for `.download_complete` marker, skips if exists

**To re-download:** Use `--force` flag

---

## 📊 Output Files

### Summary Files
All summary files are JSON format in `output/`:

- `master_download_summary.json` - Overall status from download_all_data.py
- `github_download_summary.json` - GitHub repos download results
- `kaggle_download_summary.json` - Kaggle datasets download results
- `huggingface_download_summary.json` - HuggingFace datasets download results

### Data Files
- `output/repos/{category}/{repo_name}/` - Cloned GitHub repositories
- `output/datasets/kaggle/{dataset_name}/` - Kaggle datasets
- `output/datasets/huggingface/{dataset_name}/` - HuggingFace datasets

---

## 🐛 Common Issues & Solutions

### "Module not found" errors
```bash
# Install all dependencies
pip install -r crawlers/requirements.txt
```

### "GitHub API rate limit exceeded"
```bash
# Add GITHUB_TOKEN to .env (increases from 60 to 5000 req/hr)
echo "GITHUB_TOKEN=your_token_here" >> .env
```

### "Kaggle unauthorized"
```bash
# Verify credentials
python -c "from config.settings import KAGGLE_USERNAME, KAGGLE_KEY; print(f'User: {KAGGLE_USERNAME}')"

# Or set up ~/.kaggle/kaggle.json
mkdir -p ~/.kaggle
# Copy kaggle.json there
chmod 600 ~/.kaggle/kaggle.json
```

### "Permission denied" when running scripts
```bash
# Make executable (Linux/Mac)
chmod +x verify_setup.py download_all_data.py crawlers/run_download_*.py

# Or run with python explicitly
python verify_setup.py
```

### Downloads are very slow
```bash
# For HuggingFace, use streaming mode
python crawlers/run_download_huggingface.py --streaming

# For GitHub, download only HIGH priority
python crawlers/run_download_github.py --priority high
```

---

## 📈 Progress Monitoring

### Real-time Progress
All scripts output detailed progress logs:
- Current file being downloaded
- Success/failure status
- Summary statistics

### Check Downloaded Data
```bash
# Count Solidity files
find output/repos -name "*.sol" | wc -l

# Check directory sizes
du -sh output/*/

# List all datasets
ls -lh output/datasets/*/

# View summary
cat output/master_download_summary.json | python -m json.tool
```

---

## ⚡ Quick Command Reference

```bash
# Setup
python verify_setup.py

# Download everything (skip HuggingFace)
python download_all_data.py --skip-huggingface

# Download only GitHub HIGH priority
python crawlers/run_download_github.py --priority high

# Download only Kaggle
python crawlers/run_download_kaggle.py

# Download only HuggingFace
python crawlers/run_download_huggingface.py

# Check status
python crawlers/run_download_github.py --dry-run
python crawlers/run_download_kaggle.py --status
python crawlers/run_download_huggingface.py --status

# View results
cat output/master_download_summary.json
find output -type f -name "*.sol" | wc -l
```

---

## 🎯 Recommended Workflow

1. **Verify setup:**
   ```bash
   python verify_setup.py
   ```

2. **Download essential data (2-3 hours):**
   ```bash
   python download_all_data.py --skip-huggingface
   ```

3. **Verify downloads:**
   ```bash
   cat output/master_download_summary.json
   ```

4. **Optional: Download large datasets (4-6 hours):**
   ```bash
   python crawlers/run_download_huggingface.py
   ```

5. **Explore data:**
   ```bash
   find output/repos/vulnerability_datasets -name "*.sol"
   ```

---

**For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)**

**For quick start, see [QUICK_START.md](QUICK_START.md)**
