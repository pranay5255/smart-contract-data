# AutoModel B200 Configs

These configs implement the cheap post-training path for smart-contract audit
models:

1. Convert reviewed EVMBench/ForestOfAudits records into local JSONL:

```bash
python scripts/automodel_prepare_datasets.py sft \
  --input data/post_training/detect_sft.jsonl \
  --output /data/automodel/sft_train.jsonl \
  --repo-root .

python scripts/automodel_prepare_datasets.py dpo \
  --input data/post_training/detect_dpo.jsonl \
  --output /data/automodel/dpo_train.jsonl \
  --repo-root .
```

2. Run the first artifact path on 1x B200:

```bash
automodel configs/automodel_b200/qwen25_coder_7b_qlora_sft.yaml
```

3. Run KD only after the SFT smoke works:

```bash
automodel configs/automodel_b200/qwen25_coder_7b_kd.yaml
```

4. Use TRL for DPO until AutoModel has a first-class DPO recipe for this stack:

```bash
python scripts/trl_dpo_train.py --config configs/automodel_b200/trl_dpo_qwen25_coder_7b.yaml
```

The configs assume local data is mounted at `/data/automodel` and checkpoints go
to `/outputs/automodel`. On Modal, the runner in
`modal_apps/automodel_b200_post_training.py` mounts those as volumes.

Budget math is computed, not handwritten:

```bash
python scripts/automodel_b200_budget.py --plan configs/automodel_b200/budget.yaml
```

