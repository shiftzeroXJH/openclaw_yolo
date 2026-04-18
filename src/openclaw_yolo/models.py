from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class GoalConfig:
    metric: str
    target: float


@dataclass
class ExperimentConfig:
    experiment_id: str
    description: str
    session_key: str
    task_type: str
    dataset_root: str
    dataset_yaml: str
    pretrained_model: str
    save_root: str
    goal: GoalConfig
    auto_iterate: bool
    confirm_timeout: int
    status: str
    initial_params: dict[str, Any]
    search_space: dict[str, list[Any]]
    stop_conditions: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["goal"] = asdict(self.goal)
        return data


@dataclass
class TrialRecord:
    trial_id: str
    experiment_id: str
    iteration: int
    params: dict[str, Any]
    status: str
    run_dir: str
    summary_path: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class Summary:
    trial_id: str
    basic_info: dict[str, Any]
    final_metrics: dict[str, Any]
    delta_vs_prev: dict[str, Any]
    training_dynamics: dict[str, Any]
    warnings: list[str]
    resource: dict[str, Any]
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
