# Overview And Current State

This is the entry point for the audit-PDF-to-EVMBench experiment. It explains what exists now, what remains future work, and how to navigate the numbered documentation set.

## Current Objects And Artifacts

- The documentation has been consolidated into six numbered files in this directory.
- The Modal SGLang Unlimited-OCR service is documented and intended to be served from `modal_apps/unlimited_ocr_sglang.py`.
- OCR planning and execution tooling exists for chunked overnight runs: `scripts/ocr_pdf_make_chunks.py` and `scripts/ocr_modal_run_chunk.py`.
- A current OCR chunk plan exists under `crawlers/output/ocr_runs/unlimited_ocr_modal/audit_pdf_chunks_target2500_20260624`.
- A raw-response materializer exists at `scripts/ocr_modal_materialize_pages.py` with coverage in `tests/test_ocr_modal_materialize_pages.py`.
- Current raw OCR responses live under `crawlers/output/ocr_runs/unlimited_ocr_modal/raw/<run_id>/` when chunk runs are executed.
- Current materialized OCR artifacts should live under `crawlers/output/ocr_runs/unlimited_ocr_modal/artifacts/<run_id>/`, including `extracted_pages/<pdf_id>.jsonl` and `materialize_summary.json`.
- No generated candidate task folders, EVMBench registry/split updates, admitted audit folders, or post-training exports are current artifacts yet.

## Future Experiment Work

- Normalize findings from materialized OCR pages.
- Match findings to repositories and audited commits.
- Generate candidate detect-mode task folders outside the admitted EVMBench audit directory.
- Run human review and admission checks before copying anything into `frontier-evals/project/evmbench/audits`.
- Build post-training records only after candidate/admitted provenance and split policy are explicit.

## Numbered Document Map

1. `1_OVERVIEW_AND_CURRENT_STATE.md`: product boundary, current status, roadmap, and open decisions.
2. `2_PIPELINE_AND_ARTIFACTS.md`: architecture, pipeline stages, artifact roots, schemas, provenance, failure handling, and idempotency.
3. `3_OCR_RUNBOOK.md`: Modal OCR service, chunk planning, chunk execution, resume behavior, materialization, and smoke tests.
4. `4_REVIEW_AND_ADMISSION.md`: human review, rejection reasons, candidate quality bar, leakage checks, and EVMBench admission.
5. `5_POST_TRAINING_DATASETS_AND_RECIPES.md`: post-training source inventory and RL/SFT/DPO/GRPO record shapes.
6. `6_LWM_SIMULATOR_TRAINING.md`: future-facing language-world-model simulator training math and evals.

## Recommended Reading Order

1. Read this overview to understand the current boundary.
2. Read `3_OCR_RUNBOOK.md` before running OCR or materialization jobs.
3. Read `2_PIPELINE_AND_ARTIFACTS.md` before implementing finding extraction or task generation.
4. Read `4_REVIEW_AND_ADMISSION.md` before admitting any generated task.
5. Read `5_POST_TRAINING_DATASETS_AND_RECIPES.md` only after candidate/admitted task artifacts exist.
6. Read `6_LWM_SIMULATOR_TRAINING.md` when planning simulator-style post-training beyond audit-report generation.

## Product Requirements
### Product Goal

Build a reliable documentation-backed pipeline that converts raw Solidity/EVM audit PDFs into human-reviewed EVMBench detect-mode tasks. The pipeline should create candidate task artifacts first, then admit only reviewed candidates into `frontier-evals/project/evmbench/audits`.

The first version should help dataset builders expand EVMBench task coverage without changing EVMBench runtime behavior.

### Users

- Dataset builders who collect audit PDFs and prepare benchmark tasks.
- Human reviewers who decide whether a generated candidate is good enough for EVMBench.
- RL and post-training researchers who need traceable detect-mode task records.
- EVMBench maintainers who need generated tasks to follow existing task structure and validation expectations.

### Problem

Audit PDFs contain high-value vulnerability reports, but they are not directly usable as EVMBench tasks. The useful information is split across PDF layout, prose, code references, project metadata, repository history, and audit scope. Directly copying extracted text into EVMBench would create low-quality tasks, duplicate issues, wrong repository snapshots, and possible benchmark leakage.

The pipeline needs to separate mechanical extraction from human task admission.

### Scope

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

### Non-Goals

- Generate patch-mode tasks.
- Generate exploit-mode tasks.
- Modify the detect grader or judge prompt.
- Modify nanoeval, Alcatraz, agent launch, or existing EVMBench runtime behavior.
- Automatically copy generated candidates into `frontier-evals/project/evmbench/audits`.
- Treat OCR output as trusted without review.
- Replace human review with automated trust in OCR output.

### Functional Requirements

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

### Quality Requirements

- Candidate findings must describe credible direct or indirect loss-of-funds vulnerabilities.
- The repository and commit must match the audited code closely enough for an agent to inspect the relevant vulnerable code.
- Candidate `Dockerfile` behavior must not expose gold findings or review notes inside the agent-visible audit repository.
- Candidate `config.yaml` must be compatible with existing EVMBench detect-mode expectations.
- Every admitted vulnerability must have a corresponding `findings/H-XX.md` file.
- `findings/gold_audit.md` must describe all admitted findings without adding unreviewed vulnerabilities.
- Reviewers must be able to reject candidates with explicit reasons instead of losing the decision trail.

### Success Criteria

The feasibility batch succeeds when:

- A small set of PDFs can be inventoried and OCRed.
- OCR output is sufficient for a reviewer to recover finding titles, severity, impact, and code references.
- At least one candidate detect-mode task folder can be generated without touching the admitted EVMBench audit directory.
- Reviewers can approve, reject, or request revisions using `review_status.yaml`.
- At least one approved candidate can be manually admitted and pass the existing EVMBench audit validation expectations for detect mode.
- Post-training export schemas are clear enough to implement without redefining task identity, reward fields, or provenance.

### Risks

- OCR can miss code references, tables, or finding boundaries.
- Audit PDFs can refer to private, renamed, forked, or unavailable repositories.
- The audited commit may differ from the public repository state.
- Extracted findings may not be true loss-of-funds issues.
- Multiple findings can describe the same root cause, producing duplicate benchmark entries.
- Gold finding text can leak into the agent-visible environment if candidate Dockerfiles are wrong.
- Automatic generation can produce tasks that look valid structurally but are not useful benchmark items.

### Milestones

#### Milestone 0: Documentation

Maintain this documentation package and keep it aligned with the OCR service, chunk runner, chunk planner, and materializer. No generated task files have been admitted.

#### Milestone 1: Feasibility Batch

Process a small, manually selected set of Solidity/EVM PDFs. The goal is to validate artifact shapes, OCR quality, finding normalization, repo matching, and review workflow.

#### Milestone 2: Candidate Generation

Generate candidate task folders from normalized findings and repo matches. Candidates remain outside `frontier-evals/project/evmbench/audits`.

#### Milestone 3: Review Loop

Use `review_status.yaml` to record reviewer decisions, rejection reasons, required fixes, and final approval state.

#### Milestone 4: Manual Admission

Copy only approved candidates into the EVMBench audit directory. Run existing validation and detect-mode smoke checks.

#### Milestone 5: Post-Training Exports

Export task and rollout data using the documented RL, SFT, DPO, and GRPO planning shapes.


## Current Status

Status: design specification plus Modal SGLang OCR service, OCR chunk planning/run tooling, and raw-response materialization workflow.

The intended first implementation milestone is a small feasibility batch. The batch should prove that the pipeline can ingest a few audit PDFs, OCR them, extract loss-of-funds findings, match each finding to a repository and base commit, generate candidate detect-mode task folders, and route those candidates through human review.

The first admitted task type is detect-mode only. Patch and exploit tasks stay out of scope until the detect-mode extraction and review process is reliable.


## Open Design Questions
These questions remain unresolved unless a later implementation or review decision explicitly answers them.

These questions should stay visible during implementation. They are grouped by area so assumptions are explicit.

### Task Admission

- What exact validation commands must pass before `approved_for_admission` becomes `admitted`?
- Should the first feasibility batch use only one vulnerability per task, or allow multi-finding detect tasks from the start?
- How should detect awards be assigned when the source audit has no contest award amount?
- What naming convention should generated `evmbench_audit_id` values use to avoid collisions with hand-authored tasks?
- Which EVMBench metadata files must be updated during admission beyond the audit folder itself?

### OCR

- What prompt, mode, and page-range settings should the SGLang Unlimited-OCR endpoint use for the feasibility batch?
- Should OCR run page-by-page, by page range, or with multi-page context?
- What confidence or quality signals are reliable enough to gate extraction?
- How should tables, footnotes, code snippets, and two-column layouts be represented?
- Should rendered page images be retained long term, or can checksums plus OCR records be enough?

### Finding Selection

- What threshold separates direct or indirect loss-of-funds findings from out-of-scope findings?
- Should medium-severity findings be selected when they have clear asset-loss impact?
- How should duplicate findings across multiple auditors or contest submissions be merged?
- Should disputed findings be allowed if the technical issue is still credible?
- How much remediation detail belongs in `findings/H-XX.md` for grader comparison?

### Grading

- Is the existing detect judge prompt sufficient for generated PDF-derived findings?
- Do generated findings need stricter formatting to improve judge reliability?
- Should `findings/gold_audit.md` be generated from selected `H-XX` files or independently reviewed?
- Should detect awards be normalized across tasks for RL, or preserve source award values?
- How should partial detections be analyzed if the current grader remains binary per vulnerability?

### Repository Matching

- Should candidate generation require an EVMBench mirror before review, or only before admission?
- How should the pipeline handle audit reports that reference private repos later made public?
- What is the fallback when the exact audited commit is not known but file paths match a release tag?
- Should dependency lockfiles be part of the match confidence decision?
- How should monorepos and multi-package scopes be represented in `repo_matches.jsonl`?

### Review Workflow

- Who can mark a candidate as `approved_for_admission`?
- Is one reviewer enough, or should security and infrastructure review be separate gates?
- Should review happen in plain YAML, a small web UI, or pull request comments?
- How should reviewer edits to generated findings be tracked against original extraction output?
- Should rejected candidates remain in the artifact root indefinitely for analysis?

### Training Recipes

- Which tasks are held out permanently from SFT and preference training?
- Should candidate-only tasks be usable for exploratory RL before EVMBench admission?
- What rollout metadata is required to reproduce rewards?
- How should infrastructure failures be excluded from preference pairs?
- Should GRPO groups use binary score, award-weighted score, or another reward field?

### Security and Leakage

- What automated checks should verify that gold findings are not copied into Docker images?
- Should provenance files include full OCR snippets, or only references and digests?
- How should PDFs with restrictive licensing or unclear redistribution rights be handled?
- What redaction policy is needed for private source paths, user names, or audit platform metadata?
- Should generated candidate artifacts be treated as sensitive until admitted?
