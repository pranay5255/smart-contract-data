# Design Questions

These questions should stay visible during implementation. They are grouped by area so assumptions are explicit.

## Task Admission

- What exact validation commands must pass before `approved_for_admission` becomes `admitted`?
- Should the first feasibility batch use only one vulnerability per task, or allow multi-finding detect tasks from the start?
- How should detect awards be assigned when the source audit has no contest award amount?
- What naming convention should generated `evmbench_audit_id` values use to avoid collisions with hand-authored tasks?
- Which EVMBench metadata files must be updated during admission beyond the audit folder itself?

## OCR

- Which vLLM vision/OCR model should the Modal endpoint use for the feasibility batch?
- Should OCR run page-by-page, by page range, or with multi-page context?
- What confidence or quality signals are reliable enough to gate extraction?
- How should tables, footnotes, code snippets, and two-column layouts be represented?
- Should rendered page images be retained long term, or can checksums plus OCR records be enough?

## Finding Selection

- What threshold separates direct or indirect loss-of-funds findings from out-of-scope findings?
- Should medium-severity findings be selected when they have clear asset-loss impact?
- How should duplicate findings across multiple auditors or contest submissions be merged?
- Should disputed findings be allowed if the technical issue is still credible?
- How much remediation detail belongs in `findings/H-XX.md` for grader comparison?

## Grading

- Is the existing detect judge prompt sufficient for generated PDF-derived findings?
- Do generated findings need stricter formatting to improve judge reliability?
- Should `findings/gold_audit.md` be generated from selected `H-XX` files or independently reviewed?
- Should detect awards be normalized across tasks for RL, or preserve source award values?
- How should partial detections be analyzed if the current grader remains binary per vulnerability?

## Repository Matching

- Should candidate generation require an EVMBench mirror before review, or only before admission?
- How should the pipeline handle audit reports that reference private repos later made public?
- What is the fallback when the exact audited commit is not known but file paths match a release tag?
- Should dependency lockfiles be part of the match confidence decision?
- How should monorepos and multi-package scopes be represented in `repo_matches.jsonl`?

## Review Workflow

- Who can mark a candidate as `approved_for_admission`?
- Is one reviewer enough, or should security and infrastructure review be separate gates?
- Should review happen in plain YAML, a small web UI, or pull request comments?
- How should reviewer edits to generated findings be tracked against original extraction output?
- Should rejected candidates remain in the artifact root indefinitely for analysis?

## Training Recipes

- Which tasks are held out permanently from SFT and preference training?
- Should candidate-only tasks be usable for exploratory RL before EVMBench admission?
- What rollout metadata is required to reproduce rewards?
- How should infrastructure failures be excluded from preference pairs?
- Should GRPO groups use binary score, award-weighted score, or another reward field?

## Security and Leakage

- What automated checks should verify that gold findings are not copied into Docker images?
- Should provenance files include full OCR snippets, or only references and digests?
- How should PDFs with restrictive licensing or unclear redistribution rights be handled?
- What redaction policy is needed for private source paths, user names, or audit platform metadata?
- Should generated candidate artifacts be treated as sensitive until admitted?

