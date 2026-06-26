# Architectural Insights

## Representation

| Lesson | Evidence | Implication |
|---|---|---|
| Token budget controls how much context can survive TTFT and inference. | NVARC simplified Qwen chat grids to digit/newline/user/assistant tokens; MindsAI caps input/target lengths; ARChitects pads to fixed grid-like text with mask tokens. | ARC solvers need representations that preserve train examples, test input, and candidate output without wasting sequence length. |
| Grid serialization is not neutral. | CodeT5 seq2seq predicts structured target headers; Qwen emits chat-grid rows; diffusion models fill masked grid tokens. | A model can fail because the output syntax is unnatural, even if it learned the transformation concept. |
| Output shape deserves explicit handling. | ARChitects uses a separate size model/shape detection path; autoregressive systems often embed shape in the output syntax or search constraints. | Shape mistakes are cheap to detect and expensive to recover from after final scoring. |

## Test-Time Fine-Tuning

| Lesson | Evidence | Implication |
|---|---|---|
| TTFT is the common online adaptation mechanism. | NVARC, ARChitects, MindsAI, Lonnie, and Barbadillo all use task-local adaptation. | Static inference is no longer competitive at the top of ARC-AGI-2. |
| LoRA is favored when the base model is large. | NVARC, ARChitects, Lonnie, and Barbadillo use LoRA-style adapters. | Online updates must fit per-task time and memory budgets. |
| Full or all-layer updates remain attractive when the model is small enough. | MindsAI CodeT5 configs expose all encoder/decoder layers for training and optional LoRA blocks disabled by default. | For smaller seq2seq models, updating the whole stack can be simpler than adapter engineering. |

## Augmentation

| Lesson | Evidence | Implication |
|---|---|---|
| Geometric and color symmetries are foundational. | Every visible top-five code path applies rotations/transposes and color permutations. | Any new ARC solver should treat symmetry augmentation as table stakes. |
| Augmentations must be reversible. | NVARC, MindsAI, Lonnie, and Barbadillo invert transformed predictions before submission; ARChitects transforms logits/grids back into a common frame. | Candidate generation and scoring need a canonical grid frame. |
| Augmentation count is a compute tradeoff, not a pure accuracy knob. | NVARC deliberately uses eight fixed rescoring augmentations; Barbadillo schedules GPU work around single-task TTT; MindsAI uses confidence filtering to reduce later work. | More views can help, but only if they leave enough budget for training/search. |

## Search and Candidate Selection

| Lesson | Evidence | Implication |
|---|---|---|
| Candidate selection is a top-tier bottleneck. | NVARC rescoring formula, MindsAI vote filtering, ARChitects visited-count and similarity scores, and ARChitects-2024 selection algorithms all appear in public sources. | Producing many candidates is insufficient when the evaluator accepts only two attempts. |
| Cached autoregressive search is still powerful. | NVARC's DFS uses `past_key_values` and a narrow ARC token set. | For text-grid output, exploiting the KV cache can make deeper search feasible. |
| Diffusion replaces left-to-right beam search with iterative state refinement. | ARChitects repeatedly masks uncertain positions and samples/fills grid states. | Diffusion can explore whole-grid corrections that are awkward for strict autoregressive decoding. |

## Synthetic Data

| Lesson | Evidence | Implication |
|---|---|---|
| Synthetic data can be decisive when generated as executable puzzle programs. | NVARC's multi-stage SDG pipeline is the defining feature of the winning system. | Programmatic validation and consistency checks are stronger than free-form synthetic examples alone. |
| Synthetic data can fail when distribution or representation mismatches. | ARChitects reports failed synthetic attempts; Barbadillo reports BARC induction was promising but not enough for the final submission. | Data generation must be coupled to model format, scoring, and validation. |
| Human descriptions remain useful seeds. | NVARC uses H-ARC and BARC descriptions plus manually labeled evaluation summaries as seed material. | Natural-language rationales can help generate new ARC concepts, but source leakage and benchmark hygiene need clear documentation. |

## Systems and Memory

| Lesson | Evidence | Implication |
|---|---|---|
| Kaggle L4 limits force small/quantized/adapter-heavy designs. | NVARC uses 4B maximum in competition; ARChitects and ARChitects-2024 descendants use 4-bit paths; notebooks target four GPUs or L4. | Offline scale helps, but online inference must be engineered for a fixed envelope. |
| Gradient checkpointing is a tradeoff, not a default. | NVARC disables it for TTFT speed; ARChitects enables activation checkpointing in diffusion; Lonnie/Barbadillo use Unsloth checkpointing. | The best choice depends on model size, sequence length, and whether time or memory is tighter. |
| bf16 is common where hardware supports it. | NVARC, ARChitects, MindsAI configs, and multiple notebooks use bf16. | Mixed precision is a baseline optimization, not an experimental feature. |

## Open Research Questions

| Question | Why it matters |
|---|---|
| Can diffusion and cached autoregressive DFS be ensembled without one scorer dominating the other? | NVARC's TRM attempt shows cross-family ensembling can be hard to select correctly. |
| Can synthetic puzzle generation be audited for leakage while preserving the gains? | NVARC reports using evaluation-puzzle descriptions in synthetic data development, so hygiene and split discipline matter. |
| Can learned output-shape priors reduce search enough to fund deeper TTFT? | ARChitects shows shape prediction is a separate useful stage. |
| Can scoring learn from failed candidates instead of relying on hand-designed likelihood formulas? | All systems spend significant effort selecting two final attempts. |
| Can TTFT be made robust under batch nondeterminism and rerun variance? | NVARC and Lonnie both report meaningful variability across runs or batch choices. |
