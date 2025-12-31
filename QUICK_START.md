# Quick Start - Data Download Pipeline

**⏱️ Time to first data: 5 minutes setup + 1-2 hours download**

## 🚀 One-Command Setup (If you have all credentials)

```bash
# 1. Install dependencies
pip install -r crawlers/requirements.txt

# 2. Set up environment (edit with your tokens)
cp .env.example .env
nano .env  # or use your preferred editor

# 3. Verify everything is ready
python verify_setup.py

# 4. Download all HIGH priority data
python download_all_data.py --skip-huggingface
```

---

## 📋 Get API Credentials (5 minutes)

### 1. GitHub Token (Recommended)
- Go to: https://github.com/settings/tokens
- Click: "Generate new token (classic)"
- Select: `public_repo` scope
- Copy token → Add to `.env` as `GITHUB_TOKEN=your_token`

### 2. Kaggle Credentials (Required for Kaggle datasets)
- Go to: https://www.kaggle.com/settings
- Click: "Create New API Token" (downloads kaggle.json)
- Copy username and key → Add to `.env`:
  ```
  KAGGLE_USERNAME=your_username
  KAGGLE_KEY=your_api_key
  ```

### 3. HuggingFace Token (Optional)
- Go to: https://huggingface.co/settings/tokens
- Create "Read" token
- Copy token → Add to `.env` as `HUGGINGFACE_TOKEN=your_token`

---

## 🎯 Prioritized Download Strategy

### Phase 1: Essential Data (2-3 hours, 15 GB)
```bash
# HIGH priority GitHub repos + Kaggle datasets
python download_all_data.py --skip-huggingface
```

**What you get:**
- ✅ SmartBugs Curated (143 labeled vulnerable contracts)
- ✅ SmartBugs Wild (47K contracts)
- ✅ SolidiFI Benchmark (9,369 bugs)
- ✅ DeFiHackLabs (550+ exploit PoCs)
- ✅ Audit reports (Sherlock, Cyfrin, Pashov, etc.)
- ✅ Educational resources (OpenZeppelin, RareSkills)
- ✅ Kaggle datasets (12K+ labeled contracts)

### Phase 2: Large-Scale Code (4-6 hours, 50 GB)
```bash
# HuggingFace datasets (run separately, very large)
python crawlers/run_download_huggingface.py
```

**What you get:**
- ✅ Zellic smart-contract-fiesta (514K deduplicated contracts)

---

## ⚡ Individual Downloads (Pick and Choose)

### Just GitHub Repos
```bash
# HIGH priority only (recommended)
python crawlers/run_download_github.py --priority high

# Specific categories
python crawlers/run_download_github.py --categories vulnerability_datasets audit_repos

# Everything
python crawlers/run_download_github.py
```

### Just Kaggle
```bash
python crawlers/run_download_kaggle.py
```

### Just HuggingFace
```bash
python crawlers/run_download_huggingface.py
```

---

## 🔍 Check What You'll Download (No actual downloads)

```bash
# See all HIGH priority GitHub repos
python crawlers/run_download_github.py --priority high --dry-run

# See all categories
python crawlers/run_download_github.py --list-categories

# Check Kaggle status
python crawlers/run_download_kaggle.py --status

# Check HuggingFace status
python crawlers/run_download_huggingface.py --status
```

---

## 📊 Download Status

After downloads complete, check summaries:

```bash
# Overall summary
cat output/master_download_summary.json

# GitHub summary
cat output/github_download_summary.json

# Kaggle summary
cat output/kaggle_download_summary.json

# Quick stats
find output/repos -name "*.sol" | wc -l  # Count Solidity files
du -sh output/*/  # Check sizes
```

---

## 🐛 Troubleshooting

### Setup Issues
```bash
# Run verification
python verify_setup.py

# Check Python version (need 3.10+)
python --version

# Reinstall dependencies
pip install -r crawlers/requirements.txt
```

### Download Issues
```bash
# GitHub: Make sure token is set
echo $GITHUB_TOKEN

# Kaggle: Check credentials
cat ~/.kaggle/kaggle.json

# Retry failed downloads (safe, won't re-download existing data)
python download_all_data.py
```

---

## 📝 Data Location

All data goes to `output/` directory:
```
output/
├── repos/
│   ├── vulnerability_datasets/  # SmartBugs, SolidiFI, etc.
│   ├── audit_repos/             # Audit reports
│   └── educational/             # Educational resources
└── datasets/
    ├── kaggle/                  # Kaggle datasets
    └── huggingface/             # HuggingFace datasets
```

---

## ⏱️ Time & Space Estimates

| What | Size | Time (100 Mbps) | Priority |
|------|------|-----------------|----------|
| GitHub HIGH priority | ~10 GB | 1-2 hours | ⭐⭐⭐ Essential |
| Kaggle datasets | ~5 GB | 20-30 min | ⭐⭐⭐ Essential |
| HuggingFace (Zellic) | ~50 GB | 4-6 hours | ⭐⭐ Important |

**Recommendation:** Start with Phase 1 (GitHub + Kaggle) = 2-3 hours total

---

## ✅ Quick Checklist

Before starting:
- [ ] Python 3.10+ installed
- [ ] Git installed
- [ ] 70+ GB free disk space
- [ ] API credentials ready (GitHub, Kaggle, HuggingFace)
- [ ] Dependencies installed
- [ ] `.env` file configured

To download:
- [ ] Run `python verify_setup.py` ✓
- [ ] Run `python download_all_data.py --skip-huggingface` ✓
- [ ] Optional: Run `python crawlers/run_download_huggingface.py` ✓

---

## 🎯 Next Steps

After downloads complete:

1. **Verify data:**
   ```bash
   cat output/master_download_summary.json
   ```

2. **Explore:**
   ```bash
   ls -R output/repos/vulnerability_datasets/
   ```

3. **Next phase:** Data processing (see TASKS.md Phase 2)

---

**Need more details?** See [SETUP_GUIDE.md](SETUP_GUIDE.md) for comprehensive documentation.
