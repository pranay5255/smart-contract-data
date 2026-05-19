# EVMbench Audit Conversion Plan

## Plan

Create an EVMbench audit-conversion workflow in phases, starting with detect-mode tasks only. The first deliverable should be tooling and manifests, not a large batch of generated tasks, because raw audit repos and sanitized mirrors need manual approval.

## Task List

1. **Define Inputs And Outputs**
   - Confirm raw audit repo root, e.g. `data/raw_audit_repos/`.
   - Confirm EVMbench output root, e.g. `project/evmbench/`.
   - Keep raw reports, extracted text, and generated manifests out of git or under ignored paths.

2. **Inventory Audit Reports**
   - Recursively scan raw repos for `.pdf`, `.md`, `.markdown`, `.txt`, `.json`.
   - Detect likely Solidity project files: `foundry.toml`, `hardhat.config.*`, `package.json`, `remappings.txt`, `.sol`.
   - Write `candidate_reports.jsonl`.

3. **Extract Report Text**
   - Extract Markdown directly.
   - Extract PDFs using deterministic tooling such as `pdftotext`, with fallback/error capture.
   - Store extracted text by stable content hash.
   - Add `text_path`, `extractor`, `extract_success`, `extract_error`, and `sha256`.

4. **Normalize Reports**
   - Parse project name, title, date, auditor, report URL, source URLs, and finding sections.
   - Capture finding id, title, severity, body, links, and code references.
   - Write `normalized_audit_reports.jsonl`.

5. **Select Candidate EVMbench Tasks**
   - Keep only High/Critical loss-of-funds style findings.
   - Require identifiable public source repo and audited commit/tag.
   - Exclude vague, private, informational, gas-only, centralization-only, or policy-only reports.
   - Write `candidate_evmbench_tasks.jsonl`.

6. **Manual Approval Gate**
   - Select 5-10 candidates for v1.
   - Verify public source repo, reproducible commit, usable license/context, and specific finding descriptions.
   - Mark approved records with `status: approved_detect_v1`.

7. **Prepare Sanitized Source Mirrors**
   - Checkout vulnerable source snapshot.
   - Remove audit reports, fixes, exploit notes, answer keys, and generated junk.
   - Commit sanitized snapshot.
   - Record mirror URL and commit SHA in the manifest.

8. **Generate Detect Task Directories**
   - Create `project/evmbench/audits/<audit_id>/`.
   - Add `Dockerfile`, `config.yaml`, `findings/H-XX.md`, and `findings/gold_audit.md`.
   - Use deterministic ids like `<year-month>-<project-slug>`.
   - Do not add patch/exploit fields in v1.

9. **Normalize Gold Findings**
   - Make each finding self-contained.
   - Include affected contract/function, root cause, impact, scenario, references, and remediation where available.
   - Remove source-identity leakage that is not needed for grading.

10. **Update EVMbench Metadata**
    - Append approved ids to `splits/detect-tasks.txt`.
    - Append rows to `audits/task_info_audits.csv`.
    - Maintain a generated mapping from task id back to raw report metadata.

11. **Validate Static Structure**
    - Check every `config.yaml` vulnerability has a matching `findings/H-XX.md`.
    - Check every vulnerability has an `award`.
    - Check every Dockerfile uses the approved sanitized mirror.
    - Record results in a validation log.

12. **Build And Smoke Test**
    - Build each task Docker image.
    - Confirm `$AUDIT_DIR` contains only sanitized source.
    - Run gold detect smoke with `apply_gold_solution=True`.
    - Run one real-agent smoke test after gold smoke passes.

13. **Quality Gates**
    - Reject tasks with unreproducible source snapshots, vague gold findings, leaked reports/fixes, Docker build failures, or failed gold smoke tests.
    - Track rejection reasons in the manifest.

14. **Later Promotions**
    - Promote selected detect tasks to patch mode only when fix commits/tests are clear.
    - Promote selected patch-capable tasks to exploit mode only after exploit harness grading passes.
