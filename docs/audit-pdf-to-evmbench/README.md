# Audit PDF to EVMBench

This directory defines the planned pipeline for converting raw Solidity/EVM audit PDFs into EVMBench detect-mode reinforcement learning tasks.

The current pass adds the first OCR service implementation and its setup documentation. It does not add generated task folders, registry entries, split files, or any changes to existing EVMBench or nanoeval behavior.

## Goals

- Turn raw audit PDFs into structured candidate artifacts for EVMBench.
- Target v1 at Solidity/EVM detect-mode tasks only.
- Use a Modal-hosted SGLang `baidu/Unlimited-OCR` endpoint for PDF OCR.
- Keep generated task folders as candidate artifacts until human review approves them.
- Require human review before copying any candidate into `frontier-evals/project/evmbench/audits`.
- Preserve the existing EVMBench detect, patch, exploit, and nanoeval behavior for v1.

## Non-Goals

- No automatic admission of generated tasks into EVMBench.
- No patch-mode or exploit-mode task generation until detect extraction quality is proven.
- No grader changes in the first version.
- No repository mirroring, Docker image building, or training data generation in this documentation pass.

## Document Map

- [PRD.md](PRD.md): Product goal, scope, users, success criteria, risks, and milestones.
- [TASK_PLAN.md](TASK_PLAN.md): Execution plan from PDF inventory through candidate admission.
- [ARCHITECTURE.md](ARCHITECTURE.md): Pipeline components, data flow, and EVMBench boundaries.
- [DATA_SCHEMAS.md](DATA_SCHEMAS.md): Planned JSONL, YAML, and candidate task folder shapes.
- [OCR_MODAL_SGLANG.md](OCR_MODAL_SGLANG.md): Modal deployment, API contract, and smoke-test commands for the SGLang Unlimited-OCR endpoint.
- [HUMAN_REVIEW.md](HUMAN_REVIEW.md): Reviewer workflow, approval states, rejection reasons, and quality bar.
- [POST_TRAINING_RECIPES.md](POST_TRAINING_RECIPES.md): Baseline data shapes for RL, SFT, DPO, and GRPO planning.
- [POST_TRAINING_DATASET_SOURCES.md](POST_TRAINING_DATASET_SOURCES.md): Hugging Face and local dataset inventory for post-training source selection.
- [LWM_POST_TRAINING_MATH.md](LWM_POST_TRAINING_MATH.md): LWM-only post-training math, exact-EVM verifier loop, and simulator-fidelity evals.
- [DESIGN_QUESTIONS.md](DESIGN_QUESTIONS.md): Open decisions to resolve before or during implementation.

## Recommended Reading Order

1. Start with [PRD.md](PRD.md) to understand the product boundary.
2. Read [ARCHITECTURE.md](ARCHITECTURE.md) for the pipeline shape.
3. Read [DATA_SCHEMAS.md](DATA_SCHEMAS.md) before implementation work.
4. Use [TASK_PLAN.md](TASK_PLAN.md) to sequence milestones.
5. Use [HUMAN_REVIEW.md](HUMAN_REVIEW.md) to define task admission gates.
6. Use [POST_TRAINING_RECIPES.md](POST_TRAINING_RECIPES.md) once candidate and admitted tasks exist.
7. Keep [DESIGN_QUESTIONS.md](DESIGN_QUESTIONS.md) open during implementation.

## Current Status

Status: design specification plus initial Modal SGLang OCR service.

The intended first implementation milestone is a small feasibility batch. The batch should prove that the pipeline can ingest a few audit PDFs, OCR them, extract loss-of-funds findings, match each finding to a repository and base commit, generate candidate detect-mode task folders, and route those candidates through human review.

The first admitted task type is detect-mode only. Patch and exploit tasks stay out of scope until the detect-mode extraction and review process is reliable.
