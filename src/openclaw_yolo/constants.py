from __future__ import annotations

from typing import Any

TASK_BASELINES: dict[str, dict[str, Any]] = {
    "detection": {
        "imgsz": 640,
        "batch": 16,
        "workers": 2,
        "epochs": 100,
        "lr0": 0.01,
        "weight_decay": 0.0005,
        "mosaic": 0.5,
        "mixup": 0.0,
        "degrees": 0.0,
        "translate": 0.1,
        "scale": 0.5,
        "fliplr": 0.5,
        "hsv_h": 0.015,
        "hsv_s": 0.7,
        "hsv_v": 0.4,
    }
}

SEARCH_SPACE: dict[str, dict[str, Any]] = {
    "imgsz": {"type": "int", "min": 224, "max": 1536, "step": 32},
    "batch": {"type": "choice", "values": [4, 8, 16, 32]},
    "workers": {"type": "choice", "values": [0, 1, 2, 4]},
    "epochs": {"type": "int", "min": 1, "max": 1000},
    "lr0": {"type": "float", "min": 0.00001, "max": 0.1},
    "weight_decay": {"type": "float", "min": 0.0, "max": 0.01},
    "mosaic": {"type": "float", "min": 0.0, "max": 1.0},
    "mixup": {"type": "float", "min": 0.0, "max": 1.0},
    "degrees": {"type": "float", "min": 0.0, "max": 45.0},
    "translate": {"type": "float", "min": 0.0, "max": 0.5},
    "scale": {"type": "float", "min": 0.0, "max": 1.0},
    "fliplr": {"type": "float", "min": 0.0, "max": 1.0},
    "hsv_h": {"type": "float", "min": 0.0, "max": 0.1},
    "hsv_s": {"type": "float", "min": 0.0, "max": 1.0},
    "hsv_v": {"type": "float", "min": 0.0, "max": 1.0},
}

STOP_CONDITIONS = {
    "max_trials": 8,
    "max_no_improve": 3,
    "min_delta": 0.003,
    "target_score": 0.65,
}

ALLOWED_TASK_TYPES = tuple(TASK_BASELINES.keys())

STATE_INIT = "INIT"
STATE_READY = "READY"
STATE_TRAINING = "TRAINING"
STATE_ANALYZING = "ANALYZING"
STATE_WAITING = "WAITING_USER_CONFIRM"
STATE_RETRAINING = "RETRAINING"
STATE_COMPLETED = "COMPLETED"
STATE_FAILED = "FAILED"
STATE_CANCELLED = "CANCELLED"

SUMMARY_FILENAME = "summary.json"
EXPERIMENT_FILENAME = "experiment.json"
TRIAL_CONFIG_FILENAME = "config.json"
