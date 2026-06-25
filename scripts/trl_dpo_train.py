"""Run TRL DPOTrainer from a small YAML config.

This is intentionally separate from the NeMo AutoModel configs because the
current AutoModel path in this repo treats DPO as a TRL fallback.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    if not isinstance(config, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return config


def load_json_dataset(train_file: str, eval_file: str | None):
    from datasets import load_dataset

    data_files: dict[str, str] = {"train": train_file}
    if eval_file:
        data_files["validation"] = eval_file
    dataset = load_dataset("json", data_files=data_files)
    return dataset["train"], dataset.get("validation")


def run_dpo(config: dict[str, Any]) -> None:
    from peft import LoraConfig
    from trl import DPOConfig, DPOTrainer

    train_dataset, eval_dataset = load_json_dataset(config["train_file"], config.get("eval_file"))
    training = dict(config.get("training", {}))
    output_dir = str(config["output_dir"])
    training_args = DPOConfig(output_dir=output_dir, **training)

    peft_config = None
    if config.get("peft"):
        peft_config = LoraConfig(**config["peft"])

    trainer_kwargs = {
        "model": config["model_name_or_path"],
        "args": training_args,
        "train_dataset": train_dataset,
    }
    if eval_dataset is not None:
        trainer_kwargs["eval_dataset"] = eval_dataset
    if peft_config is not None:
        trainer_kwargs["peft_config"] = peft_config

    trainer = DPOTrainer(**trainer_kwargs)
    trainer.train()
    trainer.save_model(output_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path, help="TRL DPO YAML config.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_dpo(load_config(args.config))
    return 0


if __name__ == "__main__":
    sys.exit(main())
