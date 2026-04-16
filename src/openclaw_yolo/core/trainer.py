from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any


class TrainingError(RuntimeError):
    pass


def run_training(
    pretrained_model: str,
    dataset_yaml: str,
    run_dir: str,
    trial_name: str,
    params: dict[str, Any],
) -> dict[str, str]:
    try:
        from ultralytics import YOLO
    except ImportError as exc:
        raise TrainingError(
            "ultralytics is not installed in the current environment"
        ) from exc

    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)
    stdout_log = run_path / "stdout.log"
    stderr_log = run_path / "stderr.log"

    try:
        model = YOLO(pretrained_model)
        with stdout_log.open("w", encoding="utf-8") as stdout_handle, stderr_log.open(
            "w", encoding="utf-8"
        ) as stderr_handle, redirect_stdout(stdout_handle), redirect_stderr(stderr_handle):
            model.train(
                data=dataset_yaml,
                epochs=int(params["epochs"]),
                imgsz=int(params["imgsz"]),
                batch=int(params["batch"]),
                workers=int(params["workers"]),
                lr0=float(params["lr0"]),
                weight_decay=float(params["weight_decay"]),
                mosaic=float(params["mosaic"]),
                mixup=float(params["mixup"]),
                degrees=float(params["degrees"]),
                translate=float(params["translate"]),
                scale=float(params["scale"]),
                fliplr=float(params["fliplr"]),
                hsv_h=float(params["hsv_h"]),
                hsv_s=float(params["hsv_s"]),
                hsv_v=float(params["hsv_v"]),
                project=str(run_path.parent),
                name=run_path.name,
                exist_ok=True,
                verbose=False,
            )
    except Exception as exc:  # pragma: no cover
        raise TrainingError(str(exc)) from exc

    results_csv = run_path / "results.csv"
    if not results_csv.exists():
        raise TrainingError(f"training finished but results.csv not found for {trial_name}")
    return {
        "run_dir": str(run_path.resolve()),
        "stdout_log": str(stdout_log.resolve()),
        "stderr_log": str(stderr_log.resolve()),
    }
