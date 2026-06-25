"""Modal B200 launcher for NeMo AutoModel and TRL post-training jobs.

Examples:

    modal run modal_apps/automodel_b200_post_training.py --dry-run

    modal run modal_apps/automodel_b200_post_training.py \
      --config configs/automodel_b200/qwen25_coder_7b_qlora_sft.yaml \
      --mode automodel

    modal run modal_apps/automodel_b200_post_training.py \
      --config configs/automodel_b200/qwen25_coder_7b_kd.yaml \
      --mode kd

    modal run modal_apps/automodel_b200_post_training.py \
      --config configs/automodel_b200/trl_dpo_qwen25_coder_7b.yaml \
      --mode dpo
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Literal

import modal


APP_NAME = "automodel-b200-post-training"
REMOTE_ROOT = Path("/workspace/smart-contract-data")
HF_CACHE_PATH = "/root/.cache/huggingface"
DATA_PATH = "/data/automodel"
OUTPUT_PATH = "/outputs"

GPU_CONFIG = os.environ.get("AUTOMODEL_MODAL_GPU", "B200")
TIMEOUT_SECONDS = 30 * 60 * 60

app = modal.App(APP_NAME)

HF_CACHE_VOLUME = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
DATA_VOLUME = modal.Volume.from_name("automodel-b200-data", create_if_missing=True)
OUTPUT_VOLUME = modal.Volume.from_name("automodel-b200-outputs", create_if_missing=True)

repo_root = Path(__file__).resolve().parents[1]

image = (
    modal.Image.from_registry("nvcr.io/nvidia/nemo-automodel:26.04.00")
    .pip_install(
        "accelerate",
        "bitsandbytes",
        "datasets",
        "peft",
        "PyYAML",
        "transformers",
        "trl",
    )
    .add_local_dir(repo_root / "configs", remote_path=str(REMOTE_ROOT / "configs"))
    .add_local_dir(repo_root / "scripts", remote_path=str(REMOTE_ROOT / "scripts"))
)


def remote_config_path(config: str) -> Path:
    path = Path(config)
    if path.is_absolute():
        return path
    return REMOTE_ROOT / path


def automodel_command(config: str, nproc_per_node: int) -> list[str]:
    command = ["automodel"]
    if nproc_per_node > 1:
        command.append(f"--nproc-per-node={nproc_per_node}")
    command.append(str(remote_config_path(config)))
    return command


def kd_command(config: str, nproc_per_node: int) -> list[str]:
    import inspect
    import nemo_automodel.recipes.llm.kd as kd

    return [
        "torchrun",
        "--nproc-per-node",
        str(nproc_per_node),
        inspect.getfile(kd),
        "-c",
        str(remote_config_path(config)),
    ]


def dpo_command(config: str) -> list[str]:
    return [
        "python",
        str(REMOTE_ROOT / "scripts" / "trl_dpo_train.py"),
        "--config",
        str(remote_config_path(config)),
    ]


@app.function(
    image=image,
    gpu=GPU_CONFIG,
    volumes={
        HF_CACHE_PATH: HF_CACHE_VOLUME,
        DATA_PATH: DATA_VOLUME,
        OUTPUT_PATH: OUTPUT_VOLUME,
    },
    timeout=TIMEOUT_SECONDS,
    startup_timeout=60 * 60,
)
def run_training(
    config: str = "configs/automodel_b200/qwen25_coder_7b_qlora_sft.yaml",
    mode: Literal["automodel", "kd", "dpo"] = "automodel",
    nproc_per_node: int = 1,
    dry_run: bool = False,
) -> dict[str, object]:
    if mode == "automodel":
        command = automodel_command(config, nproc_per_node)
    elif mode == "kd":
        command = kd_command(config, nproc_per_node)
    elif mode == "dpo":
        command = dpo_command(config)
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    result: dict[str, object] = {
        "mode": mode,
        "gpu": GPU_CONFIG,
        "config": str(remote_config_path(config)),
        "command": command,
        "data_path": DATA_PATH,
        "output_path": OUTPUT_PATH,
    }

    if dry_run:
        result["dry_run"] = True
        return result

    subprocess.run(command, cwd=REMOTE_ROOT, check=True)
    OUTPUT_VOLUME.commit()
    result["dry_run"] = False
    result["status"] = "completed"
    return result


@app.local_entrypoint()
def main(
    config: str = "configs/automodel_b200/qwen25_coder_7b_qlora_sft.yaml",
    mode: str = "automodel",
    nproc_per_node: int = 1,
    dry_run: bool = False,
) -> None:
    result = run_training.remote(
        config=config,
        mode=mode,  # type: ignore[arg-type]
        nproc_per_node=nproc_per_node,
        dry_run=dry_run,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
