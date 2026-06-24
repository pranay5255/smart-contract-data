# Architecture

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

OCR is performed through the Modal-hosted SGLang `baidu/Unlimited-OCR` endpoint documented in [OCR_MODAL_SGLANG.md](OCR_MODAL_SGLANG.md). The endpoint contract should preserve:

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

