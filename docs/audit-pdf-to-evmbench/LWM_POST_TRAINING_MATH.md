# LWM Post-Training Math For EVM Interaction Simulation

This document defines a post-training recipe for a language world model (LWM)
whose only job is to simulate smart-contract interaction outcomes. It is meant
to complement `POST_TRAINING_RECIPES.md`, which covers detect-mode SFT, DPO,
GRPO, and rollout records for audit agents. This document does not train the
audit agent. It trains and evaluates only the simulator.

The design follows the broad Qwen-AgentWorld pattern: continued pretraining
injects world-model knowledge, supervised finetuning activates next-state
prediction, and verifier-guided RL improves simulation fidelity. For this
project, the verifier is an exact local EVM executor such as `revm`, Foundry, or
Anvil. The LWM should never be treated as final proof of an exploit or state
transition.

## Relationship To Existing Post-Training Recipes

The existing post-training docs define agent-facing records:

- `evmbench_detect_rl_tasks.jsonl`: task metadata for detect-mode environments.
- `detect_rollouts.jsonl`: audit-agent attempts and final detect scores.
- `detect_sft.jsonl`: supervised audit-report examples.
- `detect_dpo.jsonl`: preferred and rejected audit reports.
- `detect_grouped_rollouts.jsonl`: grouped audit-agent samples.

Those records are still correct for audit-agent training. The LWM needs a
different source of truth:

```text
exact EVM transition records
```

An LWM row is not "write the audit report." It is:

```text
given source + state + history + next action, predict the exact next observation
```

The LWM can later be used by an audit agent, but the LWM training target is
simulator fidelity, not finding quality.

## Core Goal

Given contract source, ABI, deployment context, decoded state, interaction
history, and a proposed next transaction or call, predict the next observation:

```text
contracts + state + history + action -> next interaction outcome
```

The model should predict structured state-transition facts:

- success or revert
- revert reason or custom error
- return values
- emitted events
- internal and external call trace summary
- token and native balance deltas
- decoded storage deltas
- invariant labels
- confidence and uncertainty

The model should not produce free-form explanations as its primary output.
Prose can be attached as diagnostics, but exact structured fields are the
training and evaluation target.

## Formal Environment

Let an exact EVM environment be:

```text
M = (S, A, T, O, G)
```

where:

- `S` is exact EVM state: bytecode, storage, balances, nonces, block context,
  deployed addresses, and chain configuration.
- `A` is a structured action space of calls, transactions, block mutations, and
  controlled test-harness mutations.
- `T(s_{t+1} | s_t, a_t)` is the transition kernel. For a pinned local EVM and
  fixed scenario seed, it is deterministic.
- `O` maps exact transitions into structured observations.
- `G` maps exact transitions into auxiliary labels such as invariant status,
  profit, coverage, and branch hits.

The exact executor is:

```text
E(s_t, a_t) = (s_{t+1}, o_{t+1}, g_{t+1})
```

The LWM parameterized by `theta` models:

```text
p_theta(y_{t+1} | c_t, a_t)
```

with:

```text
c_t = encode(source, abi, storage_layout, decoded_state_t, semantic_state_t, h_t)
h_t = [(a_0, o_1), ..., (a_{t-1}, o_t)]
y_{t+1} = encode(o_{t+1}, selected_delta(s_t, s_{t+1}), g_{t+1})
```

The LWM predicts `y_{t+1}`. The exact executor remains the source of truth.

## Action Schema

Actions should be machine-parseable. A small action language keeps the task
learnable and makes exact replay easy.

```json
{
  "actor": "attacker",
  "kind": "tx",
  "target": "Vault",
  "function": "withdraw",
  "args": ["1000000000000000000"],
  "value": "0",
  "block_delta": 1,
  "timestamp_delta": 12,
  "gas_limit": null
}
```

Useful action kinds:

- `eth_call`: static or read-only call.
- `tx`: state-changing transaction.
- `deploy`: deploy a contract or mock.
- `warp`: change timestamp or block number.
- `deal`: set ETH or token balances in a test harness.
- `oracle_update`: mutate a mock oracle.
- `prank`: change caller context in a test harness.

Do not let this LWM invent shell commands. Shell command simulation is a
separate world-modeling problem.

## Observation Schema

The target should be a constrained JSON object:

```json
{
  "status": "revert",
  "revert": {
    "kind": "custom_error",
    "selector": "0x12345678",
    "name": "InsufficientShares",
    "args": ["attacker", "1000000000000000000"]
  },
  "return_values": [],
  "events": [],
  "calls": [
    {
      "depth": 0,
      "from": "attacker",
      "to": "Vault",
      "function": "withdraw",
      "status": "revert"
    }
  ],
  "balance_deltas": {},
  "storage_deltas": [],
  "decoded_state_deltas": [],
  "invariants": {
    "vault_solvency": "unchanged",
    "attacker_profit": "false"
  },
  "coverage": {
    "new_edges": 0,
    "new_functions": []
  },
  "confidence": 0.76
}
```

Keep three state views:

- Exact state: raw slots, bytecode, balances, nonces, logs, returndata.
- Decoded state: named variables, reserves, debt, shares, allowances, roles.
- Semantic state: solvent, stale oracle, undercollateralized, attacker profit.

The exact state is for the verifier. The decoded and semantic views are for the
LWM input and eval diagnostics.

## LWM Transition Record

Suggested file:

```text
evm_lwm_transitions.jsonl
```

Example:

```json
{
  "record_id": "txworld-00000001",
  "scenario_id": "vault-toy-001",
  "source": "exact_evm_trace",
  "split": "train",
  "source_ref": "contracts/Vault.sol",
  "compiler": {
    "solc": "0.8.24",
    "optimizer": true,
    "runs": 200
  },
  "pre_state_ref": "states/s000001.json",
  "decoded_state": {},
  "semantic_state": {},
  "history_ref": "histories/h000001.json",
  "action": {},
  "exact_observation": {},
  "post_state_ref": "states/s000002.json",
  "executor": {
    "name": "revm",
    "version": "pinned-version",
    "chain_config": "mainnet-ish-local"
  },
  "provenance": {
    "repo": "example/repo",
    "commit": "abcdef",
    "generated_by": "trace-generator-v1"
  }
}
```

This should stay separate from `detect_rollouts.jsonl`. Detect rollouts train or
evaluate agents. LWM transitions train or evaluate simulator dynamics.

## Stage 0: Exact Executor And Trace Generator

Before training, build the verifier.

The executor must:

- compile source deterministically
- deploy scenario contracts
- assign actor balances
- run typed actions
- record raw and decoded deltas
- compute invariant labels
- content-hash every state and transition

For a trace of length `T`, collect:

```text
tau = (s_0, a_0, o_1, s_1, ..., a_{T-1}, o_T, s_T)
```

From each trace produce one-step examples:

```text
x_t = (source, abi, storage_layout, decoded_state_t, semantic_state_t, h_t, a_t)
y_t = exact_observation_{t+1}
```

This stage determines the ceiling of the whole project. If the executor is not
stable, post-training optimizes against noise.

## Stage 1: Continued Pretraining

Purpose: teach the base model the language and regularities of Solidity/EVM
worlds before asking it to predict transitions exactly.

Corpus:

- Solidity source
- ABIs
- storage layouts
- deployment scripts
- Foundry and Hardhat tests
- exact traces
- event logs
- call traces
- invariant definitions
- split-safe audit findings and exploit writeups

Objective:

```text
L_CPT(theta) = - E_{z ~ D_corpus} sum_i log p_theta(z_i | z_<i)
```

This is plain next-token modeling. It must not contain held-out benchmark
answers or gold findings for evaluation audits.

Recommended mix:

```text
40% Solidity/source/tests
25% exact traces and logs
15% ABI/storage/invariant schemas
10% security reports and exploit explanations
10% general code/math retained from the base distribution
```

The percentages are starting values. The important part is that trace-like data
is present before transition SFT begins.

## Stage 2: Structured Transition SFT

Purpose: train the LWM to emit the exact next observation for a given state and
action.

Dataset:

```text
D_SFT = {(x_i, y_i)}_{i=1}^N
```

Base objective:

```text
L_SFT(theta) = - E_{(x,y) ~ D_SFT} log p_theta(y | x)
```

Because the output is structured, track a factorized diagnostic loss:

```text
L_struct =
  lambda_status L_status
+ lambda_ret    L_return
+ lambda_evt    L_events
+ lambda_call   L_calls
+ lambda_bal    L_balances
+ lambda_store  L_storage
+ lambda_inv    L_invariants
+ lambda_json   L_json
```

Field losses:

```text
L_status = CE(status, status_hat)
L_inv    = BCE(v, v_hat) for multi-label invariant vector v
L_json   = 1[invalid_json]
```

For numeric deltas:

```text
normalized_abs_error(a, b) = min(1, |a - b| / max(1, |a|))
```

For write sets:

```text
precision = |W_hat intersect W_star| / max(1, |W_hat|)
recall    = |W_hat intersect W_star| / max(1, |W_star|)
F1_write  = 2 * precision * recall / max(epsilon, precision + recall)
L_storage = 1 - F1_write + value_error_on_matched_slots
```

For events:

```text
event_score = alpha * event_F1 + (1 - alpha) * order_score
```

Do not rely on training loss alone. SFT is useful only if exact-field evals
improve.

## Stage 3: Verifier-Guided Correction

Purpose: expose the LWM to its own mistakes and train it to correct them against
the exact executor.

Loop:

```text
1. Sample x = (context, action) from train scenarios.
2. Generate y_hat ~ p_theta(. | x).
3. Replay action in exact EVM to obtain y_star.
4. Compare y_hat with y_star.
5. Add correction records emphasizing wrong fields.
```

Correction objective:

```text
L_VGC(theta) =
  - E_{(x, y_star) ~ D_correction} w(x, y_star) log p_theta(y_star | x)
```

Hard mistakes get larger weights:

```text
w = 1
  + beta_status 1[wrong_status]
  + beta_profit 1[wrong_profit_sign]
  + beta_inv    1[missed_invariant]
  + beta_store  1[large_state_error]
```

This stage is critical for real audit repos, because the most damaging simulator
errors are plausible false positives.

## Stage 4: Preference Training For Closer Predictions

For the same input `x`, let:

- `y_plus` be the exact observation or a prediction closer to exact truth.
- `y_minus` be a worse prediction.

Define distance to exact truth:

```text
D(y, y_star) =
  w_status 1[status != status_star]
+ w_ret    d_ret(y, y_star)
+ w_evt    (1 - F1_events)
+ w_call   d_tree(call_trace, call_trace_star)
+ w_bal    d_balance
+ w_store  d_storage
+ w_inv    (1 - F1_invariants)
+ w_json   1[invalid_json]
```

Preference:

```text
y_plus preferred to y_minus iff D(y_plus, y_star) < D(y_minus, y_star)
```

DPO-style objective:

```text
L_DPO(theta) =
  - E log sigma(
      beta [
        log p_theta(y_plus | x) - log p_theta(y_minus | x)
      ]
      - beta [
        log p_ref(y_plus | x) - log p_ref(y_minus | x)
      ]
    )
```

This is a practical bridge between SFT and full RL. It teaches "closer to exact
EVM" without requiring a high-variance rollout optimizer.

## Stage 5: RL For Simulator Fidelity

The LWM action is its emitted prediction `y_hat`. The reward is not exploit
success. The reward is transition fidelity.

Reward:

```text
r_LWM(x, y_hat, y_star) = 1 - D_norm(y_hat, y_star)
D_norm = D / D_max
```

KL-regularized objective:

```text
J(theta) =
  E_{x ~ D, y_hat ~ p_theta(. | x)}
    [r_LWM(x, y_hat, y_star)]
  - eta KL(p_theta(. | x) || p_ref(. | x))
```

For group-relative optimization, sample `K` predictions for the same `x`:

```text
{y_hat_1, ..., y_hat_K} ~ p_theta(. | x)
r_k = r_LWM(x, y_hat_k, y_star)
A_k = (r_k - mean(r_1..r_K)) / (std(r_1..r_K) + epsilon)
```

Optimize the likelihood of above-average predictions and suppress below-average
predictions, with KL regularization to the reference model.

Use this stage only after SFT and verifier-guided correction are stable.

## Stage 6: Calibration And Abstention

A useful simulator should know when not to be trusted.

Let:

```text
c_hat in [0, 1]
z = 1[D(y_hat, y_star) <= tau]
```

Brier loss:

```text
L_brier = E (c_hat - z)^2
L_calibrated = L_SFT + lambda_cal L_brier
```

Expected calibration error:

```text
ECE = sum_{b=1}^B |B_b| / n * |acc(B_b) - conf(B_b)|
```

Selective risk:

```text
coverage(gamma) = P(c_hat >= gamma)
risk(gamma) = E[D_norm(y_hat, y_star) | c_hat >= gamma]
```

The production simulator should support:

```text
predict
predict_with_confidence
abstain_and_request_exact_replay
```

## LWM-Only Evals

These evals measure simulator fidelity. They do not measure audit-agent
performance.

### One-Step Transition Fidelity

Input:

```text
x_t = context + action
```

Target:

```text
y_star = exact next observation
```

Metrics:

- JSON validity rate.
- Status accuracy: `success`, `revert`, `out_of_gas`, `invalid`.
- Revert selector accuracy.
- Revert reason or custom error exact match.
- Return value exact match.
- Event name F1.
- Event argument exact match.
- Balance-delta exact match.
- Storage write-set precision, recall, and F1.
- Decoded variable delta accuracy.
- Internal and external call-trace tree similarity.
- Invariant label precision, recall, and F1.

Primary score:

```text
Score_1step = 1 - mean_i D_norm(y_hat_i, y_star_i)
```

Keep the field breakdown. A single aggregate score hides dangerous errors.

### Multi-Step Rollout Fidelity

Evaluate a fixed action sequence:

```text
a_0, ..., a_{T-1}
```

Teacher-forced rollout:

```text
history uses exact prior observations
```

Free rollout:

```text
history uses model-predicted prior observations
```

Metrics:

```text
first_divergence = min t such that D(y_hat_t, y_star_t) > tau
survival@k = P(first_divergence > k)
rollout_score_T = 1 - (1/T) sum_t D_norm(y_hat_t, y_star_t)
```

State divergence:

```text
StateDiv_t =
  alpha (1 - F1_storage_write_set_t)
+ beta  normalized_balance_error_t
+ gamma decoded_state_error_t
+ delta invariant_disagreement_t
```

This eval catches compounding simulator errors.

### Counterfactual Generalization

Hold out combinations of:

- caller
- `msg.value`
- function arguments
- block timestamp
- block number
- oracle price
- token liquidity
- approval amount
- share or reserve ratio

Metric:

```text
Score_counterfactual =
  1 - mean_{x in D_counterfactual} D_norm(y_hat, y_star)
```

Report performance by perturbation type.

### Hard-State Evaluation

Create states near discontinuities:

- allowance exactly zero
- balance exactly equal to withdrawal amount
- rounding boundary
- liquidation threshold boundary
- stale-oracle threshold
- paused or unpaused role boundary
- reentrancy lock active
- proxy implementation changed

Metrics:

- boundary status accuracy
- off-by-one numeric error rate
- branch flip accuracy
- invariant flip accuracy

Formula:

```text
branch_flip_accuracy =
  P(status_hat(a_epsilon_minus) != status_hat(a_epsilon_plus)
    and matches exact flip)
```

### Profit And Invariant Signal Accuracy

Profit sign:

```text
profit = net_worth_attacker_after - net_worth_attacker_before
profit_sign_accuracy = P(sign(profit_hat) = sign(profit_star))
```

Profit magnitude:

```text
profit_rel_error = |profit_hat - profit_star| / max(1, |profit_star|)
```

Invariant agreement:

```text
F1_invariant = 2PR / (P + R)
```

Sequence ranking:

```text
recall@K =
  (# exact-positive sequences included in top-K by LWM score)
  / (# exact-positive sequences in full candidate pool)
```

For scaling, high recall matters more than high precision. The simulator can be
noisy if it rarely filters out true positives.

### Abstention And Calibration

Metrics:

- ECE
- Brier score
- selective risk at fixed coverage
- coverage at fixed risk

Operational target:

```text
At 80% coverage, model error should be materially lower than full-set error.
```

Low-confidence transitions should go to exact replay.

### Efficiency As A Simulator Filter

Given candidate sequences:

```text
C = {c_1, ..., c_N}
```

The LWM scores all `N`, exact replay runs only top `K`.

Metrics:

```text
replay_savings = 1 - K/N
positive_recall@K = positives_in_top_K / total_positives
enrichment@K = precision@K / base_positive_rate
```

This is the key scaling eval. The LWM succeeds if it preserves high recall while
reducing exact replay volume.

### Robustness Evaluation

Separate eval buckets:

- proxy and delegatecall flows
- ERC777/ERC1363 callbacks
- fee-on-transfer tokens
- rebasing tokens
- non-standard ERC20 return values
- flash-loan callbacks
- CREATE2 addresses
- fallback and receive behavior
- low-level calls
- try/catch
- assembly-heavy contracts
- chain-specific precompiles

Report per-bucket scores. Do not average them away.

## Splits

Random row splits are not enough.

### Contract-Held-Out

Train and eval contracts are disjoint.

### Repo-Held-Out

All contracts from an audit repo are held out. This should be the main
benchmark.

### Protocol-Family-Held-Out

Hold out whole categories:

- lending
- AMM
- vault
- bridge
- staking
- NFT marketplace
- derivatives

### Temporal Holdout

Train on older repos and evaluate on newer repos.

### Vulnerability-Held-Out

Hold out specific mechanisms:

- read-only reentrancy
- donation or inflation attack
- stale oracle
- incorrect share rounding
- unchecked callback
- access-control bypass

Use this as a research eval, not the only production gate.

## Suggested Acceptance Gates

### v0 Toy Contracts

- JSON validity: `>= 99%`
- status accuracy: `>= 95%`
- event F1: `>= 90%`
- invariant F1: `>= 90%`
- survival@5 free rollout: `>= 80%`

### v1 Real Unit-Test Contracts

- JSON validity: `>= 99%`
- status accuracy: `>= 90%`
- revert selector accuracy: `>= 80%`
- storage write-set F1: `>= 75%`
- invariant F1: `>= 80%`
- ECE: `<= 0.10`
- positive recall@top-10% for invariant-violating sequences: `>= 95%`

### v2 Real Audit Repos

- status accuracy: `>= 85%`
- profit sign accuracy: `>= 85%`
- invariant F1: `>= 75%`
- survival@3 free rollout: `>= 70%`
- replay savings: `>= 80%`
- positive recall after filtering: `>= 95%`

The v2 thresholds tolerate imperfect local details only if the model preserves
high recall for security-relevant transitions.

## Training Curriculum

Scale complexity gradually:

```text
1. arithmetic and storage toy contracts
2. ERC20/ERC721 standards and edge cases
3. vaults, AMMs, staking, lending mini-protocols
4. CTF and benchmark vulnerable contracts
5. Foundry test traces from real repos
6. historical exploit reproductions
7. admitted EVMBench/audit repos with safe splits
```

For each tier, generate:

- random valid calls
- boundary-value calls
- invariant-targeted calls
- revert-targeted calls
- mutation-based counterfactuals
- model-generated predictions corrected by exact replay

Balance the dataset. If most transitions are simple success cases, the model
will miss the important failures.

## Production Inference Contract

The deployed LWM should expose:

```text
predict_one_step(context, action) -> prediction
predict_rollout(context, actions) -> predictions
score_sequence(context, actions) -> scalar + labels
estimate_uncertainty(context, action) -> confidence
request_exact_replay_if_needed(prediction) -> bool
```

The orchestration layer should cache:

```text
cache_key = hash(chain_config, source_hash, pre_state_hash, action)
```

If exact replay exists, use it. If not, the LWM can provide a provisional
prediction and confidence.

## Common Failure Modes

- The model predicts plausible Solidity behavior but misses exact EVM revert
  behavior.
- It gets event names right but event args wrong.
- It predicts ERC20 transfers but misses fee-on-transfer or rebasing behavior.
- It misses delegatecall storage context.
- It treats view calls as pure even when they read changed state.
- It hallucinates decoded variable names not present in the storage layout.
- It predicts exploit profit without accounting for approvals, liquidity,
  slippage, or debt repayment.
- It is accurate on single calls but diverges during multi-step rollouts.

Each failure mode should have a targeted eval bucket and correction dataset.

## Leakage And Safety Controls

- Do not train on gold audit findings for held-out evaluation audits.
- Do not include exploit answer keys in simulator contexts for held-out tasks.
- Keep source repo, exact traces, generated predictions, and gold labels split
  by audit identity.
- Treat exact replay as the only proof path for exploit feasibility.
- Mark model predictions as provisional unless verified.
- Store all transformations and prompt versions in provenance records.

## Recommended Build Order

1. Implement exact trace schema and executor-backed trace generation.
2. Build one-step eval harness before training.
3. Train a small SFT baseline on toy and benchmark contracts.
4. Add verifier-guided correction from model mistakes.
5. Add calibration and abstention evals.
6. Add multi-step and sequence-filter evals.
7. Scale to real audit repos only after simulator metrics are stable.

The decisive metric is not whether the LWM sounds like an auditor. The decisive
metric is whether it preserves exact-replay positives while reducing the number
of exact EVM replays needed.

## References

- Qwen-AgentWorld: Language World Models for General Agents, arXiv:2606.24597. The relevant transferable pattern is CPT for world-model knowledge, SFT for next-state prediction, and RL with rubric/rule rewards for simulation fidelity.
- `POST_TRAINING_RECIPES.md` for existing audit-agent SFT, DPO, GRPO, and rollout record shapes.
- `POST_TRAINING_DATASET_SOURCES.md` for source pools and leakage boundaries.
