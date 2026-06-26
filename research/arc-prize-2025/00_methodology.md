# Methodology

## Scope

This review covers the top five entries on the ARC Prize 2025 official results page:

| Rank | Team / submitter | Official score |
|---:|---|---:|
| 1 | NVARC | 27.5 |
| 2 | ARChitects | 17.5 |
| 3 | MindsAI | 14.2 |
| 4 | Lonnie | 5.83 |
| 5 | G. Barbadillo | 5.0 |

The score column is copied from the official ARC results table. Some teams report more precise public leaderboard scores or later variants; those are included only in the relevant deep dive.

## Evidence Hierarchy

Claims are labeled by evidence type:

| Label | Meaning | Weight |
|---|---|---|
| `code` | Public notebook, repository, or dataset source code. | Highest for implementation details. |
| `paper` | Team paper, technical paper, or arXiv report. | High for architecture, data, and experimental claims. |
| `writeup` | Team-authored blog or solution summary. | High for intent, ablations, and negative results. |
| `blog/commentary` | Interview, workshop, or third-party commentary. | Supporting only. |
| `inference` | Reasoned conclusion from several public facts, not directly stated. | Always marked and treated as tentative. |

When code and a paper conflict, the code wins for the actual submitted system. The most important instance is MindsAI: the paper discusses LongT5 as part of its broader ARC research lineage, while the 2025 Kaggle notebook and solution-code dataset point to `codet5_large` and `codet5_large_v3`.

## Review Rubric

Each deep dive uses the same structure:

| Section | Purpose |
|---|---|
| Snapshot | Score, team, sources, model stack, data stack, runtime constraints. |
| Architecture diagram | Static system composition. |
| Inference/training loop diagram | Dynamic path from task to submission. |
| Architectural bet | What the system assumes will scale or transfer. |
| Learned representation | How grids and transformations are represented. |
| Training and test-time adaptation | Offline training, TTFT/TTT, LoRA, active layers, or diffusion updates. |
| Candidate generation and scoring | Search, sampling, refinement, voting, and final selection. |
| Attention/KV/activation/gradient choices | Visible low-level systems choices. |
| Strengths, failure modes, open questions | Balanced evaluation. |
| Evidence ledger | Source-backed claims and gaps. |

## Claim Rules

- Exact implementation details require `code`, `paper`, or `writeup` evidence.
- Runtime constraints are taken from the notebook metadata, team source, or the competition description when visible.
- Results are reported from the official ARC table unless explicitly labeled as local, public leaderboard, or post-deadline.
- "Worked" and "failed" are used only when a team source reports that outcome. Otherwise the language is "likely", "appears", or "inference".
- JS-only or login-gated pages are recorded as gaps instead of reconstructed from memory.

## Validation Checklist

The final document set should satisfy these checks:

| Check | Status criterion |
|---|---|
| Leaderboard scores | Match ARC official table in comparison and snapshots. |
| Equal structure | Every deep dive has the same headings and table types. |
| Mermaid diagrams | Each diagram is fenced as `mermaid` and has a closed graph/flow. |
| Source conflict labels | MindsAI LongT5 vs CodeT5 conflict is explicit. |
| Inferred claims | Inferences are labeled and not mixed with code evidence. |
| Source gaps | Inaccessible or JS-only artifacts are listed as gaps. |
