from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from openclaw_yolo.constants import ALLOWED_TASK_TYPES
from openclaw_yolo.service import OrchestratorService, ServiceError


def _goal_arg(value: str) -> dict[str, Any]:
    raw = value.strip()
    if raw.startswith(("'", '"')) and raw.endswith(("'", '"')) and len(raw) >= 2:
        raw = raw[1:-1].strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        parsed = None

    if isinstance(parsed, dict) and "metric" in parsed and "target" in parsed:
        return parsed

    for separator in ("=", ":"):
        if separator in raw and "," not in raw and "metric" not in raw and "target" not in raw:
            metric, target = raw.split(separator, 1)
            try:
                return {"metric": metric.strip(), "target": float(target.strip())}
            except ValueError as exc:
                raise argparse.ArgumentTypeError("goal target must be a number") from exc

    if "," in raw:
        pairs: dict[str, str] = {}
        for part in raw.split(","):
            if "=" in part:
                key, item_value = part.split("=", 1)
            elif ":" in part:
                key, item_value = part.split(":", 1)
            else:
                continue
            pairs[key.strip()] = item_value.strip()
        if "metric" in pairs and "target" in pairs:
            try:
                return {"metric": pairs["metric"], "target": float(pairs["target"])}
            except ValueError as exc:
                raise argparse.ArgumentTypeError("goal target must be a number") from exc

    raise argparse.ArgumentTypeError(
        "goal must be JSON or use 'metric=map50_95,target=0.65'"
    )


def _emit(payload: dict[str, Any], exit_code: int = 0) -> int:
    print(json.dumps(payload, ensure_ascii=False))
    return exit_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openclaw-yolo")
    parser.add_argument("--db-path", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect-dataset")
    inspect_parser.add_argument("--dataset-root", required=True)

    create_parser = subparsers.add_parser("create-task")
    create_parser.add_argument("--description", default="")
    create_parser.add_argument("--session-key", required=True)
    create_parser.add_argument("--task-type", required=True, choices=ALLOWED_TASK_TYPES)
    create_parser.add_argument("--dataset-root", required=True)
    create_parser.add_argument("--dataset-yaml")
    create_parser.add_argument("--pretrained", required=True)
    create_parser.add_argument("--save-root", required=True)
    create_parser.add_argument("--goal", required=True, type=_goal_arg)
    create_parser.add_argument("--auto-iterate", default="false")
    create_parser.add_argument("--confirm-timeout", type=int, default=60)
    create_parser.add_argument("--imgsz", type=int)
    create_parser.add_argument("--batch", type=int)
    create_parser.add_argument("--workers", type=int)
    create_parser.add_argument("--epochs", type=int)
    create_parser.add_argument("--lr0", type=float)
    create_parser.add_argument("--weight-decay", dest="weight_decay", type=float)
    create_parser.add_argument("--mosaic", type=float)
    create_parser.add_argument("--mixup", type=float)
    create_parser.add_argument("--degrees", type=float)
    create_parser.add_argument("--translate", type=float)
    create_parser.add_argument("--scale", type=float)
    create_parser.add_argument("--fliplr", type=float)
    create_parser.add_argument("--hsv-h", dest="hsv_h", type=float)
    create_parser.add_argument("--hsv-s", dest="hsv_s", type=float)
    create_parser.add_argument("--hsv-v", dest="hsv_v", type=float)

    run_parser = subparsers.add_parser("run-trial")
    run_parser.add_argument("--experiment-id", required=True)

    summary_parser = subparsers.add_parser("get-summary")
    summary_parser.add_argument("--trial-id", required=True)

    list_parser = subparsers.add_parser("list-tasks")

    show_parser = subparsers.add_parser("show-task")
    show_parser.add_argument("--experiment-id", required=True)

    propose_parser = subparsers.add_parser("propose-next")
    propose_parser.add_argument("--experiment-id", required=True)

    cancel_parser = subparsers.add_parser("cancel-task")
    cancel_parser.add_argument("--experiment-id", required=True)
    cancel_parser.add_argument("--reason")

    delete_parser = subparsers.add_parser("delete-task")
    delete_parser.add_argument("--experiment-id", required=True)
    delete_parser.add_argument("--keep-files", action="store_true")
    delete_parser.add_argument("--force", action="store_true")

    continue_parser = subparsers.add_parser("continue")
    continue_parser.add_argument("--experiment-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = OrchestratorService(db_path=args.db_path)

    try:
        if args.command == "inspect-dataset":
            return _emit(service.inspect_dataset(args.dataset_root))
        if args.command == "create-task":
            return _emit(
                service.create_task(
                    description=args.description,
                    session_key=args.session_key,
                    task_type=args.task_type,
                    dataset_root=args.dataset_root,
                    dataset_yaml=args.dataset_yaml,
                    pretrained=args.pretrained,
                    save_root=args.save_root,
                    goal=args.goal,
                    auto_iterate=str(args.auto_iterate).lower() == "true",
                    confirm_timeout=args.confirm_timeout,
                    initial_overrides={
                        "imgsz": args.imgsz,
                        "batch": args.batch,
                        "workers": args.workers,
                        "epochs": args.epochs,
                        "lr0": args.lr0,
                        "weight_decay": args.weight_decay,
                        "mosaic": args.mosaic,
                        "mixup": args.mixup,
                        "degrees": args.degrees,
                        "translate": args.translate,
                        "scale": args.scale,
                        "fliplr": args.fliplr,
                        "hsv_h": args.hsv_h,
                        "hsv_s": args.hsv_s,
                        "hsv_v": args.hsv_v,
                    },
                )
            )
        if args.command == "list-tasks":
            return _emit(service.list_tasks())
        if args.command == "show-task":
            return _emit(service.show_task(args.experiment_id))
        if args.command == "run-trial":
            return _emit(service.run_trial(args.experiment_id))
        if args.command == "get-summary":
            return _emit(service.get_summary(args.trial_id))
        if args.command == "propose-next":
            return _emit(service.propose_next(args.experiment_id))
        if args.command == "cancel-task":
            return _emit(service.cancel_task(args.experiment_id, args.reason))
        if args.command == "delete-task":
            return _emit(
                service.delete_task(
                    args.experiment_id,
                    keep_files=args.keep_files,
                    force=args.force,
                )
            )
        if args.command == "continue":
            return _emit(service.continue_experiment(args.experiment_id))
    except (ServiceError, FileNotFoundError, KeyError, ValueError) as exc:
        return _emit({"error": str(exc)}, exit_code=1)
    return _emit({"error": f"unsupported command: {args.command}"}, exit_code=1)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
