# Task Plan

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

- Post-training JSONL artifacts described in [POST_TRAINING_RECIPES.md](POST_TRAINING_RECIPES.md).

Gate:

- Training records must reference admitted or explicitly labeled candidate tasks.
- Data consumers can trace rewards and gold content back to reviewed provenance.

