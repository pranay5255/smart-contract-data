# Top-Five Comparison

## Leaderboard

| Rank | Team / submitter | Official ARC table score | Primary modeling family | Main public evidence |
|---:|---|---:|---|---|
| 1 | NVARC | 27.5 | Qwen3 autoregressive LLM with LoRA TTFT and DFS search | Paper, GitHub, Kaggle notebook |
| 2 | ARChitects | 17.5 | LLaDA-style masked diffusion language model | Team writeup, Kaggle notebook |
| 3 | MindsAI | 14.2 | CodeT5-style seq2seq ensemble with TTFT and AIRV | Kaggle notebook, solution-code dataset, paper background |
| 4 | Lonnie | 5.83 | 2024 ARChitects autoregressive baseline adapted to ARC-AGI-2 | Kaggle notebook |
| 5 | G. Barbadillo | 5.0 | Single-task TTT over ARChitects-2024 stack | Blog, Kaggle notebook |

Notes:

- NVARC's paper reports a 27.64 public leaderboard score during the competition and a 29.72 post-deadline variant. The official ARC results table rounds/lists the ranked score as 27.5.
- Lonnie's notebook reports large variance between public/local and semi-private runs; the official ARC score remains 5.83.
- G. Barbadillo's blog reports several explored approaches, but the final public notebook is the single-task TTT system.

## System Taxonomy

| Axis | NVARC | ARChitects | MindsAI | Lonnie | G. Barbadillo |
|---|---|---|---|---|---|
| Base paradigm | Autoregressive Qwen3 | Masked diffusion / LLaDA | Seq2seq CodeT5-style | Autoregressive Mistral-NeMo-Minitron | Autoregressive Mistral-NeMo-Minitron |
| Offline training | Large synthetic puzzle pretraining/SFT | LLaDA models trained for ARC grids | CodeT5 checkpoints and pretraining pipeline | Reuses public ARChitects-2024 model | Reuses public ARChitects-2024 model |
| Test-time adaptation | Per-puzzle LoRA TTFT | Per-task LoRA TTFT over masked tokens | TTFT over augmented samples | LoRA tuning with active-layer control | Single-task TTFT |
| Candidate generation | Cached DFS over ARC token set | Shape prediction then iterative masked grid sampling | Beam generation plus augmentation/self/model ensemble | ARChitects decoder with augmentation | ARChitects decoder with single-task scheduling |
| Candidate scoring | DFS score plus augmented log-probability rescoring | Most-visited, cosine/hinge-like scores, shape confidence | Vote aggregation, z-score filtering, AIRV | Augmented score selection | Augmented score selection |
| Runtime posture | 4 L4 Kaggle notebook, Qwen3 4B bf16 | 4 worker diffusion notebook, bf16 model load, 4-bit checkpoints | Wrapper configured without GPU in pulled metadata; solution supports GPU/TPU/Flax | Nvidia L4 notebook | Nvidia L4 notebook |

## Shared Patterns

| Pattern | Evidence across solutions | Interpretation |
|---|---|---|
| Test-time adaptation is central | All top-five systems use TTFT/TTT or task-local adaptation. | ARC-AGI-2 rewards rapid task-specific specialization more than static one-shot inference. |
| Augmentations are not optional | Geometric transforms, color permutations, train-example shuffling, and reverse transforms appear in all code-visible systems. | The benchmark's symmetries are valuable enough that candidates are often produced and rescored under multiple views. |
| Representation is a first-order design choice | Qwen chat grids, LLaDA masked grids, CodeT5 text grids, and ARChitects token formats differ materially. | Solver quality is tied to how much of the grid task becomes natural for the base model and tokenizer. |
| Scoring matters almost as much as generation | NVARC rescoring, ARChitects likelihood/visited counts, MindsAI voting/filtering, and ARChitects-2024 selection variants all invest in final choice. | With only two allowed attempts per test item, candidate selection is a bottleneck. |
| Compute limits shape algorithms | Kaggle's 12-hour and L4 constraints appear repeatedly. | Successful systems compress offline learning into small-ish models and spend online compute selectively. |
| Synthetic data is beneficial but brittle | NVARC's synthetic pipeline is central; ARChitects reports failed synthetic-data attempts; Barbadillo found BARC experiments uneven. | Data scale helps when representation and generation quality match the model; naive synthetic additions can fail. |

## Distinguishing Bets

| Solution | Main bet | Why it is different |
|---|---|---|
| NVARC | High-quality synthetic puzzle programs can teach a compact Qwen3 model a reusable ARC prior, then TTFT and cached DFS can adapt it per task. | It pushes hardest on synthetic data plus autoregressive search engineering. |
| ARChitects | Masked diffusion can represent grid completion more naturally than strict left-to-right output decoding. | It changes the generation mechanism rather than only improving data or scoring. |
| MindsAI | Seq2seq models can learn a compact grid representation and benefit from TTFT, AIRV, tokenizer dropout, focal loss, and ensembles. | It is the strongest code-visible CodeT5-style seq2seq approach in the top five. |
| Lonnie | The 2024 winning ARChitects baseline still has ARC-AGI-2 signal if tuned under L4 limits and active-layer control. | It is a targeted adaptation rather than a new model family. |
| G. Barbadillo | Robust single-task TTT is a better final competition strategy than more speculative search-and-learn/RL ideas under time limits. | It explicitly prioritizes a stable final submission after many experiments. |

## Evidence Gaps That Affect Comparison

| Gap | Impact |
|---|---|
| Private hidden test composition is unknown. | Generalization claims cannot be audited task by task. |
| Some notebooks are mirrored by ARC/Greg Kamradt while original team artifacts may live elsewhere. | Human-facing Kaggle URLs are cited, and exact API-pulled metadata is treated as code evidence. |
| Offline training scripts and model weights are not uniformly public for every team. | Offline data/training depth is clearest for NVARC and MindsAI, weaker for Lonnie and Barbadillo. |
| Post-deadline variants exist. | The main comparison uses official ranked scores; post-deadline results are secondary notes. |
