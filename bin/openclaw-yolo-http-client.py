#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:8765"
BASE_URL = os.environ.get("OPENCLAW_YOLO_BRIDGE_URL", DEFAULT_BASE_URL)
NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _wsl_windows_host_url() -> str | None:
    if platform.system().lower() != "linux":
        return None
    try:
        with open("/proc/version", "r", encoding="utf-8") as handle:
            if "microsoft" not in handle.read().lower():
                return None
    except OSError:
        return None

    for path in ("/etc/resolv.conf",):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                for line in handle:
                    parts = line.strip().split()
                    if len(parts) == 2 and parts[0] == "nameserver":
                        return f"http://{parts[1]}:8765"
        except OSError:
            continue
    return None


def _candidate_base_urls() -> list[str]:
    urls = [BASE_URL.rstrip("/")]
    if "OPENCLAW_YOLO_BRIDGE_URL" not in os.environ:
        wsl_url = _wsl_windows_host_url()
        if wsl_url and wsl_url.rstrip("/") not in urls:
            urls.append(wsl_url.rstrip("/"))
    return urls


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> int:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    last_error = ""
    for base_url in _candidate_base_urls():
        request = urllib.request.Request(
            urllib.parse.urljoin(f"{base_url}/", path.lstrip("/")),
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with NO_PROXY_OPENER.open(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                print(body)
                return 0
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            if exc.code in {502, 503, 504}:
                last_error = f"{base_url}: HTTP {exc.code}"
                continue
            print(body or json.dumps({"error": f"HTTP {exc.code}", "base_url": base_url}))
            return 1
        except urllib.error.URLError as exc:
            last_error = f"{base_url}: {exc.reason}"
    print(json.dumps({"error": f"bridge unavailable: {last_error}"}))
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openclaw-yolo-http-client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list-tasks")
    list_parser.add_argument("--full", action="store_true")
    show_parser = subparsers.add_parser("show-task")
    show_parser.add_argument("--experiment-id", required=True)
    show_parser.add_argument("--full", action="store_true")
    job_parser = subparsers.add_parser("get-job")
    job_parser.add_argument("--job-id", required=True)
    cancel_parser = subparsers.add_parser("cancel-task")
    cancel_parser.add_argument("--experiment-id", required=True)
    cancel_parser.add_argument("--reason")
    delete_parser = subparsers.add_parser("delete-task")
    delete_parser.add_argument("--experiment-id", required=True)
    delete_parser.add_argument("--keep-files", action="store_true")
    delete_parser.add_argument("--force", action="store_true")
    inspect_parser = subparsers.add_parser("inspect-dataset")
    inspect_parser.add_argument("--dataset-root", required=True)
    run_parser = subparsers.add_parser("run-trial")
    run_parser.add_argument("--experiment-id", required=True)
    summary_parser = subparsers.add_parser("get-summary")
    summary_parser.add_argument("--trial-id", required=True)
    summary_parser.add_argument("--full", action="store_true")
    continue_parser = subparsers.add_parser("continue")
    continue_parser.add_argument("--experiment-id", required=True)
    continue_parser.add_argument("--reason", required=True)
    for arg in (
        "imgsz",
        "batch",
        "workers",
        "epochs",
        "lr0",
        "weight_decay",
        "mosaic",
        "mixup",
        "degrees",
        "translate",
        "scale",
        "fliplr",
        "hsv_h",
        "hsv_s",
        "hsv_v",
    ):
        continue_parser.add_argument(f"--{arg.replace('_', '-')}")

    create_parser = subparsers.add_parser("create-task")
    create_parser.add_argument("--description", default="")
    create_parser.add_argument("--session-key", required=True)
    create_parser.add_argument("--task-type", required=True)
    create_parser.add_argument("--dataset-root", required=True)
    create_parser.add_argument("--dataset-yaml")
    create_parser.add_argument("--pretrained", required=True)
    create_parser.add_argument("--save-root", default="runs")
    create_parser.add_argument("--goal", required=True)
    create_parser.add_argument("--auto-iterate", default="false")
    create_parser.add_argument("--confirm-timeout", type=int, default=60)
    for arg in (
        "imgsz",
        "batch",
        "workers",
        "epochs",
        "lr0",
        "weight_decay",
        "mosaic",
        "mixup",
        "degrees",
        "translate",
        "scale",
        "fliplr",
        "hsv_h",
        "hsv_s",
        "hsv_v",
    ):
        create_parser.add_argument(f"--{arg.replace('_', '-')}")
    return parser


def _parse_goal(value: str) -> dict[str, Any]:
    raw = value.strip()
    if raw.startswith("{"):
        return json.loads(raw)
    if "," in raw:
        parts = {}
        for part in raw.split(","):
            key, item_value = part.split("=", 1)
            parts[key] = item_value
        return {"metric": parts["metric"], "target": float(parts["target"])}
    if "=" in raw:
        metric, target = raw.split("=", 1)
        return {"metric": metric, "target": float(target)}
    raise ValueError("unsupported goal format")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-tasks":
        compact = "false" if args.full else "true"
        return _request("GET", f"/tasks?compact={compact}")
    if args.command == "show-task":
        compact = "false" if args.full else "true"
        return _request("GET", f"/tasks/{args.experiment_id}?compact={compact}")
    if args.command == "get-job":
        return _request("GET", f"/jobs/{args.job_id}")
    if args.command == "cancel-task":
        return _request("POST", f"/tasks/{args.experiment_id}/cancel", {"reason": args.reason})
    if args.command == "delete-task":
        keep_files = "true" if args.keep_files else "false"
        force = "true" if args.force else "false"
        return _request("DELETE", f"/tasks/{args.experiment_id}?keep_files={keep_files}&force={force}")
    if args.command == "inspect-dataset":
        encoded = urllib.parse.quote(args.dataset_root, safe="")
        return _request("GET", f"/inspect-dataset?dataset_root={encoded}")
    if args.command == "run-trial":
        return _request("POST", f"/tasks/{args.experiment_id}/run")
    if args.command == "get-summary":
        compact = "false" if args.full else "true"
        return _request("GET", f"/trials/{args.trial_id}/summary?compact={compact}")
    if args.command == "continue":
        payload = {"reason": args.reason, "param_updates": {}}
        for key in (
            "imgsz",
            "batch",
            "workers",
            "epochs",
            "lr0",
            "weight_decay",
            "mosaic",
            "mixup",
            "degrees",
            "translate",
            "scale",
            "fliplr",
            "hsv_h",
            "hsv_s",
            "hsv_v",
        ):
            value = getattr(args, key)
            if value is not None:
                try:
                    payload["param_updates"][key] = int(value)
                except ValueError:
                    try:
                        payload["param_updates"][key] = float(value)
                    except ValueError:
                        payload["param_updates"][key] = value
        return _request("POST", f"/tasks/{args.experiment_id}/continue", payload)
    if args.command == "create-task":
        payload = {
            "description": args.description,
            "session_key": args.session_key,
            "task_type": args.task_type,
            "dataset_root": args.dataset_root,
            "dataset_yaml": args.dataset_yaml,
            "pretrained": args.pretrained,
            "save_root": args.save_root,
            "goal": _parse_goal(args.goal),
            "auto_iterate": str(args.auto_iterate).lower() == "true",
            "confirm_timeout": args.confirm_timeout,
        }
        for key in (
            "imgsz",
            "batch",
            "workers",
            "epochs",
            "lr0",
            "weight_decay",
            "mosaic",
            "mixup",
            "degrees",
            "translate",
            "scale",
            "fliplr",
            "hsv_h",
            "hsv_s",
            "hsv_v",
        ):
            value = getattr(args, key)
            if value is not None:
                try:
                    payload[key] = int(value)
                except ValueError:
                    try:
                        payload[key] = float(value)
                    except ValueError:
                        payload[key] = value
        return _request("POST", "/tasks", payload)
    parser.error(f"unsupported command: {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
