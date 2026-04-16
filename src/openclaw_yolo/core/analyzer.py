from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from openclaw_yolo.models import Summary


def _safe_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_results_rows(results_csv: Path) -> list[dict[str, Any]]:
    with results_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def _column_value(row: dict[str, Any], names: tuple[str, ...]) -> float | None:
    for name in names:
        if name in row:
            value = _safe_float(row[name])
            if value is not None:
                return value
    return None


def _loss_trend(rows: list[dict[str, Any]]) -> str:
    if len(rows) < 3:
        return "unknown"

    values = [_column_value(row, ("train/box_loss", "train/loss")) for row in rows]
    values = [value for value in values if value is not None]
    if len(values) < 3:
        return "unknown"

    deltas = [values[index + 1] - values[index] for index in range(len(values) - 1)]
    positives = sum(1 for delta in deltas if delta > 0)
    negatives = sum(1 for delta in deltas if delta < 0)
    if negatives >= max(2, len(deltas) * 0.7):
        return "stable_down"
    if positives >= max(2, len(deltas) * 0.7):
        return "diverging"
    return "oscillating"


def _detect_overfitting(rows: list[dict[str, Any]]) -> str:
    if len(rows) < 5:
        return "none"
    tail = rows[-5:]
    train_losses = [_column_value(row, ("train/box_loss", "train/loss")) for row in tail]
    metrics = [_column_value(row, ("metrics/mAP50-95(B)", "metrics/mAP50-95")) for row in tail]
    train_losses = [value for value in train_losses if value is not None]
    metrics = [value for value in metrics if value is not None]
    if len(train_losses) < 3 or len(metrics) < 3:
        return "none"
    if train_losses[-1] < train_losses[0] and metrics[-1] <= metrics[0]:
        return "mild"
    return "none"


def _plateau(rows: list[dict[str, Any]], min_delta: float = 0.002) -> tuple[bool, int | None]:
    if len(rows) < 6:
        return False, None
    values = [_column_value(row, ("metrics/mAP50-95(B)", "metrics/mAP50-95")) for row in rows]
    values = [value for value in values if value is not None]
    if len(values) < 6:
        return False, None
    midpoint = len(values) // 2
    old_best = max(values[:midpoint])
    recent_best = max(values[midpoint:])
    if recent_best - old_best < min_delta:
        plateau_epoch = values.index(recent_best) + 1
        return True, plateau_epoch
    return False, None


def build_summary(
    trial_id: str,
    run_dir: str,
    params: dict[str, Any],
    previous_summary: dict[str, Any] | None = None,
) -> Summary:
    run_path = Path(run_dir)
    results_csv = run_path / "results.csv"
    if not results_csv.exists():
        raise FileNotFoundError(f"results.csv not found in run dir: {run_dir}")

    rows = _load_results_rows(results_csv)
    if not rows:
        raise ValueError("results.csv is empty")

    last_row = rows[-1]
    best_map = max(
        (
            _column_value(row, ("metrics/mAP50-95(B)", "metrics/mAP50-95")) or 0.0
            for row in rows
        ),
        default=0.0,
    )
    best_epoch = next(
        (
            index + 1
            for index, row in enumerate(rows)
            if (_column_value(row, ("metrics/mAP50-95(B)", "metrics/mAP50-95")) or 0.0) == best_map
        ),
        len(rows),
    )
    precision = _column_value(last_row, ("metrics/precision(B)", "metrics/precision")) or 0.0
    recall = _column_value(last_row, ("metrics/recall(B)", "metrics/recall")) or 0.0
    map50 = _column_value(last_row, ("metrics/mAP50(B)", "metrics/mAP50")) or 0.0
    map50_95 = _column_value(last_row, ("metrics/mAP50-95(B)", "metrics/mAP50-95")) or 0.0
    plateau, plateau_epoch = _plateau(rows)
    overfitting = _detect_overfitting(rows)
    epoch_time = _column_value(last_row, ("time", "epoch_time"))
    gpu_mem = _column_value(last_row, ("gpu_mem",))
    warnings: list[str] = []
    if gpu_mem and gpu_mem > 10_240:
        warnings.append("gpu_memory_high")
    if overfitting != "none":
        warnings.append("possible_overfitting")

    prev_metrics = (previous_summary or {}).get("final_metrics", {})
    delta_vs_prev = {
        "map50_95": round(map50_95 - float(prev_metrics.get("map50_95", 0.0)), 6),
        "recall": round(recall - float(prev_metrics.get("recall", 0.0)), 6),
    }
    return Summary(
        trial_id=trial_id,
        basic_info={
            "epochs_planned": params["epochs"],
            "epochs_completed": len(rows),
            "early_stop": len(rows) < int(params["epochs"]),
            "best_epoch": best_epoch,
            "train_time_sec": None if epoch_time is None else round(epoch_time * len(rows), 3),
        },
        final_metrics={
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "map50": round(map50, 6),
            "map50_95": round(map50_95, 6),
        },
        delta_vs_prev=delta_vs_prev,
        training_dynamics={
            "loss_trend": _loss_trend(rows),
            "plateau": plateau,
            "plateau_epoch": plateau_epoch,
            "overfitting": overfitting,
        },
        warnings=warnings,
        resource={
            "avg_epoch_time": epoch_time,
            "gpu_mem_peak": gpu_mem,
        },
        params=params,
    )
