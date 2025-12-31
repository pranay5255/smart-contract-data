# Smart Contract Data Collection - Setup Guide

This guide will help you set up and run the data download pipeline on your desktop machine.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Running Downloads](#running-downloads)
- [Data Sources Overview](#data-sources-overview)
- [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Start

If you're in a hurry, here's the fastest path to get data:

```bash
# 1. Copy this repository to your desktop machine

# 2. Install dependencies
cd smart-contract-data
pip install -r crawlers/requirements.txt

# 3. Set up credentials (see .env.example)
cp .env.example .env
# Edit .env and add your API tokens

# 4. Verify setup
python verify_setup.py

# 5. Download HIGH priority GitHub repos only (fastest, ~1-2 hours)
python crawlers/run_download_github.py --priority high

# 6. Optional: Download Kaggle datasets (requires credentials, ~30 min)
python crawlers/run_download_kaggle.py

# 7. Optional: Download HuggingFace datasets (LARGE ~50GB+, several hours)
python crawlers/run_download_huggingface.py
```

---

## 📦 Detailed Setup

### 1. Prerequisites

- **Python 3.10+** (check with `python --version`)
- **Git** installed and in PATH
- **Sufficient disk space**:
  - GitHub repos: ~5-10 GB
  - Kaggle datasets: ~2-5 GB
  - HuggingFace datasets: ~50+ GB (Zellic dataset is very large)
  - **Total recommended: 70+ GB free**

### 2. Install Python Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r crawlers/requirements.txt
```

**Required packages:**
- Core: `requests`, `pyyaml`, `loguru`, `gitpython`
- Kaggle: `kaggle`
- HuggingFace: `datasets`, `huggingface-hub`

### 3. Set Up API Credentials

#### GitHub (Recommended but Optional)

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scope: `public_repo`
4. Copy the token
5. Add to `.env`: `GITHUB_TOKEN=your_token_here`

**Why?** Without a token, GitHub API limits you to 60 requests/hour. With a token, you get 5000 requests/hour.

#### Kaggle (Required for Kaggle Datasets)

**Option 1: Using .env file**
1. Go to https://www.kaggle.com/settings
2. Scroll to "API" section
3. Click "Create New API Token" (downloads `kaggle.json`)
4. Open `kaggle.json` and copy username and key
5. Add to `.env`:
   ```
   KAGGLE_USERNAME=your_username
   KAGGLE_KEY=your_api_key
   ```

**Option 2: Using kaggle.json**
1. Download `kaggle.json` as above
2. Place it in `~/.kaggle/kaggle.json` (create directory if needed)
3. Set permissions (Linux/Mac): `chmod 600 ~/.kaggle/kaggle.json`

#### HuggingFace (Optional)

1. Go to https://huggingface.co/settings/tokens
2. Create a new token with "Read" access
3. Add to `.env`: `HUGGINGFACE_TOKEN=your_token_here`

**Why?** Only needed for private datasets. Public datasets work without a token.

### 4. Verify Setup

Run the verification script to check everything is configured correctly:

```bash
python verify_setup.py
```

This will check:
- ✓ Python version
- ✓ Git installation
- ✓ Required packages
- ✓ Environment variables
- ✓ Directory permissions
- ✓ Configuration files

Fix any errors before proceeding.

---

## 🎯 Running Downloads

### Option 1: Download Everything (Recommended)

```bash
# Download all data sources in priority order
python download_all_data.py

# This will:
# 1. Download HIGH priority GitHub repos (~1-2 hours)
# 2. Download Kaggle datasets (~30 min)
# 3. Ask before downloading HuggingFace (very large)
```

**Flags:**
- `--dry-run`: See what would be downloaded without downloading
- `--skip-huggingface`: Skip the large HuggingFace download
- `--skip-kaggle`: Skip Kaggle downloads
- `--github-priority medium`: Include MEDIUM priority repos too
- `--force`: Re-download everything even if it exists

### Option 2: Download Individually

#### GitHub Repositories

```bash
# Download HIGH priority repos only (recommended)
python crawlers/run_download_github.py --priority high

# Download specific categories
python crawlers/run_download_github.py --categories vulnerability_datasets audit_repos

# Download ALL repos (including MEDIUM and LOW priority)
python crawlers/run_download_github.py

# List available categories
python crawlers/run_download_github.py --list-categories

# Dry run (see what would be downloaded)
python crawlers/run_download_github.py --priority high --dry-run
```

#### Kaggle Datasets

```bash
# Download all configured Kaggle datasets
python crawlers/run_download_kaggle.py

# Download specific dataset
python crawlers/run_download_kaggle.py --dataset tranduongminhdai/smart-contract-vulnerability-datset

# Check download status
python crawlers/run_download_kaggle.py --status

# Force re-download
python crawlers/run_download_kaggle.py --force
```

#### HuggingFace Datasets

```bash
# Download all configured HuggingFace datasets
# WARNING: This is VERY LARGE (~50GB+)
python crawlers/run_download_huggingface.py

# Download specific dataset
python crawlers/run_download_huggingface.py --dataset Zellic/smart-contract-fiesta

# Check download status
python crawlers/run_download_huggingface.py --status

# Use streaming mode (don't download full dataset)
python crawlers/run_download_huggingface.py --streaming
```

---

## 📊 Data Sources Overview

### Priority 1: GitHub Repositories (HIGH Priority)

**Labeled Vulnerability Datasets:**
- SmartBugs Curated (143 contracts, 208 vulnerabilities)
- SmartBugs Wild (47,398 contracts)
- SolidiFI Benchmark (9,369 bugs)
- DeFiHackLabs (550+ exploit PoCs) ⭐ **Critical for evaluation**
- Tintinweb VulnDB (JSON vulnerability database)

**Audit Reports:**
- Sherlock Reports
- Cyfrin Audit Reports
- Pashov Audits
- SigP Public Audits
- Hexens Public Reports
- MixBytes Public Audits
- Nethermind Public Reports

**Educational Resources:**
- OpenZeppelin Contracts
- Cyfrin Foundry Course
- RareSkills Puzzles (Solidity, Gas, Huff)

### Priority 2: Kaggle Datasets

- **Smart Contract Vulnerability Dataset** (12K+ labeled contracts)
- **BCCC-VulSCs-2023** (36,670 samples with features)

### Priority 3: HuggingFace Datasets

- **Zellic/smart-contract-fiesta** (514K deduplicated Solidity contracts)
  - ⚠️ **WARNING: Very large dataset (~50GB+)**
  - Critical for continued pretraining phase

---

## 📁 Output Structure

All downloaded data will be organized in the `output/` directory:

```
output/
├── repos/                          # GitHub repositories
│   ├── vulnerability_datasets/     # Labeled vulnerability datasets
│   │   ├── smartbugs-curated/
│   │   ├── smartbugs-wild/
│   │   ├── SolidiFI-benchmark/
│   │   ├── DeFiHackLabs/
│   │   └── smart-contract-vulndb/
│   ├── audit_repos/                # Audit reports
│   │   ├── sherlock-reports/
│   │   ├── cyfrin-audit-reports/
│   │   ├── pashov-audits/
│   │   └── ...
│   ├── educational/                # Educational resources
│   │   ├── openzeppelin-contracts/
│   │   ├── foundry-full-course-cu/
│   │   └── ...
│   └── aggregators/                # Awesome lists and aggregators
│
├── datasets/                       # Downloaded datasets
│   ├── kaggle/                     # Kaggle datasets
│   │   ├── tranduongminhdai_smart-contract-vulnerability-datset/
│   │   └── bcccdatasets_bccc-vulscs-2023/
│   └── huggingface/                # HuggingFace datasets
│       └── Zellic_smart-contract-fiesta/
│
├── github_download_summary.json    # GitHub download results
├── kaggle_download_summary.json    # Kaggle download results
├── huggingface_download_summary.json  # HuggingFace download results
└── master_download_summary.json    # Overall download status
```

---

## ⏱️ Estimated Download Times

Estimates based on typical internet speeds (100 Mbps):

| Data Source | Size | Time | Priority |
|-------------|------|------|----------|
| GitHub HIGH priority repos | ~5-10 GB | 1-2 hours | ⭐⭐⭐ |
| Kaggle datasets | ~2-5 GB | 20-30 min | ⭐⭐⭐ |
| HuggingFace (Zellic) | ~50+ GB | 4-6 hours | ⭐⭐ |
| **Total** | **~60-70 GB** | **5-8 hours** | |

**Recommendation:** Start with GitHub HIGH priority and Kaggle datasets first (total ~2-3 hours). Download HuggingFace later if needed for pretraining.

---

## 🔧 Troubleshooting

### GitHub Clone Failures

**Problem:** Git clone fails with authentication errors
**Solution:**
```bash
# Make sure GITHUB_TOKEN is set
echo $GITHUB_TOKEN  # Should show your token

# Or use git credential manager
git config --global credential.helper store
```

**Problem:** Rate limit exceeded
**Solution:**
- Add GITHUB_TOKEN to .env (increases limit from 60 to 5000 req/hr)
- Wait and retry later
- Use `--priority high` to download fewer repos

### Kaggle Download Failures

**Problem:** "Unauthorized" errors
**Solution:**
```bash
# Verify credentials are set
python -c "from config.settings import KAGGLE_USERNAME, KAGGLE_KEY; print(f'User: {KAGGLE_USERNAME}, Key: {'*' * len(KAGGLE_KEY) if KAGGLE_KEY else 'NOT SET'}')"

# Or check kaggle.json
cat ~/.kaggle/kaggle.json
```

**Problem:** "Dataset not found"
**Solution:**
- Verify dataset ID is correct (owner/dataset-name)
- Check if dataset is public (you may need to accept terms on Kaggle website)

### HuggingFace Download Failures

**Problem:** Download is extremely slow or times out
**Solution:**
```bash
# Use streaming mode instead
python crawlers/run_download_huggingface.py --streaming

# Or download in parts (not implemented yet, but can be added)
```

**Problem:** Out of disk space
**Solution:**
- The Zellic dataset is ~50GB compressed
- Free up space or skip HuggingFace downloads for now
- Use `--skip-huggingface` flag

### General Issues

**Problem:** Import errors
**Solution:**
```bash
# Reinstall dependencies
pip install -r crawlers/requirements.txt

# Verify Python version
python --version  # Should be 3.10+
```

**Problem:** Permission denied errors
**Solution:**
```bash
# Make scripts executable (Linux/Mac)
chmod +x verify_setup.py download_all_data.py
chmod +x crawlers/run_download_*.py

# Or run with python explicitly
python verify_setup.py
```

---

## 📞 Getting Help

1. **Run the verification script:** `python verify_setup.py`
2. **Check logs:** Detailed logs are in the console output
3. **Review summaries:** JSON summary files in `output/` directory
4. **Common issues:** See Troubleshooting section above

---

## 🎯 Next Steps After Download

Once you have the data downloaded:

1. **Verify data integrity:**
   ```bash
   # Check summary files
   cat output/master_download_summary.json
   ```

2. **Explore the data:**
   ```bash
   # Count Solidity files
   find output/repos -name "*.sol" | wc -l

   # List downloaded datasets
   ls -lh output/datasets/*/
   ```

3. **Proceed to Phase 2:** Data processing and normalization (see TASKS.md)

---

## 📝 Notes

- **Data size:** Be prepared for 60-70 GB of data with all sources
- **Time commitment:** Initial download takes 5-8 hours for everything
- **Incremental downloads:** Scripts detect existing data and skip re-downloading
- **Resumable:** If a script fails, re-run it - it will resume from where it left off
- **Credentials:** Never commit `.env` file to version control

---

## ✅ Checklist

Before running downloads:
- [ ] Python 3.10+ installed
- [ ] Git installed
- [ ] Dependencies installed (`pip install -r crawlers/requirements.txt`)
- [ ] `.env` file created with credentials
- [ ] `verify_setup.py` passes all checks
- [ ] Sufficient disk space (70+ GB recommended)

Ready to download:
- [ ] GitHub HIGH priority repos (`run_download_github.py --priority high`)
- [ ] Kaggle datasets (`run_download_kaggle.py`)
- [ ] HuggingFace datasets (`run_download_huggingface.py`) - Optional, very large

---

**Happy data collecting! 🚀**
