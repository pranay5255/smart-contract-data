# Post-Training Recipes

This document defines baseline data shapes for later post-training work. It does not prescribe a training implementation.

The first usable task type is EVMBench detect mode. Patch and exploit tasks are deferred until detect-mode extraction quality is proven.

## Common Principles

- Keep train, validation, and benchmark evaluation splits explicit.
- Track whether a record came from an admitted EVMBench task or an unadmitted candidate.
- Do not train on gold findings for tasks reserved for benchmark evaluation.
- Preserve provenance from PDF, OCR, normalized finding, repository match, and review state.
- Use existing detect-mode score and detect award as reward signals unless a later design changes the grader.

## Detect-Mode RL Task Records

Purpose: describe environments that can be sampled by an RL runner.

Suggested file:

```text
evmbench_detect_rl_tasks.jsonl
```

Example:

```json
{"task_id":"evmbench:2024-05-loop-generated:detect","audit_id":"2024-05-loop-generated","mode":"detect","source":"admitted_evmbench","docker_image":"evmbench/audit:2024-05-loop-generated","instructions_version":"evmbench-detect-current","max_score":1,"detect_max_award":213.33,"vulnerability_ids":["H-01"],"gold_audit_ref":"frontier-evals/project/evmbench/audits/2024-05-loop-generated/findings/gold_audit.md","provenance_ref":"frontier-evals/project/evmbench/audits/2024-05-loop-generated/provenance.json","split":"train"}
```

Required fields:

- `task_id`
- `audit_id`
- `mode`
- `source`
- `docker_image`
- `instructions_version`
- `max_score`
- `detect_max_award`
- `vulnerability_ids`
- `provenance_ref`
- `split`

## RL Rollout Records

Purpose: store sampled agent attempts and rewards.

Suggested file:

```text
detect_rollouts.jsonl
```

Example:

```json
{"rollout_id":"rollout-000001","task_id":"evmbench:2024-05-loop-generated:detect","audit_id":"2024-05-loop-generated","agent_id":"codex-default","model":"example-model","seed":0,"started_at":"2026-06-24T01:00:00Z","completed_at":"2026-06-24T01:25:00Z","final_report_ref":"rollouts/rollout-000001/submission/audit.md","trajectory_ref":"rollouts/rollout-000001/trajectory.jsonl","score":1,"max_score":1,"detect_award":213.33,"detect_max_award":213.33,"judge_results":[{"vulnerability_id":"H-01","detected":true,"rationale_ref":"rollouts/rollout-000001/judge/H-01.json"}],"error":null}
```

Reward candidates:

- Binary per-vulnerability detection.
- Total `score / max_score`.
- Award-weighted `detect_award / detect_max_award`.
- Judge rationale quality for diagnostics, not as a primary reward unless separately validated.

## SFT Records

Purpose: train models to produce high-quality audit reports from a detect-mode task prompt.

Suggested file:

```text
detect_sft.jsonl
```

Example:

```json
{"record_id":"sft-2024-05-loop-generated","task_id":"evmbench:2024-05-loop-generated:detect","messages":[{"role":"system","content_ref":"prompts/evmbench_detect_system.md"},{"role":"user","content":"Audit the provided Solidity/EVM repository and write the final report to submission/audit.md."},{"role":"assistant","content_ref":"frontier-evals/project/evmbench/audits/2024-05-loop-generated/findings/gold_audit.md"}],"source":"gold_audit","split":"train","provenance_ref":"frontier-evals/project/evmbench/audits/2024-05-loop-generated/provenance.json"}
```

SFT records should use reviewed gold content only. Do not include tasks that are held out for benchmark evaluation.

## DPO Records

Purpose: train preferences between stronger and weaker audit reports for the same task.

Suggested file:

```text
detect_dpo.jsonl
```

Example:

```json
{"record_id":"dpo-2024-05-loop-generated-0001","task_id":"evmbench:2024-05-loop-generated:detect","prompt_ref":"prompts/tasks/2024-05-loop-generated-detect.json","chosen_ref":"rollouts/high_score/audit.md","rejected_ref":"rollouts/low_score/audit.md","chosen_score":1,"rejected_score":0,"preference_reason":"Chosen report detects H-01 with correct root cause and affected code path; rejected report reports unrelated generic risk.","judge_results_ref":"preferences/dpo-2024-05-loop-generated-0001-judges.json","split":"train"}
```

Selection rules:

- Prefer pairs with clear score separation.
- Avoid pairs where both reports are wrong for different reasons unless the preference is manually reviewed.
- Keep prompt and environment identity identical between chosen and rejected outputs.

## GRPO and Grouped RL Records

Purpose: support group-based policy optimization or later RL variants that compare multiple outputs for the same task.

Suggested file:

```text
detect_grouped_rollouts.jsonl
```

Example:

```json
{"group_id":"grpo-2024-05-loop-generated-0001","task_id":"evmbench:2024-05-loop-generated:detect","prompt_ref":"prompts/tasks/2024-05-loop-generated-detect.json","samples":[{"rollout_id":"r1","final_report_ref":"rollouts/r1/submission/audit.md","score":1,"detect_award":213.33},{"rollout_id":"r2","final_report_ref":"rollouts/r2/submission/audit.md","score":0,"detect_award":0.0},{"rollout_id":"r3","final_report_ref":"rollouts/r3/submission/audit.md","score":0,"detect_award":0.0}],"reward_field":"detect_award","normalization":"group_relative","split":"train"}
```

Notes:

- Group samples should share the same task, prompt version, and environment version.
- Store raw scores before normalization.
- Keep failed infrastructure runs separate from low-quality audit reports.

## Candidate vs Admitted Records

Training data may reference unadmitted candidates for experimentation, but those records must be labeled:

```json
{"source":"candidate_unadmitted","review_state":"needs_revision"}
```

Default policy should use only `source: admitted_evmbench` for serious post-training runs unless an experiment explicitly studies candidate data quality.

## Leakage Controls

- Never mix gold reports from evaluation tasks into training records.
- Never include `findings/H-XX.md` or `gold_audit.md` in an agent prompt unless the recipe is explicitly supervised training.
- Store split assignment with task identity, not just rollout identity.
- Keep PDF and OCR provenance available for audits of training contamination.

