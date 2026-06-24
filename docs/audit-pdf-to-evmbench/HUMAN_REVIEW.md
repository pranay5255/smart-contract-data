# Human Review

Human review is required before any generated candidate is copied into `frontier-evals/project/evmbench/audits`.

The reviewer is not just checking formatting. The reviewer decides whether the candidate is a valid benchmark task.

## Review Principles

- Treat OCR, extraction, and repo matching as untrusted until verified.
- Admit only Solidity/EVM detect-mode tasks in v1.
- Prefer fewer high-quality tasks over broad automatic coverage.
- Preserve explicit rejection reasons.
- Do not admit a task if gold findings or review artifacts are visible to the agent.
- Do not admit patch or exploit task material in v1.

## Review States

- `generated`: Candidate was generated but not reviewed.
- `in_review`: Reviewer is actively evaluating it.
- `needs_revision`: Candidate may be acceptable after specific fixes.
- `approved_for_admission`: Candidate is ready to copy into EVMBench.
- `rejected`: Candidate should not be admitted.
- `admitted`: Candidate has been copied into EVMBench and passed required validation.

## Reviewer Checklist

### PDF and OCR Evidence

- Source PDF checksum matches `pdf_inventory.jsonl`.
- OCR text covers the pages containing selected findings.
- Finding headings, severity, and code references are recoverable from the PDF.
- Any OCR uncertainty is captured in `provenance.json` or review notes.

### Finding Quality

- Each selected finding is a credible direct or indirect loss-of-funds issue.
- Each selected finding has a distinct root cause.
- Duplicate findings are merged or removed.
- Each `findings/H-XX.md` describes the same vulnerability as the source finding.
- The `gold_audit.md` contains only approved findings.
- The finding is not merely informational, non-critical, or dependent on unavailable private context.

### Repository Match

- Repository URL is correct for the audited project.
- Candidate commit, tag, or branch matches the audited code.
- In-scope files from the PDF exist at the selected commit.
- Affected contracts and functions are present.
- The repository can be mirrored if required by EVMBench conventions.

### Candidate Folder

- `config.yaml` uses detect-mode compatible fields.
- Every configured vulnerability has a matching `findings/H-XX.md`.
- Each vulnerability has an `award`.
- `Dockerfile` checks out the reviewed repository snapshot.
- `Dockerfile` does not copy findings, provenance, OCR text, or review notes into the agent-visible repository.
- `provenance.json` links the candidate to PDF, OCR, finding, and repo evidence.
- `review_status.yaml` is current.

### EVMBench Admission Readiness

- Candidate audit ID is stable and not already used.
- Candidate is detect-mode only.
- Existing EVMBench behavior does not need to change.
- Any required split or registry updates are understood before admission.
- A validation and smoke-test plan exists.

## Minimum Quality Bar

A candidate can be approved only when all of the following are true:

- It targets Solidity/EVM code.
- It contains at least one reviewed loss-of-funds finding.
- The audited repository and commit are sufficiently verified.
- The vulnerable code is available in the repository snapshot.
- The candidate can be evaluated by the existing detect-mode grader.
- The gold finding text is clear enough for judge comparison.
- The task does not expose answers to the agent.
- The reviewer can explain why the task belongs in EVMBench.

## Rejection Reasons

Use one or more explicit rejection reasons:

- `non_evm`: PDF is not Solidity/EVM.
- `not_loss_of_funds`: Finding does not match the v1 benchmark target.
- `no_public_repo`: Audited code is unavailable.
- `wrong_or_unknown_commit`: Base commit cannot be verified.
- `insufficient_ocr`: OCR does not recover enough evidence.
- `ambiguous_finding`: Finding cannot be separated from surrounding report text.
- `duplicate_root_cause`: Finding duplicates another selected issue.
- `not_reproducible`: Candidate cannot be regenerated from artifacts.
- `leaks_gold`: Candidate exposes answers to the agent.
- `bad_task_shape`: Candidate does not match EVMBench detect-mode structure.
- `licensing_or_access`: Source material cannot be used.
- `out_of_scope`: Requires patch or exploit evaluation.

## Review Record

`review_status.yaml` should record:

- Current state.
- Reviewer identity or handle.
- Checklist booleans.
- Required changes.
- Rejection reasons when rejected.
- Admission notes when approved.
- Timestamp of the last decision.

Example:

```yaml
review_version: 1
candidate_id: cand-2024-05-loop-detect
state: needs_revision
reviewers:
  - name: security-reviewer
    role: task_admission
decisions:
  ocr_evidence_verified: true
  finding_quality_verified: true
  repo_commit_verified: false
  dockerfile_leakage_checked: true
  detect_mode_only: true
rejection_reasons: []
required_changes:
  - Verify exact audited commit against contest snapshot.
notes: "Finding H-01 is suitable, but commit evidence is not strong enough yet."
updated_at: "2026-06-24T00:45:00Z"
```

## Admission Procedure

After approval:

1. Copy the approved candidate folder into `frontier-evals/project/evmbench/audits/<audit_id>`.
2. Apply any existing EVMBench metadata updates required for the audit to be discoverable.
3. Build the audit Docker image.
4. Run existing validation.
5. Run a detect-mode smoke test.
6. Mark `review_status.yaml` as `admitted` only after validation passes.

Admission should be a deliberate repository change, not a side effect of extraction.

