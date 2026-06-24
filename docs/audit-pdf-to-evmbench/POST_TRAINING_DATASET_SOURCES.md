# Post-Training Dataset Sources

This document inventories Hugging Face and local smart-contract security datasets that can support the post-training recipes in `POST_TRAINING_RECIPES.md`.

The review policy in `HUMAN_REVIEW.md` is the gating policy for anything that becomes an EVMBench task. These datasets can help generate, filter, or train on candidate records, but they do not bypass human review.

The current implementation target is detect mode. Patch-mode and exploit-mode notes in this document are planning notes only. They describe how the same source pools may become useful once the detect-mode pipeline is reliable and the review policy is expanded.

## Selection Policy

- Use reviewed Solidity/EVM detect-mode tasks as the default high-trust source for serious SFT and RL experiments.
- Treat external labels, generated summaries, and incident writeups as untrusted until normalized and sampled.
- Do not use patch or exploit material as agent-visible context for v1 detect-mode tasks.
- Do not train on gold findings for tasks reserved for benchmark evaluation.
- Preserve source URL, dataset revision, license, original path, and any transformation code in provenance records.
- Keep raw corpora, normalized examples, admitted tasks, and held-out evaluation tasks in separate splits.

## Your Hugging Face Uploads From 2026-06-24

These are public datasets under `pranay5255`. They are useful as source pools, but most are raw artifact collections rather than ready-to-train records.

### `pranay5255/smart-contract-audit-pdfs`

- HF URL: `https://huggingface.co/datasets/pranay5255/smart-contract-audit-pdfs`
- Current shape: file tree of audit report PDFs, 4,088 files.
- Example paths: `repos/audit_repos/PublicAuditReports/*.pdf`.
- Best use:
  - Primary source for OCR, finding extraction, and candidate EVMBench detect-task generation.
  - Source material for SFT only after OCR, finding normalization, repository matching, and human review.
- RL-env use:
  - Indirect only. PDFs become RL environments only after they produce approved EVMBench detect-mode task folders.
- Caveats:
  - Raw PDFs are not training rows.
  - OCR uncertainty, licensing, audited commit matching, and gold leakage must be checked before admission.

### `pranay5255/smart-contract-audit-nonpdf-artifacts`

- HF URL: `https://huggingface.co/datasets/pranay5255/smart-contract-audit-nonpdf-artifacts`
- Current shape: mixed non-PDF files from audit repositories, 948 files.
- Example paths: `Auditing/*.md`, `PublicReports/*/Readme.md`, Solidity snippets, images, repository metadata.
- Best use:
  - Supplemental context for source discovery, audit-firm metadata, repo matching, and retrieval indexes.
  - Potential SFT examples only after filtering down to audited Solidity/EVM content.
- RL-env use:
  - Usually indirect. These artifacts can help verify candidates, not define a task by themselves.
- Caveats:
  - Mixed scope includes non-EVM, operational docs, images, and non-audit material.
  - Needs filtering and provenance tagging before use.

### `pranay5255/smart-contract-vulnerability-benchmarks`

- HF URL: `https://huggingface.co/datasets/pranay5255/smart-contract-vulnerability-benchmarks`
- Current shape: raw benchmark repository snapshots, 5,307 files.
- Current contents: SmartBugs Curated, SmartBugs Wild, SolidiFI, and Tintinweb VulnDB.
- Example formats: Solidity files, JSON labels, CSV bug logs, benchmark README files.
- Best use:
  - SFT for vulnerability identification, classification, and short explanation generation.
  - Evaluation data for detectors that consume individual contracts or labeled snippets.
  - Seed material for taxonomy mapping between benchmark labels and EVMBench findings.
- RL-env use:
  - Possible but not direct. These are not EVMBench task folders. A separate wrapper would need to provide repository state, prompt, hidden labels, and grader.
- Caveats:
  - DeFiHackLabs was cloned locally after this upload and is not currently included in this HF dataset.
  - Many examples are synthetic or benchmark-specific rather than real audit tasks.

### `pranay5255/smart-contract-kaggle-source-files`

- HF URL: `https://huggingface.co/datasets/pranay5255/smart-contract-kaggle-source-files`
- Current shape: source-code CSV shards plus metadata, 14 files.
- Example paths:
  - `csv_source_files/bccc_secure_source_codes/data-*.csv`
  - `csv_source_files/bccc_vulnerable_source_codes/data-*.csv`
  - Kaggle `.download_complete` and `metadata.json` files.
- Best use:
  - SFT or classifier training for secure vs vulnerable contrastive examples.
  - Data balancing for simple vulnerability classification curricula.
- RL-env use:
  - Low direct value for EVMBench. It lacks repository context, hidden gold reports, and a task runtime.
- Caveats:
  - CSV shards need schema inspection before mixing with finding-level audit data.

### `pranay5255/smart-contract-csv-datasets`

- HF URL: `https://huggingface.co/datasets/pranay5255/smart-contract-csv-datasets`
- Current shape: original CSV tables and manifest, 7 files.
- Example files:
  - `SC_4label.csv`
  - `SC_Vuln_8label.csv`
  - `BCCC-VolSCs-2023_Secure.csv`
  - `BCCC-VolSCs-2023_Vulnerable.csv`
- Best use:
  - Label-supervised SFT or classifier training.
  - Vulnerability type pretraining before higher-quality audit-report SFT.
- RL-env use:
  - Not directly suitable. These are row-level labels, not executable task environments.
- Caveats:
  - Label definitions may not align with EVMBench loss-of-funds findings.
  - Keep separate from benchmark held-out tasks.

### `pranay5255/smart-contract-aggregators-educational`

- HF URL: `https://huggingface.co/datasets/pranay5255/smart-contract-aggregators-educational`
- Current shape: mixed repository snapshots, 1,041 files.
- Example contents: awesome lists, RareSkills puzzles, Cyfrin course files, OpenZeppelin contracts.
- Best use:
  - Retrieval corpus for background security knowledge.
  - Low-stakes curriculum SFT for Solidity fluency, terminology, and secure coding style.
- RL-env use:
  - Not directly suitable for EVMBench detect-mode RL.
- Caveats:
  - Educational material is not reviewed gold vulnerability data.
  - Avoid letting generic best-practice text dominate audit-report training mixes.

## DeFiHackLabs Family

### Local Raw Clone: `SunWeb3Sec/DeFiHackLabs`

- Local path: `crawlers/output/repos/vulnerability_datasets/DeFiHackLabs`
- Source URL: `https://github.com/SunWeb3Sec/DeFiHackLabs`
- Current local shape: Foundry-style exploit reproduction repository.
- Current local counts: 865 files, 785 Solidity files, 69 Markdown files, about 11 MB.
- Typical paths: `src/test/YYYY-MM/*_exp.sol`, `past/YYYY/README.md`, `academy/**/readme.md`.
- Best use:
  - SFT examples for exploit-root-cause explanation, incident-to-code reasoning, and vulnerability taxonomy mapping.
  - Candidate mining for real incident patterns that can later be paired with audited repository snapshots.
  - Future patch/exploit-mode research after v1 detect extraction is proven.
- RL-env use:
  - Not v1 detect-mode as-is. It is closer to exploit-mode material.
  - Could support future exploit RL environments if wrapped with Foundry tests, hidden targets, and safe grading.
  - For v1, use only as background/source evidence during candidate generation, not as agent-visible gold.
- Caveats:
  - This raw clone is not yet in your HF uploads from 2026-06-24.
  - Exploit PoCs can leak answers if included in detect-task prompts.
  - Must be screened for educational-only licensing and safety constraints before public dataset redistribution.

### `akshaynexus/DeFiHackLabs-Dataset`

- HF URL: `https://huggingface.co/datasets/akshaynexus/DeFiHackLabs-Dataset`
- Current shape: processed JSON/JSONL dataset and contract artifacts, 36 files.
- Example files:
  - `data/contracts/contracts.compact.json`
  - `data/output/dataset.json`
  - `data/output/dataset.backup.json`
  - `output/incidents.jsonl`
- HF tags: JSON, tabular/text, machine-generated annotations, text classification, summarization.
- Best use:
  - SFT for incident summaries, vulnerability categorization, and exploit explanation drafts.
  - Bootstrap labels for candidate triage.
- RL-env use:
  - Low direct value. It is processed incident data, not an executable environment.
- Caveats:
  - Machine-generated fields require sampling and validation.
  - Do not treat summaries as reviewed gold findings.

### `seyyedaliayati/solidity-defi-vulnerabilities`

- HF URL: `https://huggingface.co/datasets/seyyedaliayati/solidity-defi-vulnerabilities`
- Current shape: one Parquet training file plus README.
- Approximate size class: fewer than 1,000 rows.
- HF tags: Solidity, vulnerability, smart contract, DeFi hacks, text classification, text generation.
- Best use:
  - Small DeFi vulnerability SFT or classification warmup.
  - Quick sanity-check evaluation for DeFi exploit terminology.
- RL-env use:
  - Not directly suitable.
- Caveats:
  - Small dataset. Use as supplemental data only.
  - Check exact schema before mixing with larger audit-finding corpora.

### `Farseen0/scar-eval`

- HF URL: `https://huggingface.co/datasets/Farseen0/scar-eval`
- Current shape: Parquet held-out evaluation pairs, 838 rows according to the dataset card.
- HF tags: smart contracts, Solidity, security, evaluation, benchmark, text retrieval.
- Source mix includes DeFiHackLabs as one component.
- Best use:
  - Retrieval/evaluator benchmarking.
  - Held-out evaluation for vulnerability-related embeddings or rerankers.
- RL-env use:
  - Not an EVMBench environment, but can evaluate retrieval components used before task generation.
- Caveats:
  - Keep as evaluation data, not SFT training data, if using the SCAR ecosystem for retrieval benchmarks.

### Related SCAR Datasets

- `Farseen0/scar-pairs`
  - Shape: Parquet training pairs, about 1K to 10K rows.
  - Use: contrastive retrieval training for code/finding matching.
- `Farseen0/scar-pairs-extended`
  - Shape: Parquet training pairs, about 10K to 100K rows.
  - Use: larger retrieval/reranking training.
- `Farseen0/scar-corpus`
  - Shape: 10 Parquet shards, about 100K to 1M rows.
  - Use: Solidity security retrieval corpus.
- Caveat:
  - These are retrieval resources, not reviewed EVMBench tasks.

## Similar And Newly Found Hugging Face Candidates

### `aissacas/solidity-rekt-dataset`

- HF URL: `https://huggingface.co/datasets/aissacas/solidity-rekt-dataset`
- Created: 2026-05-20.
- Current shape: JSONL training files.
- Example files: `mog_train.jsonl`, `ngmi_train.jsonl`, `rekt_train.jsonl`.
- HF tags: Solidity, smart contract, vulnerability detection, security, reentrancy, DeFi, exploit.
- Best use:
  - SFT for incident-style vulnerability reports and exploit explanations.
  - Classifier or reward-model data after schema inspection.
- RL-env use:
  - Not direct. It can help write or judge reports, but does not define executable tasks.
- Caveats:
  - Needs schema and label semantics review.

### `daveytea/x23-solidity-vulnerabilities-audit-findings`

- HF URL: `https://huggingface.co/datasets/daveytea/x23-solidity-vulnerabilities-audit-findings`
- Created: 2026-05-06.
- Current shape: large Parquet/JSONL corpus with embedding files, 136 files.
- Example files: `data/embedding_texts.jsonl`, `data/embedding_texts-*.parquet`, `data/embeddings_long-*.parquet`.
- Best use:
  - Retrieval indexes, embedding/reranking experiments, and finding clustering.
  - Possible SFT after extracting non-embedding source text records.
- RL-env use:
  - Indirect only.
- Caveats:
  - Embedding-heavy layout is not immediately usable as audit-report SFT.
  - Must separate source text from derived vectors.

### `samscrack/solidity-audit-cot`

- HF URL: `https://huggingface.co/datasets/samscrack/solidity-audit-cot`
- Created: 2026-05-04.
- Current shape: JSONL, `audit_cot_clean.jsonl`.
- HF tags: Solidity, smart contracts, audit, chain-of-thought, security, reasoning.
- Best use:
  - SFT for audit reasoning style only after policy and quality review.
  - Prefer extracting final answers or concise rationales rather than training on hidden chain-of-thought.
- RL-env use:
  - Not direct. Could supply preference or critique data after filtering.
- Caveats:
  - Chain-of-thought provenance and quality must be scrutinized.
  - Do not mix with benchmark gold reports without split controls.

### `oxdev/smart-contract-security-audit-v2`

- HF URL: `https://huggingface.co/datasets/oxdev/smart-contract-security-audit-v2`
- Created: 2026-04-25.
- Current shape: Parquet train/validation split.
- Example files: `data/train-00000-of-00001.parquet`, `data/validation-00000-of-00001.parquet`.
- Best use:
  - SFT and validation for audit finding generation or classification.
  - Baseline validation mix for report-quality prompts.
- RL-env use:
  - Not direct.
- Caveats:
  - Need inspect schema and deduplicate against your audit PDFs.

### `xanoutas/solidity-security-findings`

- HF URL: `https://huggingface.co/datasets/xanoutas/solidity-security-findings`
- Created: 2026-04-01.
- Current shape: JSON, `security_findings.json`.
- HF tags: Solidity, security, smart contracts, vulnerabilities, Web3.
- Best use:
  - SFT for finding writeups, severity labels, and vulnerability descriptions.
  - Candidate taxonomy mapping.
- RL-env use:
  - Not direct.
- Caveats:
  - Validate source attribution and severity semantics.

### `web3se/smart-contract-intent-vul-dataset`

- HF URL: `https://huggingface.co/datasets/web3se/smart-contract-intent-vul-dataset`
- Created: 2026-02-01.
- Current shape: compressed SQL dump, `web3_all.sql.gz`.
- HF tags: code, text classification.
- Best use:
  - Vulnerability taxonomy, label mapping, and contract-intent features.
  - Classifier pretraining after SQL extraction.
- RL-env use:
  - Not direct.
- Caveats:
  - Requires database import or SQL parsing before normalization.
  - Schema may be contract-level rather than finding-level.

### `SkywardNomad92/smart-contract-audit-findings`

- HF URL: `https://huggingface.co/datasets/SkywardNomad92/smart-contract-audit-findings`
- Created: 2026-01-28.
- Current shape: JSONL train/validation split.
- Example files: `data/train.jsonl`, `data/validation.jsonl`.
- HF tags: smart contracts, security, audit, Solidity, blockchain, vulnerability detection.
- Best use:
  - SFT for final audit report style and finding descriptions.
  - DPO or reward-model pair construction if paired with lower-quality generated reports.
- RL-env use:
  - Indirect. It can train report writers or judges, not task environments.
- Caveats:
  - Deduplicate against your audit-report corpus before training.

### `jhsu12/solidity-vuln-detect-sft-data`

- HF URL: `https://huggingface.co/datasets/jhsu12/solidity-vuln-detect-sft-data`
- Created: 2026-04-22.
- Current shape: Parquet train/test split.
- Example files: `data/train-00000-of-00001.parquet`, `data/test-00000-of-00001.parquet`.
- Best use:
  - SFT warmup for vulnerability detection prompts.
  - Held-out sanity checks if train/test are kept separate.
- RL-env use:
  - Not direct.
- Caveats:
  - Inspect prompt/answer fields before mixing with audit-report data.

### `jhsu12/solidity-vulnerability-eval-dataset`

- HF URL: `https://huggingface.co/datasets/jhsu12/solidity-vulnerability-eval-dataset`
- Created: 2026-04-24.
- Current shape: Parquet, one train file.
- Best use:
  - Lightweight eval set for vulnerability classification/detection.
- RL-env use:
  - Not direct.
- Caveats:
  - Despite the name, confirm whether it is safe to use as evaluation only.

### Additional Narrow Candidates To Triage

- `jhsu12/solidity-vuln-expert-reentrancy`
- `jhsu12/solidity-vuln-expert-access-control`
- `jhsu12/solidity-vuln-expert-integer-overflow-underflow`
- `jhsu12/solidity-vuln-expert-timestamp-dependence`
- `jhsu12/solidity-vuln-expert-unchecked-low-level-calls`
- `samscrack/solidity-eval-2026`
- `samscrack/solidity-cpt-top10-quality`
- `samscrack/c4-audit-findings`
- `samscrack/cyfrin-audit-findings`
- `msc-smart-contract-auditing/audits-with-reasons`
- `msc-smart-contract-auditing/vulnerability-severity-classification`
- `mwritescode/slither-audited-smart-contracts`
- `Zellic/smart-contract-fiesta`

These are worth metadata and schema inspection, but should not be admitted to the training plan until their licenses, schemas, duplication risk, and label quality are understood.

## Mapping To Post-Training Uses

### SFT

Good SFT candidates:

- Reviewed EVMBench gold reports from admitted training splits.
- Normalized audit-finding JSONL from your OCR pipeline after human review.
- External finding corpora such as `SkywardNomad92/smart-contract-audit-findings`, `xanoutas/solidity-security-findings`, and `oxdev/smart-contract-security-audit-v2` after deduplication and schema validation.
- DeFiHackLabs-derived records for incident explanation and vulnerability taxonomy, not for benchmark gold.
- Kaggle and SmartBugs/SolidiFI rows for classifier-style vulnerability warmup.

Avoid direct SFT on:

- Raw PDFs.
- Raw exploit PoCs.
- Unreviewed machine-generated summaries.
- Evaluation splits intended for retrieval or benchmark measurement.

### RL Environments

Direct RL environment candidates:

- Only admitted EVMBench detect-mode task folders with hidden gold findings and a working grader.

Indirect RL support data:

- Audit PDFs and non-PDF artifacts can generate candidates.
- SCAR datasets can train retrieval components used before task generation.
- DeFiHackLabs raw PoCs can inform future exploit-mode environments, but not v1 detect-mode.
- Finding datasets can train reward models or report judges only after calibration against EVMBench scores.

Not sufficient by themselves:

- CSV labels, Parquet finding rows, JSONL summaries, SQL dumps, and raw repository corpora. These lack the complete task runtime, prompt, hidden answer, and grader required for RL.

### DPO Or Preference Data

Useful sources:

- EVMBench rollouts with different detect scores for the same task.
- External audit-finding datasets as chosen examples paired against model-generated rejected reports.
- Human-reviewed candidate revisions where a bad report was corrected.

Required controls:

- Same task prompt and environment for chosen/rejected pairs.
- Clear score or review separation.
- No use of evaluation-task gold reports in training.

## Patch-Mode Planning

Patch mode needs a different evidence standard than detect mode. A finding description is not enough. A useful patch task needs vulnerable code, a target fix or expected behavior, tests that fail before the fix, and hidden validation that catches superficial patches.

### Patch Data Requirements

- Vulnerable repository snapshot.
- Finding text or issue description.
- A minimal fix diff, fixed commit, or reviewed patch reference.
- Public or generated regression tests.
- Hidden tests or exploit replay that distinguish correct fixes from cosmetic changes.
- Build instructions that work inside the EVMBench-style Docker image.
- Provenance linking the finding, vulnerable commit, fixed commit or patch, and tests.

### Dataset Fit For Patch Mode

- `pranay5255/smart-contract-audit-pdfs`
  - Useful for extracting finding descriptions, impact, recommendations, and affected functions.
  - Not enough alone because most PDFs do not include machine-applyable patches.
- `pranay5255/smart-contract-audit-nonpdf-artifacts`
  - Useful when audit repos include Markdown advisories, patched snippets, or issue metadata.
  - Needs matching to source repositories and commits.
- `pranay5255/smart-contract-vulnerability-benchmarks`
  - SmartBugs and SolidiFI can support synthetic or benchmark patch tasks.
  - SolidiFI is especially useful when injected-bug and original/fixed variants can be paired.
- `pranay5255/smart-contract-kaggle-source-files` and `pranay5255/smart-contract-csv-datasets`
  - Useful for patch-classification warmup and vulnerable/secure contrastive examples.
  - Weak as patch tasks because row-level CSV labels usually lack tests and repository state.
- Raw `DeFiHackLabs`
  - Useful for deriving regression tests from exploit PoCs.
  - Better as hidden validation than as patch prompt material.
- External finding corpora such as `SkywardNomad92/smart-contract-audit-findings`, `xanoutas/solidity-security-findings`, and `oxdev/smart-contract-security-audit-v2`
  - Useful for SFT examples that explain how to fix a finding.
  - Need code and tests before they become patch environments.

### Patch SFT Records

Candidate patch SFT records should look like:

```json
{"record_id":"patch-sft-example","task_mode":"patch","prompt_parts":{"finding_ref":"...","repo_snapshot_ref":"...","affected_files":["..."]},"assistant_output":{"patch_diff_ref":"...","explanation_ref":"..."},"source":"reviewed_patch_pair","split":"train","provenance_ref":"..."}
```

High-quality patch SFT examples should include:

- The vulnerability description.
- The affected code context.
- The minimal patch diff.
- A short explanation of why the patch closes the root cause.
- Test evidence when available.

### Patch RL Environments

Patch RL environments should reward behavior, not style:

- Build succeeds.
- Existing tests still pass.
- Regression tests fail before the patch and pass after the patch.
- Hidden exploit or invariant tests fail before the patch and pass after the patch.
- The patch does not remove core functionality or hard-code test values.

Potential reward fields:

- `build_passed`
- `public_tests_passed`
- `hidden_regression_passed`
- `exploit_replay_blocked`
- `patch_minimality_score`

### Patch-Mode Caveats

- Patch tasks can leak answers if fixed commits, diffs, or recommendations are copied into the agent-visible repository.
- Many audit reports describe root cause but not sufficient repair details.
- Synthetic benchmark patches may teach narrow bug patterns that do not transfer to real audit tasks.
- Generated tests must be reviewed because weak tests create reward hacking opportunities.

## Exploit-Mode Planning

Exploit mode is closer to DeFiHackLabs than detect mode is. It requires an executable vulnerable system, hidden success conditions, and careful safety boundaries. In planning, exploit mode should focus on historical, local, sandboxed reproductions.

### Exploit Data Requirements

- Vulnerable repository snapshot or reproducible fork setup.
- Deployment script or local fixture.
- Objective definition, such as drain condition, invariant break, unauthorized state transition, or balance delta.
- Hidden grade script or Foundry/Hardhat test.
- Optional public hints for low, medium, high, and max hint regimes.
- Clear separation between agent-visible code and hidden exploit solution.
- Safety notes confirming that the target is historical, local, or otherwise non-live.

### Dataset Fit For Exploit Mode

- Raw `DeFiHackLabs`
  - Strongest current source for exploit-mode planning.
  - Format is mostly Foundry PoCs under `src/test/YYYY-MM/*_exp.sol`.
  - Can be mined for attacker setup, fork block, target contracts, exploit transaction sequence, and expected profit/balance delta.
- `akshaynexus/DeFiHackLabs-Dataset`
  - Useful for incident metadata, summarization, and selecting incidents for deeper raw-PoC inspection.
  - Not a complete executable exploit environment by itself.
- `seyyedaliayati/solidity-defi-vulnerabilities`
  - Useful for small SFT/eval examples around DeFi exploit classes.
  - Not enough for executable exploit RL.
- `aissacas/solidity-rekt-dataset`
  - Useful for incident narratives and exploit taxonomy.
  - Needs code and reproducible tests before environment use.
- Top-level local `audits/2024-09/AIRBTC`
  - Already resembles an exploit task with Foundry files and an exploit test.
  - Good small fixture for testing exploit-mode packaging conventions.
- Existing EVMBench exploit tasks in `frontier-evals/project/evmbench/audits`
  - Best reference for final shape because they already match the target benchmark harness.

### Exploit SFT Records

Exploit SFT should not teach live-target abuse. Useful records should be framed as historical or sandboxed analysis:

```json
{"record_id":"exploit-sft-example","task_mode":"exploit","prompt_parts":{"vulnerable_repo_ref":"...","objective":"Break the local invariant in the provided sandbox."},"assistant_output":{"exploit_strategy_ref":"...","poc_ref":"..."},"source":"historical_sandboxed_poc","split":"train","safety_context":"historical_local_reproduction","provenance_ref":"..."}
```

High-quality exploit SFT examples can include:

- Root-cause explanation.
- Attack preconditions.
- Minimal transaction sequence.
- Why the exploit succeeds.
- Why the exploit is historical or sandboxed.

### Exploit RL Environments

Exploit RL environments should reward only local, benchmark-defined success:

- Deploys local target.
- Compiles exploit.
- Executes exploit against local or forked historical state.
- Satisfies hidden grade script.
- Does not rely on external live services beyond pinned, reproducible fork state.

Potential reward fields:

- `compile_passed`
- `setup_passed`
- `exploit_executed`
- `profit_or_invariant_score`
- `hidden_grade_passed`

### Exploit-Mode Caveats

- Exploit data is more safety-sensitive than detect or patch data.
- Agent-visible PoCs can trivialize exploit tasks.
- Fork-based reproductions can break when RPCs or archive nodes change.
- Some PoCs depend on live chain state or external contracts that must be pinned and cached.
- Only historical, educational, sandboxed exploit reproductions should be considered.

## Mode-Specific Source Priority

For planning, the same datasets rank differently by mode:

- Detect mode:
  - Highest value: audit PDFs, reviewed audit findings, admitted EVMBench detect tasks.
  - Support value: vulnerability CSVs, SmartBugs/SolidiFI, SCAR retrieval data.
- Patch mode:
  - Highest value: paired vulnerable/fixed code, fixed commits, reviewed diffs, regression tests.
  - Support value: audit recommendations, SolidiFI-style injected bugs, DeFiHackLabs exploit tests as hidden regressions.
- Exploit mode:
  - Highest value: executable historical PoCs, Foundry/Hardhat fixtures, existing EVMBench exploit tasks.
  - Support value: incident writeups, DeFiHackLabs-derived metadata, exploit taxonomy datasets.

## Recommended Next Actions

1. Upload the raw `DeFiHackLabs` clone to a dedicated HF dataset, for example `pranay5255/defihacklabs-raw`, or append it to `pranay5255/smart-contract-vulnerability-benchmarks` with a new revision note.
2. Create a small schema-inspection script for each external HF dataset that records columns, row counts, sample records, license, and duplication risk.
3. Add normalized dataset manifests under `data/post_training_sources/` before downloading large external corpora.
4. Keep `Farseen0/scar-eval` and any other eval-labeled datasets out of SFT unless intentionally reassigned.
5. Build a first detect SFT mix from reviewed findings only, then use the lower-trust external datasets for ablations.
6. Build detect RL records only from admitted EVMBench tasks as described in `POST_TRAINING_RECIPES.md`.
7. For patch planning, start by finding paired vulnerable/fixed examples and tests rather than just finding descriptions.
8. For exploit planning, start with raw DeFiHackLabs and existing EVMBench exploit tasks, but keep PoCs hidden from agent-visible prompts.
