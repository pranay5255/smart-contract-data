# Training a 1B-3B smart contract vulnerability detection model in 60 days

A specialized code model for smart contract security can achieve **31-36% precision with 60-88% recall** through careful adaptation of OLMo 3's methodology—significantly outperforming prompt-only approaches (4-22% precision). The optimal path involves **StarCoder2-3B or Qwen2.5-Coder-1.5B** as base models, a three-stage training pipeline (continued pretraining → SFT → DPO), and strategic compute allocation with **RTX 4090 for 30+ ablations** and **8xH100 for final training**. This report provides the complete technical blueprint.

---

## OLMo 3's core innovations apply directly to small models

OLMo 3's three-stage training pipeline—pretraining on **5.9T tokens**, mid-training on **100B high-quality tokens**, and post-training via SFT+DPO+RLVR—scales down effectively to 1B-3B models with key adaptations.

**Mid-training data composition** (the critical stage for domain adaptation) uses a carefully optimized mix: **28% web pages, 20% code, 19% math, 14% Q&A, 8% reasoning traces, 6% instruction data, 5% academic PDFs**. For smart contract specialization, this translates to upsampling Solidity code **10-50x** while maintaining a replay buffer of **20-30% general code** to prevent catastrophic forgetting. The quality-aware upsampling strategy—where the **top 5% of data receives multiple copies** while lower-quality content appears once—proves essential for small model performance.

**Training hyperparameters** that transfer from OLMo 3: peak learning rate of **3×10⁻⁴** with cosine decay to 10%, **2,000 warmup steps**, and batch size warmup from 1024 to 4096 by ~500B tokens seen. For 1B models, critical batch size reaches 2048 by 168B tokens—smaller models can use single training runs without the multi-seed averaging that benefits 7B+ models.

**Post-training pipeline** follows: (1) SFT for 2 epochs on task-formatted data, (2) DPO with "delta learning" using contrastive pairs from strong/weak models (e.g., GPT-4 chosen vs GPT-3.5 rejected), and (3) optional RLVR with verifiable rewards. For vulnerability detection, test case verification provides binary correctness signals analogous to OLMo 3's code reward system.

---

## SmartBugs-curated provides the evaluation gold standard

The smart contract vulnerability landscape centers on **SmartBugs-curated** (143 contracts, 208 vulnerabilities across 9 DASP categories) for benchmarking and **SmartBugs-wild** (47,398 real contracts) for scale evaluation. The SWC Registry defines **37 weakness types** (SWC-100 through SWC-136), while OWASP's 2025 Top 10 reflects current attack patterns—**access control vulnerabilities caused $953M in losses** in 2024 alone.

**Benchmark scores to target**: Traditional static analysis tools achieve ~27% precision (Mythril best-in-class); fine-tuned LLMs reach **31-36% precision** with careful optimization; GPT-4 out-of-the-box achieves only 22% precision despite 88% recall. The precision-recall tradeoff is critical—**high false positive rates (4-20% precision) make LLMs impractical** without fine-tuning.

| Benchmark | Size | Annotation Level | Primary Use |
|-----------|------|------------------|-------------|
| SmartBugs-curated | 143 contracts, 208 vulns | Line-level | Gold standard evaluation |
| SmartBugs-wild | 47,398 contracts | Contract-level | Scale testing |
| SolidiFI | 9,369 injected bugs | Function-level | Tool comparison |
| DeFiHackLabs | 550+ incidents | Exploit-level | Real-world validation |

**Dataset splitting requirements**: Split at project/contract level (not function level) to avoid data leakage. Use **70/20/10** train/val/test with stratified sampling by CWE type, ensuring **100+ samples per vulnerability category** for multi-class training. Temporal splits (older CVEs for training, recent for testing) provide the most realistic evaluation.

---

## StarCoder2-3B emerges as the optimal base model

Among code-specialized models in the 0.5B-3B range, **StarCoder2-3B** offers the best combination of training transparency and fine-tuning infrastructure, while **Qwen2.5-Coder-1.5B** provides superior raw performance with less documentation.

| Model | Params | HumanEval | Training Transparency | Solidity Support | License |
|-------|--------|-----------|----------------------|------------------|---------|
| **StarCoder2-3B** | 3B | 31% | ⭐⭐⭐⭐⭐ (full data tracing) | Via fine-tuning | OpenRAIL-M |
| **Qwen2.5-Coder-1.5B** | 1.5B | 61% | ⭐⭐ (paper only) | Likely (92 langs) | Apache 2.0 |
| DeepSeek-Coder-1.3B | 1.3B | 34%/65% | ⭐⭐ | Unknown | Commercial OK |
| SmolLM2-1.7B | 1.7B | N/A | ⭐⭐⭐⭐ | Limited | Apache 2.0 |

**Critical finding**: No model under 3B has confirmed Solidity in pretraining data. Community fine-tuned versions exist (`yoniebans/starcoder2-3b-qlora-solidity`), but you'll need **continued pretraining on Solidity** regardless of base model choice.

**For ablations**, use **TinyLlama-1.1B** or **SmolLM2 series**—both have excellent training transparency with intermediate checkpoints every 500B tokens, enabling systematic scaling law studies.

---

## Three-tier data mixing balances specialization and capability retention

The optimal data strategy follows OLMo 3's quality-tiered approach adapted for low-resource domain specialization.

**Continued pretraining mix (100-200B tokens)**:
- 50% general high-quality code (StarCoder data, filtered)
- 30% Solidity code (Etherscan verified contracts, GitHub)
- 10% code-related natural language (documentation, audit reports)
- 10% math/reasoning traces (capability retention)

**Fine-tuning mix for vulnerability detection**:
- 40% vulnerability-labeled Solidity (~5K-10K contracts from SmartBugs + CVE data)
- 25% synthetic vulnerability pairs (HexaCoder-style oracle-guided generation)
- 20% clean non-vulnerable contracts (negative examples)
- 10% general code instruction data (forgetting prevention)
- 5% security documentation (CWE descriptions, audit methodology)

**Synthetic data generation** via HexaCoder approach: (1) generate vulnerable code with GPT-4 few-shot prompting, (2) validate with static analyzer (Slither/Mythril), (3) generate fixed versions, (4) re-validate fixes. This achieves **87% success rate** in producing validated vulnerability/fix pairs. For Solidity specifically, tools like SolidiFI enable systematic bug injection for training data augmentation.

**Replay strategy**: During fine-tuning, maintain **10-20% of each batch from general code** data. Smart-LLaMA-DPO research shows removing continued pretraining drops integer overflow F1 from **88.29% to 53.01%**—replay is essential.

---

## RTX 4090 setup enables rapid ablation iteration

The RTX 4090 (24GB VRAM) supports **4-bit QLoRA training of up to 7B models** with the right optimization stack.

**Unsloth configuration** (2x speed, 60-70% memory reduction):
```python
from unsloth import FastLanguageModel

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="bigcode/starcoder2-3b",
    max_seq_length=2048,
    load_in_4bit=True,
    dtype=None,  # Auto-detect BF16
)

model = FastLanguageModel.get_peft_model(
    model,
    r=16,  # LoRA rank (start here, increase to 32-64 if underfitting)
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", 
                    "gate_proj", "up_proj", "down_proj"],
    lora_alpha=32,  # 2x rank is typical
    lora_dropout=0,
    use_gradient_checkpointing="unsloth",  # Extra 30% memory savings
    use_rslora=True,  # Rank-stabilized LoRA for stability
)
```

**Maximum batch sizes on RTX 4090 (seq_len=2048)**:

| Model | 4-bit QLoRA | BF16 LoRA |
|-------|-------------|-----------|
| 1B | 8-16 | 4-8 |
| 3B | 2-4 | 1-2 |
| 7B | 1-2 | N/A |

**Experiment tracking**: Weights & Biases sweeps for parallel hyperparameter search across 100+ configurations:
```yaml
method: bayes
metric: {name: eval_f1, goal: maximize}
parameters:
  learning_rate: {distribution: log_uniform_values, min: 1e-5, max: 1e-3}
  lora_r: {values: [8, 16, 32, 64]}
  batch_size: {values: [1, 2, 4]}
  gradient_accumulation_steps: {values: [4, 8, 16]}
early_terminate: {type: hyperband, min_iter: 100}
```

---

## 8xH100 final training uses FSDP with hybrid sharding

For the final 1B-3B training runs, **FSDP with HYBRID_SHARD** provides optimal efficiency on single-node 8xH100.

```yaml
# accelerate_config.yaml
distributed_type: FSDP
fsdp_config:
  fsdp_sharding_strategy: HYBRID_SHARD
  fsdp_auto_wrap_policy: TRANSFORMER_BASED_WRAP
  fsdp_backward_prefetch: BACKWARD_PRE
  fsdp_forward_prefetch: true
  fsdp_state_dict_type: SHARDED_STATE_DICT
  fsdp_use_orig_params: true
mixed_precision: bf16
num_processes: 8
```

**H100 vs 4090 performance**: Single H100 is **2-3x faster** than RTX 4090; 8xH100 with NVLink provides **5-10x throughput** for multi-GPU training versus PCIe-limited 4090 setups. Full BF16 training of 3B models requires ~20GB per GPU with FSDP—well within H100's 80GB.

---

## Post-training pipeline converts detection to instruction format

**SFT data format** (Alpaca-style for single-turn analysis):
```json
{
  "instruction": "Analyze this Solidity function for vulnerabilities. Report: (1) vulnerability type, (2) CWE ID, (3) vulnerable line numbers, (4) root cause explanation.",
  "input": "[Solidity code snippet]",
  "output": "Vulnerability: Reentrancy\nCWE: CWE-841\nLines: 12-15\nExplanation: The external call on line 12 occurs before state update on line 15, allowing recursive calls to drain funds..."
}
```

**SFT hyperparameters for 1B-3B models** (from arXiv 2412.13337):
- Learning rate: **2e-5** (lower is safer)
- Effective batch size: **3,840-7,680** (larger batches outperform small)
- Epochs: **1-2** (often 1 is sufficient)
- No warmup needed (research shows omitting warmup doesn't hurt)
- Constant or cosine LR schedule (both work equally well)

**DPO for precision improvement** constructs preference pairs:
- **Chosen**: Accurate vulnerability identification with CWE type, line numbers, remediation
- **Rejected**: False negatives or vague explanations

DPO hyperparameters: β=**0.1** (start here), learning rate **5e-7** (1/10th to 1/100th of SFT), 1 epoch.

---

## The 60-day timeline divides into five distinct phases

| Phase | Days | Compute | Activities |
|-------|------|---------|------------|
| **Setup & Data** | 1-10 | 4090 | Data pipeline, tokenization, SmartBugs integration, Solidity collection |
| **Small Ablations** | 11-25 | 4090 | 30M-100M experiments (20 runs), hyperparameter search, data mix optimization |
| **Medium Ablations** | 26-40 | 4090 | 500M experiments (10 runs), validate scaling predictions |
| **Final Training** | 41-55 | 8xH100 | 1B-3B full training (3 seeds), SFT + DPO pipeline |
| **Evaluation** | 56-60 | 4090/H100 | SmartBugs benchmarking, documentation, ablation analysis |

**Go/no-go checkpoints**:
- **Day 25**: Are 100M model losses tracking scaling law predictions? Is data pipeline stable?
- **Day 40**: Does 500M performance justify scaling to 1B+? Are compute estimates accurate?

**Compute budget estimate**:

| Component | H100 Hours | RTX 4090 Hours | Cost (H100 @ $5/hr) |
|-----------|------------|----------------|---------------------|
| Small ablations | 40-80 | 120-240 | $200-400 |
| Medium ablations | 120-200 | 400-600 | $600-1,000 |
| Final training (3 seeds) | 200-400 | — | $1,000-2,000 |
| **Total** | **360-680** | **520-840** | **$1,800-$3,400** |

---

## Scaling law predictions enable confident resource allocation

**Chinchilla-optimal token counts** for target models:
- 1B parameters → **20B tokens**
- 2B parameters → **40B tokens**  
- 3B parameters → **60B tokens**

**Training time estimates (compute-optimal)**:

| Model | Tokens | RTX 4090 | H100 | 8xH100 |
|-------|--------|----------|------|--------|
| 100M | 2B | 8-12 hrs | 2-4 hrs | — |
| 500M | 10B | 40-60 hrs | 12-20 hrs | — |
| 1B | 20B | 80-120 hrs | 25-40 hrs | 4-6 hrs |
| 3B | 60B | N/A | 85-130 hrs | 12-18 hrs |

**What transfers from small ablations**: Data quality effects, learning rate schedules (with batch size scaling), tokenizer performance, relative ordering of data mixture compositions, architecture hyperparameters.

**What doesn't transfer**: Emergent abilities (appear only above scale thresholds), absolute benchmark scores, exact convergence dynamics. Accept that **some capabilities cannot be predicted from small-scale ablations**—reserve 20% compute buffer for unexpected findings.

---

## Concrete configuration recommendations

**Phase 1: 100M ablation model (Days 11-20)**
```python
# Architecture (GPT-2-style, scaled)
config = {
    "vocab_size": 50257,
    "n_positions": 2048,
    "n_embd": 640,
    "n_layer": 10,
    "n_head": 10,
}
# Training: 2B tokens, ~10 hours on 4090
# Sweep: learning_rate, data_mix_ratio, lora_rank
```

**Phase 2: 500M validation model (Days 26-35)**
```python
config = {
    "n_embd": 1280,
    "n_layer": 24,
    "n_head": 20,
}
# Training: 10B tokens, ~50 hours on 4090
# Validate: Do scaling predictions from 100M hold?
```

**Phase 3: 1B-3B final training (Days 41-55)**
```python
# Use StarCoder2-3B or Qwen2.5-Coder-1.5B base
# Continued pretraining: 100B tokens
# SFT: 10K-50K samples, 2 epochs
# DPO: 5K-20K preference pairs, 1 epoch
```

---

## Evaluation metrics define success criteria

**Primary metrics**:
- **Precision**: Target >35% (vs 22% GPT-4 baseline)
- **Recall**: Target >70% (vs 88% GPT-4, acceptable trade-off)
- **F1-score**: Target >0.45 macro-averaged across vulnerability types
- **False positive rate**: Target <65% (critical for practical adoption)

**Per-vulnerability targets** (based on literature):
- Reentrancy: F1 >0.80 (well-studied)
- Integer overflow: F1 >0.75
- Access control: F1 >0.60 (most impactful)
- Unchecked calls: F1 >0.70

**Evaluation protocol**: Run on SmartBugs-curated (143 contracts) for direct comparison with published results; validate on DeFiHackLabs recent incidents for real-world relevance.

---

## Conclusion: the path forward

The 60-day timeline is feasible with disciplined execution. **Start immediately** with data pipeline construction—collecting verified Solidity contracts from Etherscan, integrating SmartBugs datasets, and building the synthetic data generation pipeline using Slither for oracle validation. Run **30+ ablations on RTX 4090** in weeks 2-5 to establish robust scaling law predictions before committing 8xH100 compute to final training.

The choice between StarCoder2-3B (better transparency, fill-in-middle support) and Qwen2.5-Coder-1.5B (better raw performance, smaller size) depends on whether you prioritize reproducibility or inference efficiency. For a research-focused project with publication goals, StarCoder2-3B's fully traceable training data provides essential provenance. For deployment optimization, Qwen2.5-Coder-1.5B's superior performance in a smaller footprint may justify the documentation trade-off.

The **most likely failure mode** is insufficient Solidity-specific data quality—prioritize the HexaCoder-style synthetic generation pipeline and aggressive quality filtering. The second risk is catastrophic forgetting during fine-tuning—maintain strict **20% replay buffers** from general code throughout post-training.