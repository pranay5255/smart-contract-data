"""Compute Modal B200 post-training budgets from a YAML plan."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PhaseCost:
    name: str
    gpu_count: int
    hours: float
    b200_hours: float
    cost_usd: float
    category: str


@dataclass(frozen=True)
class BudgetSummary:
    hourly_rate_per_b200: float
    total_budget_usd: float
    purchased_b200_hours: float
    planned_b200_hours: float
    planned_cost_usd: float
    reserve_b200_hours: float
    reserve_cost_usd: float
    phases: list[PhaseCost]


def load_plan(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML object")
    return data


def summarize_budget(plan: dict[str, Any]) -> BudgetSummary:
    hourly_rate = float(plan["hourly_rate_per_b200"])
    total_budget = float(plan["total_budget_usd"])
    phases: list[PhaseCost] = []

    for phase in plan.get("phases", []):
        if not isinstance(phase, dict):
            raise ValueError("Each phase must be a YAML object")
        gpu_count = int(phase.get("gpu_count", 1))
        hours = float(phase["hours"])
        b200_hours = gpu_count * hours
        phases.append(
            PhaseCost(
                name=str(phase["name"]),
                gpu_count=gpu_count,
                hours=hours,
                b200_hours=b200_hours,
                cost_usd=b200_hours * hourly_rate,
                category=str(phase.get("category", "training")),
            )
        )

    planned_b200_hours = sum(phase.b200_hours for phase in phases)
    planned_cost = planned_b200_hours * hourly_rate
    purchased_b200_hours = total_budget / hourly_rate
    reserve_hours = purchased_b200_hours - planned_b200_hours

    return BudgetSummary(
        hourly_rate_per_b200=hourly_rate,
        total_budget_usd=total_budget,
        purchased_b200_hours=purchased_b200_hours,
        planned_b200_hours=planned_b200_hours,
        planned_cost_usd=planned_cost,
        reserve_b200_hours=reserve_hours,
        reserve_cost_usd=reserve_hours * hourly_rate,
        phases=phases,
    )


def as_jsonable(summary: BudgetSummary) -> dict[str, Any]:
    data = asdict(summary)
    for key, value in list(data.items()):
        if isinstance(value, float):
            data[key] = round(value, 4)
    for phase in data["phases"]:
        for key, value in list(phase.items()):
            if isinstance(value, float):
                phase[key] = round(value, 4)
    return data


def format_table(summary: BudgetSummary) -> str:
    lines = [
        "Modal B200 budget",
        f"rate: ${summary.hourly_rate_per_b200:.4f}/B200-hour",
        f"budget: ${summary.total_budget_usd:.2f} = {summary.purchased_b200_hours:.1f} B200-hours",
        "",
        f"{'phase':28} {'gpus':>4} {'hours':>8} {'B200-h':>8} {'cost':>10}",
    ]
    for phase in summary.phases:
        lines.append(
            f"{phase.name:28} {phase.gpu_count:>4} {phase.hours:>8.1f} "
            f"{phase.b200_hours:>8.1f} ${phase.cost_usd:>9.2f}"
        )
    lines.extend(
        [
            "",
            "planned: "
            f"{summary.planned_b200_hours:.1f} B200-hours = ${summary.planned_cost_usd:.2f}",
            "reserve: "
            f"{summary.reserve_b200_hours:.1f} B200-hours = ${summary.reserve_cost_usd:.2f}",
        ]
    )
    if summary.reserve_b200_hours < 0:
        lines.append("WARNING: planned phases exceed the budget.")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan",
        type=Path,
        default=Path("configs/automodel_b200/budget.yaml"),
        help="Budget YAML path.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = summarize_budget(load_plan(args.plan))
    if args.json:
        print(json.dumps(as_jsonable(summary), indent=2, sort_keys=True))
    else:
        print(format_table(summary))
    return 1 if summary.reserve_b200_hours < 0 else 0


if __name__ == "__main__":
    sys.exit(main())
