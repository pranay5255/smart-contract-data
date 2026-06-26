# Attention, KV, Gradients, Activations

This systems review compares visible low-level choices across the top-five ARC Prize 2025 submissions. It uses only public code, papers, and team writeups; inferred items are marked.

## Attention And Decoding

| Solution | Attention / decoding family | Visible details | Systems implication |
|---|---|---|---|
| NVARC | Autoregressive Qwen3 with DFS | Public code primes the prefix once, then recursively expands tokens using `past_key_values` and `use_cache=True`. | Strong fit for constrained text-grid decoding; KV reuse makes deeper DFS practical. |
| ARChitects | Masked diffusion / LLaDA | Public code repeatedly forwards masked grid states, averages augmented-view logits, and refines/resamples positions. | Trades KV-cache efficiency for whole-grid correction and non-left-to-right reasoning. |
| MindsAI | Seq2seq CodeT5-style generation | Public configs use seq2seq generation with beams/return sequences; no custom cache/search path is visible. | Relies on framework generation and scoring/voting rather than bespoke token search. |
| Lonnie | Autoregressive ARChitects-2024 stack | Inherited causal LM inference and decoder selection; no new custom DFS cache path. | Uses a known ARC-2024 path, tuned for the 2025 runtime. |
| G. Barbadillo | Autoregressive ARChitects-2024 stack | Same model family as Lonnie, organized around single-task TTT. | Focuses engineering on task scheduling and TTT rather than new attention machinery. |

## KV Cache And Prefix Reuse

| Solution | KV-cache visibility | Notes |
|---|---|---|
| NVARC | Explicit | `inference_turbo_dfs` calls the model on prefix tokens and passes `outputs.past_key_values` into recursive DFS expansions. |
| ARChitects | Not applicable / not visible | Diffusion repeatedly evaluates masked states; no autoregressive prefix-cache path is visible. |
| MindsAI | Framework-level only | Seq2seq generation may use decoder cache internally, but no public code exposes custom KV logic. |
| Lonnie | Framework/inherited only | Likely inherited from the causal LM generation path; no notebook-specific KV work. |
| G. Barbadillo | Framework/inherited only | Same as Lonnie; final work centers on one-task scheduling. |

Batch-invariance note: NVARC's paper reports testing batch-invariant inference from Thinking Machines Lab. It improved precision/local validation but was about 17 percent slower in Kaggle, so it was not used in the final submission.

## Gradients And Online Adaptation

| Solution | Online adaptation | Gradient controls |
|---|---|---|
| NVARC | Per-puzzle LoRA TTFT | Rank 256, alpha 32, bf16, AdamW torch, cosine schedule, gradient checkpointing disabled, 4-bit disabled. |
| ARChitects | Per-task LoRA TTFT | Rank 64, alpha 16, AdamW8bit, separate lr for LoRA and embedding params, Accelerate bf16. |
| MindsAI | CodeT5 TTFT | Visible configs use one epoch, gradient accumulation 16, bf16, gradient checkpointing, focal loss; optional LoRA blocks are present but disabled by default in visible CodeT5 configs. |
| Lonnie | LoRA TTFT over 2024 ARChitects baseline | Active first layers, frozen later layers, Unsloth 4-bit, AdamW8bit, LoRA target modules across attention/MLP/embed/lm_head. |
| G. Barbadillo | Single-task LoRA TTT | Rank 4, alpha 16, AdamW8bit, gradient accumulation 1, one epoch, 4-GPU scheduling. |

## Activations, Precision, And Memory

| Solution | Precision / memory choices | Tradeoff |
|---|---|---|
| NVARC | bf16, no 4-bit in public TTFT, no gradient checkpointing, Flash Attention 2 reported in paper. | More memory per model than 4-bit, but faster and simpler online LoRA updates. |
| ARChitects | 4-bit model artifacts, bf16 load path, LLaDA activation checkpointing `one_in_two`. | Saves memory for diffusion but pays recomputation cost. |
| MindsAI | bf16 and gradient checkpointing in CodeT5 configs; mixed precision inference controls; TPU/Flax path exists. | More framework flexibility, but public wrapper does not fully reveal actual competition accelerator path. |
| Lonnie | Unsloth 4-bit plus gradient checkpointing. | Fits the 2024 large causal LM baseline inside L4 constraints. |
| G. Barbadillo | Unsloth 4-bit plus gradient checkpointing, model copied to shared memory. | Makes many single-task runs feasible in a no-internet Kaggle environment. |

## Representation And Tokenization

| Solution | Representation | Tokenization / syntax risks |
|---|---|---|
| NVARC | Qwen chat turns for each input/output pair, compact digit-row grids. | Efficient token set, but autoregressive row order can cascade errors. |
| ARChitects | Fixed text grid with mask token and 10-color + mask state. | Needs correct shape and mask scheduling; parser/scorer is custom. |
| MindsAI | Seq2seq `solve:` prompt and target header with dimensions/symbols/rows. | Header syntax helps shape but increases target-format burden. |
| Lonnie | ARChitects-2024 formatter. | Proven in 2024, but may not match ARC-AGI-2 difficulty. |
| G. Barbadillo | Same inherited ARChitects-2024 formatter. | Single-task TTFT reduces task interference but not representation limitations. |

## Search, Scoring, And Candidate Memory

| Solution | Candidate memory | Final scoring method |
|---|---|---|
| NVARC | Stores DFS beams and candidate grids; caches augmented scores per grid id. | Combines DFS score with augmented likelihood scores; final decoder aggregates candidates. |
| ARChitects | Tracks visited grid states across diffusion restarts. | Most-visited, cosine similarity, hinge-like score, and shape confidence signals. |
| MindsAI | Aggregated predictions across model/self-ensemble cycles. | Vote counts, z-score filtering, ambiguous top-two agreement, and final submission handler. |
| Lonnie | Decoder store from inherited ARChitects code. | `score_full_probmul_3` with augmented scoring. |
| G. Barbadillo | Per-task stored inference outputs. | `score_full_probmul_3` with augmented scoring. |

## Runtime Constraints

| Constraint | Common response |
|---|---|
| 12-hour Kaggle budget | Early stop/buffer times, per-task queues, confidence filtering, and constrained search. |
| 4 L4 GPUs | Multiprocessing workers, GPU slot locks, LoRA rather than full online training for larger models. |
| No internet | Offline wheelhouses, Kaggle model/dataset sources, copied source code. |
| Long sequences | Compact grid serialization, max sequence clipping, activation checkpointing, 4-bit load paths. |
| Two attempts per test item | Heavy investment in scoring, voting, and candidate deduplication. |

## Practical Takeaways

| If building a new ARC-AGI-2 solver | Use this lesson |
|---|---|
| Choosing a model family | Decide first whether the output process is left-to-right, seq2seq, or whole-grid diffusion; representation and scorer follow from that choice. |
| Adding TTFT | Budget for adapter reset, per-task data construction, and cleanup, not just training steps. |
| Adding augmentation | Implement reversible transforms and canonical candidate ids before scaling generation. |
| Adding search | Cache model states if autoregressive; if diffusion, cache candidate grids and scores instead. |
| Adding synthetic data | Validate by executable programs or strict consistency checks; weak synthetic data can hurt or waste compute. |
