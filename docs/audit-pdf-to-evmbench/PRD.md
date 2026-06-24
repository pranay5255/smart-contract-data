# PRD

## Product Goal

Build a reliable documentation-backed pipeline that converts raw Solidity/EVM audit PDFs into human-reviewed EVMBench detect-mode tasks. The pipeline should create candidate task artifacts first, then admit only reviewed candidates into `frontier-evals/project/evmbench/audits`.

The first version should help dataset builders expand EVMBench task coverage without changing EVMBench runtime behavior.

## Users

- Dataset builders who collect audit PDFs and prepare benchmark tasks.
- Human reviewers who decide whether a generated candidate is good enough for EVMBench.
- RL and post-training researchers who need traceable detect-mode task records.
- EVMBench maintainers who need generated tasks to follow existing task structure and validation expectations.

## Problem

Audit PDFs contain high-value vulnerability reports, but they are not directly usable as EVMBench tasks. The useful information is split across PDF layout, prose, code references, project metadata, repository history, and audit scope. Directly copying extracted text into EVMBench would create low-quality tasks, duplicate issues, wrong repository snapshots, and possible benchmark leakage.

The pipeline needs to separate mechanical extraction from human task admission.

## Scope

v1 includes:

- Solidity/EVM audit PDF inventory.
- PDF page OCR through a Modal-hosted SGLang `baidu/Unlimited-OCR` endpoint.
- Finding extraction from OCR text and page evidence.
- Normalization of candidate loss-of-funds findings.
- Repository and base-commit matching.
- Candidate EVMBench detect-mode task folder generation.
- Human review before admission.
- Post-training data shape definitions for later RL, SFT, DPO, and GRPO work.

v1 explicitly targets detect mode only. A v1 candidate may include only the files needed to evaluate whether an agent can produce `submission/audit.md` that detects known vulnerabilities.

## Non-Goals

- Generate patch-mode tasks.
- Generate exploit-mode tasks.
- Modify the detect grader or judge prompt.
- Modify nanoeval, Alcatraz, agent launch, or existing EVMBench runtime behavior.
- Automatically copy generated candidates into `frontier-evals/project/evmbench/audits`.
- Treat OCR output as trusted without review.
- Replace human review with automated trust in OCR output.

## Functional Requirements

1. The system records every input PDF in `pdf_inventory.jsonl` with stable identity, source, checksum, metadata, and processing status.
2. The OCR stage emits page-level records under `extracted_pages/<pdf_id>.jsonl`.
3. The finding extraction stage emits normalized candidate findings under `normalized_findings/<pdf_id>.jsonl`.
4. The repo matching stage emits reviewed or reviewable repository candidates in `repo_matches.jsonl`.
5. The candidate generation stage emits `candidate_task_manifest.jsonl` and one candidate task folder per proposed EVMBench task.
6. Candidate task folders include `config.yaml`, `Dockerfile`, finding files, `findings/gold_audit.md`, and `provenance.json`.
7. Generated task folders are candidate artifacts only.
8. Human review is required before admission into `frontier-evals/project/evmbench/audits`.
9. Review state is recorded in `review_status.yaml` next to each candidate.
10. Accepted candidates keep enough provenance to trace each EVMBench vulnerability back to PDF pages, OCR output, normalized finding records, and repo matching evidence.

## Quality Requirements

- Candidate findings must describe credible direct or indirect loss-of-funds vulnerabilities.
- The repository and commit must match the audited code closely enough for an agent to inspect the relevant vulnerable code.
- Candidate `Dockerfile` behavior must not expose gold findings or review notes inside the agent-visible audit repository.
- Candidate `config.yaml` must be compatible with existing EVMBench detect-mode expectations.
- Every admitted vulnerability must have a corresponding `findings/H-XX.md` file.
- `findings/gold_audit.md` must describe all admitted findings without adding unreviewed vulnerabilities.
- Reviewers must be able to reject candidates with explicit reasons instead of losing the decision trail.

## Success Criteria

The feasibility batch succeeds when:

- A small set of PDFs can be inventoried and OCRed.
- OCR output is sufficient for a reviewer to recover finding titles, severity, impact, and code references.
- At least one candidate detect-mode task folder can be generated without touching the admitted EVMBench audit directory.
- Reviewers can approve, reject, or request revisions using `review_status.yaml`.
- At least one approved candidate can be manually admitted and pass the existing EVMBench audit validation expectations for detect mode.
- Post-training export schemas are clear enough to implement without redefining task identity, reward fields, or provenance.

## Risks

- OCR can miss code references, tables, or finding boundaries.
- Audit PDFs can refer to private, renamed, forked, or unavailable repositories.
- The audited commit may differ from the public repository state.
- Extracted findings may not be true loss-of-funds issues.
- Multiple findings can describe the same root cause, producing duplicate benchmark entries.
- Gold finding text can leak into the agent-visible environment if candidate Dockerfiles are wrong.
- Automatic generation can produce tasks that look valid structurally but are not useful benchmark items.

## Milestones

### Milestone 0: Documentation

Create this documentation package. No implementation code or generated task files are created.

### Milestone 1: Feasibility Batch

Process a small, manually selected set of Solidity/EVM PDFs. The goal is to validate artifact shapes, OCR quality, finding normalization, repo matching, and review workflow.

### Milestone 2: Candidate Generation

Generate candidate task folders from normalized findings and repo matches. Candidates remain outside `frontier-evals/project/evmbench/audits`.

### Milestone 3: Review Loop

Use `review_status.yaml` to record reviewer decisions, rejection reasons, required fixes, and final approval state.

### Milestone 4: Manual Admission

Copy only approved candidates into the EVMBench audit directory. Run existing validation and detect-mode smoke checks.

### Milestone 5: Post-Training Exports

Export task and rollout data using the documented RL, SFT, DPO, and GRPO planning shapes.

