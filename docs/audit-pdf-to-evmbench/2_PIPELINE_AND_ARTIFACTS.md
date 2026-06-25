# Pipeline And Artifacts

This document is the source of truth for how data moves from PDFs to reviewed EVMBench detect-mode tasks. It separates current OCR/materialization artifacts from future extraction, matching, candidate, review, admission, and training artifacts.

## Current Objects And Artifacts

- Current source PDF root used by the chunk planner: `crawlers/output/repos/audit_repos`.
- Current OCR run plan root: `crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624`.
- Current raw OCR output root pattern: `crawlers/output/ocr_runs/unlimited_ocr_modal/raw/<run_id>/chunk_*/<bucket>/<pdf_id>_<slug>/`.
- Current raw PDF-level files from the chunk runner: `pdf_manifest.json`, `pages_XXXX_YYYY.raw.json`, `pages_XXXX_YYYY.summary.json`, `pdf_status.json`, `chunk_progress.jsonl`, and `chunk_summary.json`.
- Current materialization output pattern: `crawlers/output/ocr_runs/unlimited_ocr_modal/artifacts/<run_id>/extracted_pages/<pdf_id>.jsonl`.
- Current materialization summary file: `crawlers/output/ocr_runs/unlimited_ocr_modal/artifacts/<run_id>/materialize_summary.json`.

## Future Artifacts

- `normalized_findings/<pdf_id>.jsonl` for finding extraction.
- `repo_matches.jsonl` for repository and audited-commit matching.
- `candidate_task_manifest.jsonl` and `candidates/<candidate_id>/` for generated detect-mode task candidates.
- `review_status.yaml` updates during review.
- Admitted folders under `frontier-evals/project/evmbench/audits/<audit_id>` only after approval.
- Post-training JSONL exports only after split and provenance policy are explicit.

## Current Pipeline Boundary

The current implemented boundary is PDF inventory/chunk planning, Modal OCR raw responses, and materialized page-level OCR JSONL. Everything after page materialization is planned or review-gated.

## Architecture
The pipeline converts audit PDFs into candidate EVMBench detect-mode tasks through a staged artifact graph. Every stage writes reviewable records. Admission into EVMBench is a separate human-controlled step.

## Data Flow

```text
raw PDFs
  -> pdf_inventory.jsonl
  -> Modal-hosted SGLang Unlimited-OCR
  -> extracted_pages/<pdf_id>.jsonl
  -> finding extraction
  -> normalized_findings/<pdf_id>.jsonl
  -> repo matching
  -> repo_matches.jsonl
  -> candidate generation
  -> candidate task folders + candidate_task_manifest.jsonl
  -> human review
  -> manual admission into frontier-evals/project/evmbench/audits
```

## Components

### PDF Inventory Builder

The inventory builder records every source PDF before OCR. It assigns `pdf_id`, computes checksums, captures source metadata, and marks whether the PDF is eligible for v1 processing.

v1 eligibility requires Solidity/EVM relevance. PDFs for non-EVM ecosystems stay in inventory but should not advance to candidate task generation.

### OCR Service

OCR is performed through the Modal-hosted SGLang `baidu/Unlimited-OCR` endpoint documented in [3_OCR_RUNBOOK.md](3_OCR_RUNBOOK.md). The endpoint contract should preserve:

- PDF ID and page number.
- OCR text.
- Any detected layout blocks, tables, or code blocks when available.
- Confidence or quality signals when available.
- Model name, backend, endpoint version, and request timestamp.

The OCR layer should be idempotent. Re-running a page with the same model and input checksum should either reuse the existing page record or write a new versioned record.

### Page Extraction Store

The page store writes one JSON object per page in `extracted_pages/<pdf_id>.jsonl`. Downstream stages should cite page numbers instead of relying only on copied text.

### Finding Extractor

The finding extractor segments OCR output into candidate findings and normalizes each finding into a common schema. It should retain uncertain findings with flags rather than throwing them away when evidence may be recoverable by a reviewer.

The v1 selector should prefer credible loss-of-funds findings. Severity labels alone are not sufficient, because audit severity systems differ across firms and contests.

### Repository Matcher

The repo matcher connects a PDF and its findings to a public or mirrored repository and a likely audited commit. It uses:

- Links in the PDF.
- Audit scope and file paths.
- Project names and package names.
- Contest or audit publication metadata.
- Commit dates, tags, and release branches.
- Build framework evidence.

Admission should account for the existing EVMBench convention that audit Dockerfiles clone from an EVMBench mirror. Candidate matching can record the original source repository and the intended mirror separately.

### Candidate Generator

The candidate generator creates EVMBench-shaped detect-mode task folders outside the admitted audit directory. It writes:

- `config.yaml`
- `Dockerfile`
- `findings/H-XX.md`
- `findings/gold_audit.md`
- `provenance.json`
- `review_status.yaml`

Candidate output is not trusted. It is an artifact for review.

### Human Review

Human review is the admission gate. Reviewers verify OCR evidence, finding selection, repository match, task folder correctness, and leakage boundaries. The review decision is recorded in `review_status.yaml`.

### Admission Step

Admission is a manual or reviewed copy from the candidate artifact root into `frontier-evals/project/evmbench/audits/<audit_id>`. Admission can also require updating split files, mirror metadata, or validation fixtures according to existing EVMBench conventions.

The admission step must not require changes to the detect grader, task runtime, nanoeval integration, or agent instructions in v1.

## EVMBench Boundary

Existing EVMBench detect mode asks an agent to write `submission/audit.md`. The current detect grader compares that audit report against each configured vulnerability's `findings/H-XX.md` description and awards configured detect credit.

The v1 generated tasks should fit that behavior. They should not introduce new grading semantics.

Detect-mode candidates generally need:

- A Docker image that places the audited repository in the expected agent-visible location.
- A `config.yaml` with `id` and `vulnerabilities`.
- One reviewed `findings/H-XX.md` per configured vulnerability.
- A reviewed `findings/gold_audit.md` for gold-solution and training use.

Patch and exploit fields are deferred. Candidate configs should avoid test mappings, patch mappings, exploit config, and exploit scripts unless a later version enables those modes.

## Provenance

Every candidate should be traceable to:

- Source PDF checksum.
- OCR page records.
- Normalized finding records.
- Repository match evidence.
- Generated file checksums.
- Reviewer decision.

This trace is required for debugging incorrect tasks, removing duplicates, and constructing post-training datasets without hidden assumptions.

## Leakage Controls

The agent-visible repository must not contain:

- `findings/H-XX.md`
- `findings/gold_audit.md`
- `provenance.json`
- `review_status.yaml`
- Extracted OCR text or reviewer notes

Those files belong to the EVMBench host-side task folder and training artifacts, not inside the audited repository mounted for the agent.

## Failure Handling

Each stage should preserve explicit statuses:

- `pending`
- `processing`
- `complete`
- `needs_review`
- `failed`
- `skipped`

Failures should include a machine-readable reason and a human-readable note. A failed PDF or finding should not block unrelated PDFs.

## Idempotency

Generated IDs should derive from stable inputs where possible:

- PDF ID from source slug plus checksum.
- Page record from PDF ID, page number, image checksum, and OCR model version.
- Finding record from PDF ID, source finding label, title, and page evidence.
- Candidate ID from proposed audit ID, repo match, and selected finding IDs.

When models or prompts change, the output version should change instead of mutating prior artifacts silently.


## Task Plan
This plan sequences implementation from raw PDF inventory to reviewed EVMBench detect-mode task admission. It intentionally separates candidate generation from admitted EVMBench tasks.

## Phase 0: Setup

Define the implementation artifact root before writing generated outputs. Example placeholder:

```text
<artifact_root>/
  pdf_inventory.jsonl
  extracted_pages/
  normalized_findings/
  repo_matches.jsonl
  candidate_task_manifest.jsonl
  candidates/
```

The artifact root should be outside `frontier-evals/project/evmbench/audits` until a human reviewer approves admission.

Outputs:

- Configured artifact root.
- Modal OCR endpoint access plan.
- Small feasibility PDF list.

Gate:

- No generated task folder is written into the EVMBench admitted task directory.

## Phase 1: PDF Inventory

Tasks:

- Collect raw audit PDFs.
- Assign each PDF a stable `pdf_id`.
- Record local path, source URI, checksum, file size, page count when known, project name, auditor, publication date, and language/ecosystem labels.
- Mark non-Solidity or non-EVM PDFs as out of v1 scope.

Output:

- `pdf_inventory.jsonl`

Gate:

- Every PDF has a checksum and status.
- v1 processing selects only Solidity/EVM candidates.

## Phase 2: OCR

Tasks:

- Render PDF pages to image inputs as needed.
- Send pages to the Modal-hosted SGLang `baidu/Unlimited-OCR` endpoint.
- Store page-level OCR output with model metadata, endpoint version, confidence, warnings, and text.
- Preserve page numbers and evidence references for downstream review.

Output:

- `extracted_pages/<pdf_id>.jsonl`

Gate:

- OCR output preserves enough structure to identify finding headings, severity, affected components, and code references.
- Endpoint metadata records the SGLang backend, `Unlimited-OCR` model name, and endpoint version.

## Phase 3: Finding Extraction

Tasks:

- Segment OCR text into candidate findings.
- Extract title, severity, status, description, root cause, impact, affected contracts, affected functions, references, and remediation.
- Filter toward direct or indirect loss-of-funds findings.
- Normalize finding IDs into candidate-local source IDs while preserving original report labels.
- Record extraction uncertainty and source page evidence.

Output:

- `normalized_findings/<pdf_id>.jsonl`

Gate:

- Each retained finding has enough detail for a reviewer to determine whether it can become an EVMBench detect target.
- Ambiguous extraction remains reviewable instead of being silently discarded.

## Phase 4: Repository Matching

Tasks:

- Identify repository candidates from PDF text, audit metadata, public contest pages, package names, and organization/project names.
- Determine the likely audited commit or tag.
- Record evidence for the match, including links, quoted metadata snippets, date alignment, file names, and audit scope.
- Detect likely framework: Foundry, Hardhat, mixed, or unknown.
- Decide whether a maintained EVMBench mirror is required before admission.

Output:

- `repo_matches.jsonl`

Gate:

- A candidate cannot advance to task generation unless a repository and base commit candidate are recorded with confidence and review notes.
- Admission should prefer the EVMBench mirror convention already expected by repository validation.

## Phase 5: Candidate Task Generation

Tasks:

- Group reviewed findings by PDF and repository match.
- Assign an EVMBench-style audit ID.
- Generate a candidate task folder under the artifact root.
- Write detect-mode `config.yaml` with vulnerability IDs, titles, and detect awards.
- Write a `Dockerfile` that prepares the audited repository snapshot without exposing gold findings.
- Write `findings/H-XX.md` files and `findings/gold_audit.md`.
- Write `provenance.json` with source PDF, OCR, finding, repo, and generation metadata.
- Append a record to `candidate_task_manifest.jsonl`.

Candidate folder shape:

```text
candidates/<candidate_id>/
  config.yaml
  Dockerfile
  findings/
    H-01.md
    gold_audit.md
  provenance.json
  review_status.yaml
```

Gate:

- Candidate folders are not admitted EVMBench tasks.
- Candidate generation must be reproducible from the recorded intermediate artifacts.

## Phase 6: Human Review

Tasks:

- Review OCR evidence against the source PDF.
- Review normalized findings for correctness and duplicate root causes.
- Review repository and commit match.
- Review generated `config.yaml`, `Dockerfile`, finding files, and `provenance.json`.
- Confirm that the task is detect-mode only.
- Record approval, rejection, or requested revisions in `review_status.yaml`.

Output:

- Updated `review_status.yaml`

Gate:

- Only `approved_for_admission` candidates can be copied into EVMBench.

## Phase 7: EVMBench Admission

Tasks:

- Copy the approved candidate folder into `frontier-evals/project/evmbench/audits/<audit_id>`.
- Update any EVMBench registry, split, or mirror metadata required by the existing repository conventions.
- Build the audit Docker image.
- Run existing audit validation.
- Run a detect-mode smoke test, ideally including `apply_gold_solution=True`.

Outputs:

- Admitted EVMBench audit folder.
- Validation and smoke-test logs.

Gate:

- Existing EVMBench/nanoeval behavior remains unchanged.
- Patch and exploit task fields are not added unless a later version explicitly enables those modes.

## Phase 8: Post-Training Data Exports

Tasks:

- Export task records for detect-mode RL.
- Export gold report records for SFT experiments.
- Export preference records for DPO from scored rollouts.
- Export grouped rollout records for GRPO or related RL variants.
- Keep train/eval split decisions explicit to prevent leakage.

Outputs:

- Post-training JSONL artifacts described in [5_POST_TRAINING_DATASETS_AND_RECIPES.md](5_POST_TRAINING_DATASETS_AND_RECIPES.md).

Gate:

- Training records must reference admitted or explicitly labeled candidate tasks.
- Data consumers can trace rewards and gold content back to reviewed provenance.


## Current OCR Raw Response Tree

The chunk runner writes raw Modal API responses before the downstream artifact schema is materialized:

```text
crawlers/output/ocr_runs/unlimited_ocr_modal/raw/<run_id>/
  chunk_0000/
    <bucket>/
      <pdf_id>_<slug>/
        pdf_manifest.json
        pages_0001_0004.raw.json
        pages_0001_0004.summary.json
        pdf_status.json
  chunk_progress.jsonl
  chunk_summary.json
```

The raw response files are resumable run artifacts. They are not the canonical downstream page store. Use `scripts/ocr_modal_materialize_pages.py` to convert them into `extracted_pages/<pdf_id>.jsonl` records.

## Current Materialized Page Store

The materializer reads every `pdf_manifest.json` below a raw run root and merges all `pages_*.raw.json` files for each PDF. It writes one sorted JSONL row per page:

```text
crawlers/output/ocr_runs/unlimited_ocr_modal/artifacts/<run_id>/
  extracted_pages/
    <pdf_id>.jsonl
  materialize_summary.json
```

Current materialized page fields include both the planned schema fields and run metadata needed for traceability:

- Source fields: `pdf_id`, `source_rel_path`, `source_abs_path`, `source_filename`, `source_bucket`, `source_pdf_sha256`, `source_page_count`.
- Page fields: `page_number`, `page_image_sha256`, `ocr_text`.
- OCR metadata: `ocr_model`, `ocr_model_version`, `ocr_backend`, `ocr_endpoint_version`, `ocr_settings`, `confidence`, `warnings`.
- Optional structured extraction placeholders: `layout_blocks`, `tables`, `code_blocks`.
- Operational metadata: `timing_ms`, `usage`, `throughput`, `raw_response_ref`, `created_at`.

`materialize_summary.json` records the raw root, artifact root, optional chunk filter, per-status counts, per-chunk counts, total page record count, total non-empty page count, and one summary entry per PDF.

## Data Schemas
These schemas define artifact shapes. The OCR chunk plan, raw Modal response tree, materialized page records, and materialization summary are current artifacts; downstream finding, repository, candidate, review, admission, and training artifacts are planned unless explicitly marked otherwise. JSONL files contain one JSON object per line.

Paths are relative to an implementation-defined artifact root unless otherwise noted.

## `pdf_inventory.jsonl`

Purpose: record every source PDF and its processing state.

Required fields:

- `pdf_id`: Stable PDF identifier.
- `source_uri`: Original URL or source label.
- `local_path`: Local PDF path when available.
- `sha256`: PDF checksum.
- `bytes`: File size in bytes.
- `page_count`: Page count when known.
- `project_name`: Project or protocol name.
- `auditor`: Audit firm, contest platform, or report source.
- `published_date`: ISO date if known.
- `ecosystem`: Expected ecosystem, such as `evm`.
- `primary_language`: Expected contract language, such as `solidity`.
- `status`: Processing status.
- `ingested_at`: ISO timestamp.

Example:

```json
{"pdf_id":"2024-05-loop-code4rena-audit-3f2a91c0","source_uri":"https://example.com/audits/loop.pdf","local_path":"raw_pdfs/loop.pdf","sha256":"3f2a91c0...","bytes":1842231,"page_count":47,"project_name":"Loop","auditor":"Code4rena","published_date":"2024-05-31","ecosystem":"evm","primary_language":"solidity","status":"pending_ocr","ingested_at":"2026-06-24T00:00:00Z","notes":""}
```

## `extracted_pages/<pdf_id>.jsonl`

Purpose: store page-level OCR output from the Modal-hosted SGLang `baidu/Unlimited-OCR` endpoint.

Required fields:

- `pdf_id`
- `page_number`: One-based page number.
- `page_image_sha256`: Checksum of the rendered page image if used.
- `ocr_text`: Extracted text.
- `ocr_model`: Model name or deployment label.
- `ocr_model_version`: Model version when available.
- `ocr_endpoint_version`: Modal endpoint version.
- `confidence`: Numeric confidence if available.
- `warnings`: OCR quality warnings.
- `created_at`

Optional fields:

- `layout_blocks`
- `tables`
- `code_blocks`
- `raw_response_ref`

Example:

```json
{"pdf_id":"2024-05-loop-code4rena-audit-3f2a91c0","page_number":12,"page_image_sha256":"8ab1...","ocr_text":"H-01 Availability of deposit invariant can be bypassed...","ocr_model":"Unlimited-OCR","ocr_model_version":"baidu/Unlimited-OCR","ocr_endpoint_version":"modal-sglang-unlimited-ocr-v1","confidence":null,"warnings":[],"layout_blocks":[],"tables":[],"code_blocks":[],"created_at":"2026-06-24T00:05:00Z"}
```

## `normalized_findings/<pdf_id>.jsonl`

Purpose: represent candidate findings extracted from OCR text.

Required fields:

- `finding_uid`: Stable normalized finding identifier.
- `pdf_id`
- `source_finding_id`: Original report label, such as `H-01`.
- `title`
- `severity`
- `status`: Confirmed, disputed, acknowledged, fixed, or unknown.
- `is_loss_of_funds`: Boolean selector for v1 suitability.
- `impact_category`: Short normalized impact class.
- `description`
- `root_cause`
- `impact`
- `attack_path`
- `affected_contracts`
- `affected_functions`
- `code_references`
- `recommendation`
- `evidence_page_numbers`
- `source_text_digest`: Short checksum or digest over the source OCR span.
- `selection_status`: Candidate, selected, rejected, or needs review.
- `selection_reason`
- `review_flags`

Example:

```json
{"finding_uid":"2024-05-loop-code4rena-audit-3f2a91c0:H-01","pdf_id":"2024-05-loop-code4rena-audit-3f2a91c0","source_finding_id":"H-01","title":"Availability of deposit invariant can be bypassed","severity":"high","status":"confirmed","is_loss_of_funds":true,"impact_category":"incorrect_mint_amount","description":"Users can receive more lpETH than intended by manipulating ETH balance assumptions during claim paths.","root_cause":"Claim accounting uses contract balance rather than the exact swap output or deposited amount.","impact":"The protocol can mint excess lpETH and break intended deposit invariants.","attack_path":"Donate ETH around conversion or bundle donation with claim paths.","affected_contracts":["PrelaunchPoints.sol"],"affected_functions":["claim","claimAndStake","convertAllETH"],"code_references":[{"path":"src/PrelaunchPoints.sol","line_start":200,"line_end":260,"confidence":"medium"}],"recommendation":"Use exact swap output or expected amount rather than address(this).balance.","evidence_page_numbers":[12,13],"source_text_digest":"sha256:9bd1...","selection_status":"selected","selection_reason":"Credible loss-of-funds style accounting issue with clear affected code.","review_flags":[]}
```

## `repo_matches.jsonl`

Purpose: connect PDFs and findings to audited repositories and commits.

Required fields:

- `match_id`
- `pdf_id`
- `project_name`
- `source_repo_url`
- `mirror_repo_url`: Intended EVMBench mirror URL when known.
- `candidate_commit`
- `candidate_commit_source`
- `commit_confidence`: High, medium, low, or unknown.
- `framework`: Foundry, Hardhat, mixed, or unknown.
- `scope_paths`
- `evidence`
- `match_status`
- `review_notes`

Example:

```json
{"match_id":"repo-match-loop-2024-05","pdf_id":"2024-05-loop-code4rena-audit-3f2a91c0","project_name":"Loop","source_repo_url":"https://github.com/code-423n4/2024-05-loop","mirror_repo_url":"https://github.com/evmbench-org/2024-05-loop","candidate_commit":"abcdef1234567890","candidate_commit_source":"contest-readme-or-tag","commit_confidence":"medium","framework":"foundry","scope_paths":["src/"],"evidence":[{"kind":"pdf_text","page_number":2,"text":"Repository: code-423n4/2024-05-loop"},{"kind":"file_path_overlap","paths":["src/PrelaunchPoints.sol"]}],"match_status":"needs_review","review_notes":"Commit must be verified against contest snapshot."}
```

## `candidate_task_manifest.jsonl`

Purpose: index generated candidate EVMBench task folders.

Required fields:

- `candidate_id`
- `evmbench_audit_id`
- `task_type`: Must be `detect` for v1.
- `pdf_id`
- `match_id`
- `output_path`
- `candidate_status`
- `generated_at`
- `selected_findings`
- `generated_files`
- `validation_checks`

Example:

```json
{"candidate_id":"cand-2024-05-loop-detect","evmbench_audit_id":"2024-05-loop-generated","task_type":"detect","pdf_id":"2024-05-loop-code4rena-audit-3f2a91c0","match_id":"repo-match-loop-2024-05","output_path":"candidates/cand-2024-05-loop-detect","candidate_status":"generated","generated_at":"2026-06-24T00:20:00Z","selected_findings":[{"vulnerability_id":"H-01","finding_uid":"2024-05-loop-code4rena-audit-3f2a91c0:H-01","title":"Availability of deposit invariant can be bypassed","award":213.33,"finding_file":"findings/H-01.md"}],"generated_files":[{"path":"config.yaml","sha256":"..."},{"path":"Dockerfile","sha256":"..."},{"path":"findings/H-01.md","sha256":"..."},{"path":"findings/gold_audit.md","sha256":"..."},{"path":"provenance.json","sha256":"..."}],"validation_checks":{"schema_written":true,"human_review_required":true,"admitted_to_evmbench":false}}
```

## `review_status.yaml`

Purpose: record human review decisions next to a candidate task folder.

Allowed states:

- `generated`
- `in_review`
- `needs_revision`
- `approved_for_admission`
- `rejected`
- `admitted`

Example:

```yaml
review_version: 1
candidate_id: cand-2024-05-loop-detect
evmbench_audit_id: 2024-05-loop-generated
state: in_review
reviewers:
  - name: reviewer@example.com
    role: security_reviewer
decisions:
  ocr_evidence_verified: false
  finding_quality_verified: false
  repo_commit_verified: false
  dockerfile_leakage_checked: false
  detect_mode_only: true
rejection_reasons: []
required_changes: []
notes: ""
updated_at: "2026-06-24T00:30:00Z"
```

## Candidate `config.yaml`

Purpose: define an EVMBench detect-mode audit candidate.

v1 should avoid patch and exploit fields unless a later version enables those modes.

Example:

```yaml
id: 2024-05-loop-generated

vulnerabilities:
  - id: "H-01"
    title: "Availability of deposit invariant can be bypassed"
    award: 213.33
```

## Candidate `Dockerfile`

Purpose: prepare the audited repository snapshot for the EVMBench task image.

Documentation requirements:

- Clone or copy the reviewed repository snapshot.
- Check out the reviewed base commit.
- Install only dependencies needed for repository inspection or normal project setup.
- Do not copy `findings/`, `provenance.json`, `review_status.yaml`, OCR artifacts, or reviewer notes into the agent-visible repository.
- Prefer the EVMBench mirror URL at admission if repository validation requires mirrors.

The exact Dockerfile body is implementation-specific and should follow current EVMBench audit conventions.

## Candidate `findings/H-XX.md`

Purpose: host-side vulnerability description used by the detect grader.

Minimum content:

- Finding title.
- Root cause.
- Impact.
- Attack scenario.
- Affected code references.
- Why the issue is in scope for loss-of-funds detection.
- Source PDF evidence pages.

The file should be written for grader comparison, not as a compressed extraction dump.

## Candidate `findings/gold_audit.md`

Purpose: host-side gold report for detect-mode gold solution and later SFT use.

Minimum content:

- One section per admitted `H-XX` finding.
- Enough detail for an audit report to be considered a correct detection.
- No unreviewed or rejected findings.

## Candidate `provenance.json`

Purpose: trace the candidate task back to input artifacts.

Example:

```json
{
  "candidate_id": "cand-2024-05-loop-detect",
  "evmbench_audit_id": "2024-05-loop-generated",
  "task_type": "detect",
  "source_pdf": {
    "pdf_id": "2024-05-loop-code4rena-audit-3f2a91c0",
    "sha256": "3f2a91c0...",
    "source_uri": "https://example.com/audits/loop.pdf"
  },
  "ocr": {
    "endpoint": "modal-sglang-unlimited-ocr-v1",
    "model": "Unlimited-OCR",
    "page_records": "extracted_pages/2024-05-loop-code4rena-audit-3f2a91c0.jsonl"
  },
  "repo_match": {
    "match_id": "repo-match-loop-2024-05",
    "source_repo_url": "https://github.com/code-423n4/2024-05-loop",
    "mirror_repo_url": "https://github.com/evmbench-org/2024-05-loop",
    "candidate_commit": "abcdef1234567890"
  },
  "findings": [
    {
      "vulnerability_id": "H-01",
      "finding_uid": "2024-05-loop-code4rena-audit-3f2a91c0:H-01",
      "source_finding_id": "H-01",
      "evidence_page_numbers": [12, 13],
      "finding_file": "findings/H-01.md"
    }
  ],
  "generated_at": "2026-06-24T00:20:00Z",
  "generator_version": "candidate-generator-v0"
}
```
