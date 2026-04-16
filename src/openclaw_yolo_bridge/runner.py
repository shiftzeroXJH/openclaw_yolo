from __future__ import annotations

import json
import os
import subprocess
from typing import Any


class BridgeCommandError(RuntimeError):
    pass


def _cli_executable() -> str:
    return os.environ.get("OPENCLAW_YOLO_BRIDGE_EXECUTABLE", "openclaw-yolo")


def _db_path() -> str | None:
    return os.environ.get("OPENCLAW_YOLO_BRIDGE_DB_PATH")


def _append_optional(args: list[str], flag: str, value: Any) -> None:
    if value is None:
        return
    args.extend([flag, str(value)])


def build_cli_args(command: str, payload: dict[str, Any] | None = None) -> list[str]:
    payload = payload or {}
    args = [_cli_executable()]
    db_path = _db_path()
    if db_path:
        args.extend(["--db-path", db_path])

    if command == "list-tasks":
        return args + ["list-tasks"]
    if command == "show-task":
        return args + ["show-task", "--experiment-id", str(payload["experiment_id"])]
    if command == "cancel-task":
        built = args + ["cancel-task", "--experiment-id", str(payload["experiment_id"])]
        _append_optional(built, "--reason", payload.get("reason"))
        return built
    if command == "delete-task":
        built = args + ["delete-task", "--experiment-id", str(payload["experiment_id"])]
        if payload.get("keep_files"):
            built.append("--keep-files")
        if payload.get("force"):
            built.append("--force")
        return built
    if command == "inspect-dataset":
        return args + ["inspect-dataset", "--dataset-root", str(payload["dataset_root"])]
    if command == "run-trial":
        return args + ["run-trial", "--experiment-id", str(payload["experiment_id"])]
    if command == "get-summary":
        return args + ["get-summary", "--trial-id", str(payload["trial_id"])]
    if command == "propose-next":
        return args + ["propose-next", "--experiment-id", str(payload["experiment_id"])]
    if command == "continue":
        return args + ["continue", "--experiment-id", str(payload["experiment_id"])]
    if command == "create-task":
        built = [
            *args,
            "create-task",
            "--description",
            str(payload.get("description", "")),
            "--task-type",
            str(payload["task_type"]),
            "--dataset-root",
            str(payload["dataset_root"]),
            "--pretrained",
            str(payload["pretrained"]),
            "--save-root",
            str(payload["save_root"]),
            "--goal",
            f"metric={payload['goal']['metric']},target={payload['goal']['target']}",
        ]
        _append_optional(built, "--dataset-yaml", payload.get("dataset_yaml"))
        if "auto_iterate" in payload:
            built.extend(["--auto-iterate", str(payload["auto_iterate"]).lower()])
        _append_optional(built, "--confirm-timeout", payload.get("confirm_timeout"))
        for key, flag in (
            ("imgsz", "--imgsz"),
            ("batch", "--batch"),
            ("workers", "--workers"),
            ("epochs", "--epochs"),
            ("lr0", "--lr0"),
            ("weight_decay", "--weight-decay"),
            ("mosaic", "--mosaic"),
            ("mixup", "--mixup"),
            ("degrees", "--degrees"),
            ("translate", "--translate"),
            ("scale", "--scale"),
            ("fliplr", "--fliplr"),
            ("hsv_h", "--hsv-h"),
            ("hsv_s", "--hsv-s"),
            ("hsv_v", "--hsv-v"),
        ):
            _append_optional(built, flag, payload.get(key))
        return built

    raise BridgeCommandError(f"unsupported bridge command: {command}")


def run_cli(command: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    args = build_cli_args(command, payload)
    process = subprocess.run(args, capture_output=True, text=True, check=False)
    stdout = process.stdout.strip()
    stderr = process.stderr.strip()
    try:
        parsed = json.loads(stdout) if stdout else {}
    except json.JSONDecodeError as exc:
        raise BridgeCommandError(
            f"CLI returned non-JSON output for {command}: {stdout[:200]}"
        ) from exc

    if process.returncode != 0:
        if "error" not in parsed:
            parsed["error"] = stderr or f"command failed: {command}"
        return process.returncode, parsed
    return process.returncode, parsed
