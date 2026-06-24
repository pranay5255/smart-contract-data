# Data Schemas

These schemas define planned artifact shapes. They are not implementation code. JSONL files contain one JSON object per line.

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
  "generator_version": "unimplemented-docs-v1"
}
```

