# AutoModel B200 Post-Training Runbook

This runbook turns the post-training plan into repository artifacts. It chooses
NVIDIA NeMo AutoModel as the default training runner for cheap B200 experiments
and keeps TRL as the DPO fallback.

## Current Objects And Artifacts

- AutoModel configs live under `configs/automodel_b200/`.
- Dataset conversion lives in `scripts/automodel_prepare_datasets.py`.
- Budget calculation lives in `scripts/automodel_b200_budget.py`.
- TRL DPO fallback launcher lives in `scripts/trl_dpo_train.py`.
- Modal B200 launcher lives in `modal_apps/automodel_b200_post_training.py`.

No SFT, KD, DPO, OPD, or evaluation JSONL exports are current data artifacts
until reviewed candidate or admitted EVMBench tasks exist.

## Decision

Use AutoModel instead of Marin for the cheap path because the immediate target is
HF-compatible SFT/PEFT/KD artifacts on B200. AutoModel has first-class SFT,
LoRA/QLoRA, KD, Hugging Face checkpoint layouts, FP8 support, and distributed
training recipes. DPO remains a TRL `DPOTrainer` job until the exact AutoModel
DPO path is proven for this stack.

Important caveat: the confirmed quantization path here is FP8 and QLoRA/NF4, not
native NVFP4 training. Treat NVFP4 as a future compatibility gate, not as a claim
in experiment results.

## Model Order

Default student:

```text
Qwen/Qwen2.5-Coder-7B-Instruct
```

Use `configs/automodel_b200/qwen25_coder_7b_qlora_sft.yaml` first. This is the
fastest route to a useful HF adapter/checkpoint.

Stretch student:

```text
Qwen/Qwen2.5-Coder-32B-Instruct
```

Use `configs/automodel_b200/qwen25_coder_32b_qlora_sft.yaml` only after the 7B
run succeeds.

MoE stretch or teacher:

```text
Qwen/Qwen3-Coder-30B-A3B-Instruct
```

Do not make this the core student until a B200 smoke proves fit, throughput, and
checkpoint export. The current KD config uses `Qwen/Qwen2.5-Coder-32B-Instruct`
as teacher because the student and teacher should share a tokenizer for
AutoModel KD.

## Data Preparation

Convert reviewed SFT records into the simple columns consumed by AutoModel's
`ColumnMappedTextInstructionDataset`:

```bash
python scripts/automodel_prepare_datasets.py sft \
  --input data/post_training/detect_sft.jsonl \
  --output /data/automodel/sft_train.jsonl \
  --repo-root .
```

The output rows have:

```json
{"context":"...", "question":"...", "answer":"..."}
```

Convert preference pairs for TRL DPO:

```bash
python scripts/automodel_prepare_datasets.py dpo \
  --input data/post_training/detect_dpo.jsonl \
  --output /data/automodel/dpo_train.jsonl \
  --repo-root .
```

The output rows have:

```json
{"prompt":"...", "chosen":"...", "rejected":"..."}
```

Keep benchmark holdouts out of these files. Candidate-only rows must stay
explicitly labeled and should not be mixed into serious runs by default.

## Budget

Modal lists B200 at `$0.001736/sec`, which is `$6.2496/B200-hour`. At that rate,
`$1200` buys about `192.0` single-B200 hours.

Compute the current budget table:

```bash
python scripts/automodel_b200_budget.py --plan configs/automodel_b200/budget.yaml
```

The non-reserve phase plan consumes `144` B200-hours, about `$899.94`, leaving
about `48` B200-hours, about `$300.06`, under a `$1200` cap. This corrects the
earlier rough reserve estimate of `~68h`.

Use mostly `1x B200`:

- Stack smoke: `6h`, about `$37`.
- 7B SFT/PEFT: `20h`, about `$125`.
- KD: `24h`, about `$150`.
- DPO: `20h`, about `$125`.
- OPD rollout generation: `30h`, about `$187`.
- OPD training: `24h`, about `$150`.
- Evaluation: `20h`, about `$125`.
- Computed reserve: `~48h`, about `$300`.

Avoid `8x B200` except for a short smoke. At the base GPU rate, `8x B200` is
about `$50/hour`, so `$1200` lasts only about `24` wall-clock node-hours before
CPU, memory, region, and non-preemptible multipliers.

## Local Launch Commands

SFT/QLoRA:

```bash
automodel configs/automodel_b200/qwen25_coder_7b_qlora_sft.yaml
```

KD:

```bash
python - <<'PY'
import inspect
import subprocess
import nemo_automodel.recipes.llm.kd as kd

subprocess.run(
    [
        "torchrun",
        "--nproc-per-node",
        "1",
        inspect.getfile(kd),
        "-c",
        "configs/automodel_b200/qwen25_coder_7b_kd.yaml",
    ],
    check=True,
)
PY
```

DPO:

```bash
python scripts/trl_dpo_train.py \
  --config configs/automodel_b200/trl_dpo_qwen25_coder_7b.yaml
```

FP8 smoke after SFT/PEFT works:

```bash
automodel configs/automodel_b200/qwen25_coder_7b_fp8_smoke.yaml
```

## Modal Launch Commands

Dry-run the command that will execute remotely:

```bash
modal run modal_apps/automodel_b200_post_training.py --dry-run
```

Run 7B QLoRA SFT:

```bash
modal run modal_apps/automodel_b200_post_training.py \
  --config configs/automodel_b200/qwen25_coder_7b_qlora_sft.yaml \
  --mode automodel
```

Run KD:

```bash
modal run modal_apps/automodel_b200_post_training.py \
  --config configs/automodel_b200/qwen25_coder_7b_kd.yaml \
  --mode kd
```

Run TRL DPO:

```bash
modal run modal_apps/automodel_b200_post_training.py \
  --config configs/automodel_b200/trl_dpo_qwen25_coder_7b.yaml \
  --mode dpo
```

The Modal app mounts:

- `/root/.cache/huggingface` from Modal Volume `huggingface-cache`.
- `/data/automodel` from Modal Volume `automodel-b200-data`.
- `/outputs` from Modal Volume `automodel-b200-outputs`.

Set `AUTOMODEL_MODAL_GPU=B200:8` before `modal run` only for an explicit
multi-GPU smoke.

## Method Order

1. `W0`: SFT/PEFT on clean reviewed audit examples.
2. `KD`: AutoModel KD from a larger coder teacher into the 7B student.
3. `DPO`: TRL `DPOTrainer` on scored preference pairs.
4. `OPD`: generate student rollouts, teacher-correct them, then train on
   corrected continuations and preference pairs.
5. `FP8`: run only after the BF16/QLoRA baseline works.

## Rule Out For Now

- Full fine-tuning 30B/32B as the default path.
- Multi-node MoE training.
- 8-GPU OPD matrices.
- Continued pretraining.
- Native NVFP4 claims.
- Broad benchmark optimization beyond EVMBench plus small canaries.

## Publishable Artifact Path

- HF adapter/checkpoint for the best audit-tuned coder model.
- Clean SFT/KD/DPO/OPD dataset on HF with provenance and split metadata.
- GitHub repo with AutoModel Modal runner, data conversion, training configs,
  and evaluation scripts.
- Paper result: static SFT/KD/DPO versus OPD on smart-contract audit robustness
  under a fixed B200 budget.

## Source Notes

- AutoModel SFT/PEFT docs: <https://docs.nvidia.com/nemo/automodel/latest/recipes-e2e-examples/sft-peft>
- AutoModel KD docs: <https://docs.nvidia.com/nemo/automodel/latest/recipes-e2e-examples/knowledge-distillation>
- AutoModel FP8 docs: <https://docs.nvidia.com/nemo/automodel/latest/development/fp8-training>
- AutoModel custom dataset docs: <https://docs.nvidia.com/nemo/automodel/latest/datasets/columnmapped-dataset>
- TRL DPO docs: <https://huggingface.co/docs/trl/main/en/dpo_trainer>
- Modal pricing: <https://modal.com/pricing>

