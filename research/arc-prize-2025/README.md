# ARC Prize 2025 Top-Five Research Review

This directory reviews the top five ARC Prize 2025 submissions with equal depth. The goal is to compare the systems as systems: data, representation, adaptation, search, scoring, and low-level runtime choices.

## Reading Order

1. [00_methodology.md](00_methodology.md) - evidence hierarchy, claim labels, and known gaps.
2. [01_top5_comparison.md](01_top5_comparison.md) - leaderboard, taxonomy, and shared patterns.
3. [02_architectural_insights.md](02_architectural_insights.md) - cross-solution lessons.
4. Deep dives:
   - [NVARC](deep-dives/01_nvarc.md)
   - [ARChitects](deep-dives/02_architects.md)
   - [MindsAI](deep-dives/03_mindsai.md)
   - [Lonnie](deep-dives/04_lonnie.md)
   - [G. Barbadillo](deep-dives/05_g_barbadillo.md)
5. [systems/attention_kv_gradients_activations.md](systems/attention_kv_gradients_activations.md) - shared attention, KV-cache, gradient, activation, memory, and representation review.

## Source Index

Primary sources used:

| Source | Role | Link |
|---|---|---|
| ARC Prize 2025 official results page | Leaderboard order, score table, official source links | <https://arcprize.org/competitions/2025> |
| ARC Prize 2025 technical report / analysis | Benchmark context and official analysis | <https://arxiv.org/abs/2601.10904> |
| ARC Prize 2025 Kaggle competition | Competition environment and submissions | <https://www.kaggle.com/competitions/arc-prize-2025> |
| NVARC paper | Synthetic data, Qwen3, LoRA TTFT, DFS, rescoring, TRM | <https://drive.google.com/file/d/1vkEluaaJTzaZiJL69TkZovJUkPSDH5Xc/view> |
| NVARC code repository | Public NVARC code pointers | <https://github.com/1ytic/NVARC> |
| NVARC Kaggle notebook | Public submitted code evidence | <https://www.kaggle.com/code/sorokin/arc2-qwen3-unsloth-flash-lora-batch4-queue> |
| ARChitects 2025 writeup | LLaDA pivot, diffusion, recursive latent sampling, failed ideas | <https://lambdalabsml.github.io/ARC2025_Solution_by_the_ARChitects/> |
| ARChitects Kaggle notebook | Public masked-diffusion code evidence | <https://www.kaggle.com/code/gregkamradt/arc-2025-diffusion> |
| MindsAI 2025 Kaggle notebook | Submission wrapper and CodeT5 config | <https://www.kaggle.com/code/gregkamradt/mindsai-tufa-2025-v4> |
| MindsAI solution-code Kaggle dataset | Public source archive with configs and docs | <https://www.kaggle.com/datasets/jcole75/arc2025-solution-code> |
| MindsAI paper | Background on TTFT/AIRV lineage; not treated as the exact 2025 Kaggle stack where it conflicts with code | <https://arxiv.org/abs/2506.14276> |
| Lonnie Kaggle notebook | Code evidence for active-layer control and ARChitects-2024 adaptation | <https://www.kaggle.com/code/lonnieqin/lb-5-83-baseline-from-1st-place-of-2024> |
| G. Barbadillo solution summary | Search-and-learn framing, BARC experiments, hindsight relabeling, RL attempts | <https://ironbar.github.io/arc25/05_Solution_Summary/> |
| G. Barbadillo Kaggle notebook | Code evidence for single-task TTT implementation | <https://www.kaggle.com/code/ironbar/the-architects-single-task-ttt> |

Source gaps:

| Gap | Treatment |
|---|---|
| Some Kaggle pages are JS-only in a browser. | Public notebook and dataset API pulls were used when available; docs still link the human-facing Kaggle pages. |
| The official ARC page rounds scores while some papers/notebooks report public leaderboard variants. | The comparison table uses the official ARC table score, with per-solution notes for alternate reported public scores. |
| MindsAI paper names LongT5 in its described research system, while the 2025 Kaggle notebook and solution-code dataset use CodeT5 variants. | The 2025 deep dive treats CodeT5 / Salesforce CodeT5-style seq2seq as the leaderboard submission stack and records LongT5 as background source conflict. |
| Private leaderboard and hidden test internals are not public. | Claims about hidden-set generalization are labeled as inference unless directly reported by teams. |

## Glossary

| Term | Meaning |
|---|---|
| ARC-AGI-2 | The 2025 ARC benchmark used by the competition. |
| TTFT / TTT | Test-time fine-tuning or test-time training on augmented examples derived from each hidden task. |
| AIRV | Augment, Inference, Reverse augmentation, Vote. A MindsAI term for augmented inference and voting. |
| LLaDA / masked diffusion | A language-modeling approach that fills masked tokens iteratively instead of decoding left-to-right only. |
| DFS decoding | Depth-first search over output tokens, often using model likelihood to prune candidates. |
| KV cache | Stored attention keys and values reused during autoregressive decoding. |
| Product of experts / PoE | Combining transformed-view logits or probabilities so multiple augmented views jointly shape a prediction. |
| LoRA | Low-rank adapter training that updates small adapter matrices rather than all model weights. |
| TRM | Tiny Recursive Model; a small recurrent reasoning model with per-puzzle embeddings in the referenced implementation. |
| BARC | Prior ARC induction/transduction dataset and method family used as data or comparison in several discussions. |

## Notes

All documents avoid long verbatim quotations. Each deep dive uses the same rubric and marks evidence type as `code`, `paper`, `writeup`, `blog/commentary`, or `inference`.
