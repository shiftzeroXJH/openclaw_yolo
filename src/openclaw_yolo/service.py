from __future__ import annotations

import json
import shlex
import subprocess
import shutil
import stat
from pathlib import Path
from typing import Any

from openclaw_yolo.constants import (
    EXPERIMENT_FILENAME,
    SEARCH_SPACE,
    STATE_ANALYZING,
    STATE_AUTO_TUNE,
    STATE_CANCELLED,
    STATE_COMPLETED,
    STATE_FAILED,
    STATE_READY,
    STATE_RETRAINING,
    STATE_TRAINING,
    STATE_WAITING,
    STOP_CONDITIONS,
    SUMMARY_FILENAME,
    TRIAL_CONFIG_FILENAME,
)
from openclaw_yolo.core.analyzer import build_summary
from openclaw_yolo.core.baseline import build_initial_params
from openclaw_yolo.core.dataset import inspect_dataset
from openclaw_yolo.core.llm_adapter import LLMAdapterError, request_next_step
from openclaw_yolo.core.param_search import ProposalValidationError, validate_proposal
from openclaw_yolo.core.trainer import TrainingError, run_training
from openclaw_yolo.db.repository import Repository
from openclaw_yolo.models import ExperimentConfig, GoalConfig, TrialRecord
from openclaw_yolo.utils import ensure_dir, read_json, write_json


class ServiceError(RuntimeError):
    pass


OPENCLAW_SESSIONS_PATH = "~/.openclaw/agents/main/sessions/sessions.json"
OPENCLAW_NOTIFY_SCRIPT = "/home/shiftzero/bin/openclaw_notify.sh"


def _compact_search_space(search_space: dict[str, Any]) -> dict[str, str]:
    compact: dict[str, str] = {}
    for name, spec in search_space.items():
        if not isinstance(spec, dict):
            compact[name] = str(spec)
            continue
        spec_type = spec.get("type")
        if spec_type == "choice":
            values = ", ".join(str(value) for value in spec.get("values", []))
            compact[name] = f"choice[{values}]"
            continue
        if spec_type in {"int", "float"}:
            parts = [spec_type]
            if "min" in spec and "max" in spec:
                parts.append(f"{spec['min']}..{spec['max']}")
            if "step" in spec:
                parts.append(f"step {spec['step']}")
            compact[name] = " ".join(parts)
            continue
        compact[name] = str(spec)
    return compact


def _compact_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "final_metrics": summary.get("final_metrics", {}),
        "delta_vs_prev": summary.get("delta_vs_prev", {}),
        "training_dynamics": summary.get("training_dynamics", {}),
        "warnings": summary.get("warnings", []),
        "resource": summary.get("resource", {}),
        "basic_info": summary.get("basic_info", {}),
        "params": summary.get("params", {}),
    }


def _notification_summary(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "final_metrics": summary.get("final_metrics", {}),
        "delta_vs_prev": summary.get("delta_vs_prev", {}),
        "training_dynamics": summary.get("training_dynamics", {}),
        "warnings": summary.get("warnings", []),
        "resource": summary.get("resource", {}),
        "params": summary.get("params", {}),
    }


def _resolve_session_id(session_key: str) -> str:
    script = (
        "import json, sys, pathlib; "
        "path = pathlib.Path(sys.argv[1]).expanduser(); "
        "session_key = sys.argv[2]; "
        "data = json.loads(path.read_text(encoding='utf-8')); "
        "entry = data.get(session_key); "
        "session_id = None if entry is None else entry.get('sessionId'); "
        "sys.exit(2) if entry is None or not session_id else print(session_id)"
    )
    try:
        process = subprocess.run(
            ["wsl", "python3", "-c", script, OPENCLAW_SESSIONS_PATH, session_key],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ServiceError("failed to invoke WSL while validating session_key") from exc

    stdout = process.stdout.strip()
    stderr = process.stderr.strip()
    if process.returncode == 0 and stdout:
        return stdout
    if process.returncode == 2:
        raise ServiceError("invalid session_key: not found in OpenClaw sessions.json")
    if "No such file" in stderr:
        raise ServiceError(f"OpenClaw sessions file not found: {OPENCLAW_SESSIONS_PATH}")
    raise ServiceError(stderr or "failed to resolve session_key via WSL")


def _build_notify_message(
    config: ExperimentConfig,
    trial_id: str,
    compact_summary: dict[str, Any],
) -> str:
    return (
        "\u8fd9\u662f\u4e00\u6b21 YOLO \u8bad\u7ec3\u5b8c\u6210\u540e\u7684\u81ea\u52a8\u56de\u8c03\uff0c\u8bf7\u7ee7\u7eed\u5728\u5f53\u524d\u4f1a\u8bdd\u4e0a\u4e0b\u6587\u4e2d\u5904\u7406\u3002\n\n"
        f"experiment_id: {config.experiment_id}\n"
        f"trial_id: {trial_id}\n"
        f"goal: {config.goal.metric}={config.goal.target}\n\n"
        "compact_summary:\n"
        f"{json.dumps(compact_summary, ensure_ascii=False, indent=2, sort_keys=True)}\n\n"
        "\u8bf7\u4f60\u57fa\u4e8e\u8fd9\u6b21\u8bad\u7ec3\u7ed3\u679c\uff1a\n"
        "1. \u7528\u4e2d\u6587\u603b\u7ed3\u672c\u8f6e\u6548\u679c\n"
        "2. \u5224\u65ad\u662f\u5426\u8fbe\u5230\u76ee\u6807\n"
        "3. \u5224\u65ad\u662f\u5426\u5b58\u5728\u5e73\u53f0\u671f\u3001\u8fc7\u62df\u5408\u3001\u8d44\u6e90\u74f6\u9888\u6216\u8bad\u7ec3\u4e0d\u7a33\u5b9a\n"
        "4. \u7ed9\u51fa\u4e0b\u4e00\u8f6e\u8bad\u7ec3\u5efa\u8bae\n"
        "5. \u53c2\u6570\u5efa\u8bae\u6700\u591a 3 \u4e2a\uff0c\u4e14\u53ea\u5141\u8bb8\uff1a\n"
        "imgsz, batch, workers, epochs, lr0, weight_decay, mosaic, mixup, degrees, translate, scale, fliplr, hsv_h, hsv_s, hsv_v\n"
        "6. \u4e0d\u8981\u6267\u884c\u8bad\u7ec3\u547d\u4ee4\uff0c\u53ea\u8f93\u51fa\u7ed9\u6211\u7684\u7ed3\u8bba\u548c\u5efa\u8bae"
    )


def _notify_status(latest_event: dict[str, Any] | None) -> dict[str, Any] | None:
    if latest_event is None:
        return None
    payload = latest_event.get("payload", {})
    status = "sent" if latest_event.get("event_type") == "OPENCLAW_NOTIFY_SENT" else "failed"
    result = {
        "status": status,
        "created_at": latest_event.get("created_at"),
        "trial_id": payload.get("trial_id"),
        "session_key": payload.get("session_key"),
    }
    if status == "sent":
        result["session_id"] = payload.get("session_id")
    else:
        result["error"] = payload.get("error")
    return result


def _notify_openclaw_session(session_id: str, message: str) -> None:
    command = (
        f"{shlex.quote(OPENCLAW_NOTIFY_SCRIPT)} "
        f"{shlex.quote(session_id)} "
        f"{shlex.quote(message)}"
    )
    try:
        process = subprocess.run(
            ["wsl", "bash", "-ic", command],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ServiceError("failed to invoke WSL while notifying OpenClaw") from exc
    if process.returncode != 0:
        raise ServiceError(process.stderr.strip() or "openclaw_notify.sh failed")


def _resolve_pretrained_model(pretrained: str) -> str:
    pretrained_path = Path(pretrained)
    if pretrained_path.is_absolute() and pretrained_path.exists():
        return str(pretrained_path.resolve())

    package_model_path = Path(__file__).resolve().parent / "models" / pretrained
    if package_model_path.exists():
        return str(package_model_path.resolve())

    if pretrained_path.exists():
        return str(pretrained_path.resolve())

    return pretrained


def _validate_pretrained_model(pretrained_model: str) -> None:
    model_path = Path(pretrained_model)
    if not model_path.exists():
        return
    if model_path.is_dir():
        raise ServiceError(f"pretrained model path is a directory: {pretrained_model}")
    size = model_path.stat().st_size
    if size < 1024:
        raise ServiceError(
            f"pretrained model file looks invalid or truncated: {pretrained_model} ({size} bytes)"
        )


def _handle_rmtree_error(func: Any, path: str, exc_info: Any) -> None:
    try:
        os_path = Path(path)
        os_path.chmod(stat.S_IWRITE)
        func(path)
    except Exception:
        raise exc_info[1]


class OrchestratorService:
    def __init__(self, db_path: str | None = None) -> None:
        if db_path == ":memory:":
            repo_path = ":memory:"
        else:
            repo_path = str(Path(db_path or "openclaw_yolo_state.sqlite").resolve())
        self.repo = Repository(repo_path)

    def inspect_dataset(self, dataset_root: str) -> dict[str, Any]:
        return {"yaml_candidates": inspect_dataset(dataset_root)}

    def create_task(
        self,
        *,
        description: str,
        session_key: str,
        task_type: str,
        dataset_root: str,
        dataset_yaml: str | None,
        pretrained: str,
        save_root: str,
        goal: dict[str, Any],
        auto_iterate: bool,
        confirm_timeout: int,
        initial_overrides: dict[str, Any],
    ) -> dict[str, Any]:
        normalized_session_key = session_key.strip()
        if not normalized_session_key:
            raise ServiceError("session_key is required")
        _resolve_session_id(normalized_session_key)
        candidates = inspect_dataset(dataset_root)
        if dataset_yaml is None:
            if len(candidates) != 1:
                return {
                    "status": "needs_dataset_yaml",
                    "yaml_candidates": candidates,
                    "message": "dataset yaml must be specified when zero or multiple candidates are found",
                }
            dataset_yaml = candidates[0]
        elif not Path(dataset_yaml).exists():
            raise ServiceError(f"dataset yaml not found: {dataset_yaml}")

        resolved_pretrained = _resolve_pretrained_model(pretrained)
        _validate_pretrained_model(resolved_pretrained)
        experiment_id = self.repo.next_experiment_id()
        experiment_dir = ensure_dir(Path(save_root) / "experiments" / experiment_id)
        config = ExperimentConfig(
            experiment_id=experiment_id,
            description=description.strip(),
            session_key=normalized_session_key,
            task_type=task_type,
            dataset_root=str(Path(dataset_root).resolve()),
            dataset_yaml=str(Path(dataset_yaml).resolve()),
            pretrained_model=resolved_pretrained,
            save_root=str(Path(save_root).resolve()),
            goal=GoalConfig(metric=str(goal["metric"]), target=float(goal["target"])),
            auto_iterate=auto_iterate,
            confirm_timeout=confirm_timeout,
            status=STATE_READY,
            initial_params=build_initial_params(task_type, initial_overrides),
            search_space=SEARCH_SPACE,
            stop_conditions=STOP_CONDITIONS,
        )
        self.repo.create_experiment(config)
        write_json(experiment_dir / EXPERIMENT_FILENAME, config.to_dict())
        self.repo.add_event(experiment_id, "EXPERIMENT_CREATED", config.to_dict())
        return {
            "status": config.status,
            "experiment_id": experiment_id,
            "description": config.description,
            "session_key": config.session_key,
            "dataset_yaml": config.dataset_yaml,
            "initial_params": config.initial_params,
            "experiment_dir": str(experiment_dir),
        }

    def list_tasks(self, compact: bool = False) -> dict[str, Any]:
        experiments = self.repo.list_experiments()
        if compact:
            return {
                "experiments": [
                    {
                        "experiment_id": item.experiment_id,
                        "description": item.description,
                        "session_key": item.session_key,
                        "status": item.status,
                    }
                    for item in experiments
                ]
            }
        return {
            "experiments": [
                {
                    "experiment_id": item.experiment_id,
                    "description": item.description,
                    "session_key": item.session_key,
                    "task_type": item.task_type,
                    "status": item.status,
                    "goal": item.goal.__dict__,
                    "dataset_yaml": item.dataset_yaml,
                    "pretrained_model": item.pretrained_model,
                }
                for item in experiments
            ]
        }

    def show_task(self, experiment_id: str, compact: bool = False) -> dict[str, Any]:
        config = self.repo.get_experiment(experiment_id)
        trials = self.repo.list_trials(experiment_id)
        notify_status = _notify_status(
            self.repo.latest_event_for_types(
                experiment_id,
                ["OPENCLAW_NOTIFY_SENT", "OPENCLAW_NOTIFY_FAILED"],
            )
        )
        if compact:
            latest_trial = trials[-1] if trials else None
            return {
                "experiment_id": config.experiment_id,
                "description": config.description,
                "session_key": config.session_key,
                "status": config.status,
                "goal": config.goal.__dict__,
                "trial_count": len(trials),
                "openclaw_notify": notify_status,
                "latest_trial": None
                if latest_trial is None
                else {
                    "trial_id": latest_trial.trial_id,
                    "iteration": latest_trial.iteration,
                    "status": latest_trial.status,
                    "metrics": latest_trial.metrics,
                },
            }
        return {
            "experiment": config.to_dict(),
            "openclaw_notify": notify_status,
            "trials": [
                {
                    "trial_id": trial.trial_id,
                    "iteration": trial.iteration,
                    "status": trial.status,
                    "params": trial.params,
                    "metrics": trial.metrics,
                    "summary_path": trial.summary_path,
                }
                for trial in trials
            ],
        }

    def cancel_task(self, experiment_id: str, reason: str | None = None) -> dict[str, Any]:
        config = self.repo.get_experiment(experiment_id)
        if config.status in {STATE_COMPLETED, STATE_CANCELLED}:
            return {
                "experiment_id": experiment_id,
                "status": config.status,
                "message": "task already finalized",
            }
        self.repo.update_experiment_status(experiment_id, STATE_CANCELLED)
        self.repo.add_event(
            experiment_id,
            "TASK_CANCELLED",
            {"reason": reason or "cancelled by user"},
        )
        return {
            "experiment_id": experiment_id,
            "status": STATE_CANCELLED,
            "reason": reason or "cancelled by user",
        }

    def delete_task(
        self,
        experiment_id: str,
        *,
        keep_files: bool = False,
        force: bool = False,
    ) -> dict[str, Any]:
        config = self.repo.get_experiment(experiment_id)
        finalized_states = {STATE_COMPLETED, STATE_CANCELLED, STATE_FAILED}
        if not force and config.status not in finalized_states:
            raise ServiceError(
                f"task {experiment_id} is in status {config.status}; cancel or finalize it first, or use --force"
            )

        trials = self.repo.list_trials(experiment_id)
        experiment_dir = Path(config.save_root).resolve() / "experiments" / experiment_id
        files_deleted = False
        warnings: list[str] = []

        deleted_trials = self.repo.delete_trials_for_experiment(experiment_id)
        deleted_events = self.repo.delete_events_for_experiment(experiment_id)
        self.repo.delete_experiment(experiment_id)

        if not keep_files and experiment_dir.exists():
            save_root = Path(config.save_root).resolve()
            experiments_root = (save_root / "experiments").resolve()
            resolved_experiment_dir = experiment_dir.resolve()
            if experiments_root not in resolved_experiment_dir.parents:
                raise ServiceError(f"refusing to delete path outside experiments root: {resolved_experiment_dir}")
            try:
                shutil.rmtree(resolved_experiment_dir, onerror=_handle_rmtree_error)
                files_deleted = True
            except Exception as exc:
                warnings.append(f"failed to delete files: {exc}")

        return {
            "experiment_id": experiment_id,
            "deleted": True,
            "deleted_trials": deleted_trials,
            "deleted_events": deleted_events,
            "files_deleted": files_deleted,
            "kept_files": keep_files,
            "previous_status": config.status,
            "trial_ids": [trial.trial_id for trial in trials],
            "warnings": warnings,
        }

    def run_trial(self, experiment_id: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        config = self.repo.get_experiment(experiment_id)
        trials = self.repo.list_trials(experiment_id)
        trial_id = self.repo.next_trial_id()
        iteration = len(trials) + 1
        trial_params = dict(params or config.initial_params)
        trial_dir = ensure_dir(Path(config.save_root) / "experiments" / experiment_id / trial_id)
        status = STATE_TRAINING if iteration == 1 else STATE_RETRAINING
        trial = TrialRecord(
            trial_id=trial_id,
            experiment_id=experiment_id,
            iteration=iteration,
            params=trial_params,
            status=status,
            run_dir=str(trial_dir),
        )
        write_json(trial_dir / TRIAL_CONFIG_FILENAME, trial_params)
        self.repo.create_trial(trial)
        self.repo.update_experiment_status(experiment_id, status)
        self.repo.add_event(experiment_id, "TRIAL_STARTED", {"trial_id": trial_id, "params": trial_params}, trial_id)

        try:
            training_result = run_training(
                pretrained_model=config.pretrained_model,
                dataset_yaml=config.dataset_yaml,
                run_dir=str(trial_dir),
                trial_name=trial_id,
                params=trial_params,
            )
            run_dir = training_result["run_dir"]
            previous_summary = None
            summaries = self.repo.recent_summaries(experiment_id, limit=1)
            if summaries:
                previous_summary = summaries[-1]
            self.repo.update_experiment_status(experiment_id, STATE_ANALYZING)
            summary = build_summary(trial_id, run_dir, trial_params, previous_summary).to_dict()
            summary_path = trial_dir / SUMMARY_FILENAME
            write_json(summary_path, summary)
            next_status = self._completion_status(config, summary, iteration)
            self.repo.update_trial(
                trial_id,
                status=next_status,
                metrics=summary["final_metrics"],
                summary_path=str(summary_path),
            )
            self.repo.update_experiment_status(experiment_id, next_status)
            self.repo.add_event(experiment_id, "TRIAL_COMPLETED", summary, trial_id)
            self._notify_training_result(config, trial_id, summary)
            return {
                "status": next_status,
                "trial_id": trial_id,
                "run_dir": run_dir,
                "stdout_log": training_result["stdout_log"],
                "stderr_log": training_result["stderr_log"],
                "summary_path": str(summary_path),
                "final_metrics": summary["final_metrics"],
            }
        except TrainingError as exc:
            self.repo.update_trial(trial_id, status=STATE_FAILED)
            self.repo.update_experiment_status(experiment_id, STATE_FAILED)
            self.repo.add_event(experiment_id, "TRIAL_FAILED", {"trial_id": trial_id, "error": str(exc)}, trial_id)
            raise ServiceError(str(exc)) from exc

    def get_summary(self, trial_id: str, compact: bool = False) -> dict[str, Any]:
        trial = self.repo.get_trial(trial_id)
        if not trial.summary_path:
            raise ServiceError(f"trial has no summary yet: {trial_id}")
        summary = read_json(trial.summary_path)
        if compact:
            return {
                "trial_id": trial_id,
                "final_metrics": summary.get("final_metrics", {}),
                "delta_vs_prev": summary.get("delta_vs_prev", {}),
                "training_dynamics": summary.get("training_dynamics", {}),
                "warnings": summary.get("warnings", []),
            }
        return summary

    def propose_next(self, experiment_id: str) -> dict[str, Any]:
        config = self.repo.get_experiment(experiment_id)
        trials = self.repo.list_trials(experiment_id)
        if not trials:
            raise ServiceError("cannot propose next step before the first trial exists")
        latest_trial = trials[-1]
        if not latest_trial.summary_path:
            raise ServiceError("latest trial has no summary")
        latest_summary = read_json(latest_trial.summary_path)
        target_reached = float(latest_summary["final_metrics"].get(config.goal.metric, 0.0)) >= config.goal.target
        if target_reached:
            proposal = {
                "decision": "stop",
                "param_updates": {},
                "reason": f"target reached for {config.goal.metric}",
            }
        else:
            recent_trials = trials[-2:]
            payload = {
                "task": {
                    "experiment_id": config.experiment_id,
                    "description": config.description,
                    "task_type": config.task_type,
                    "status": config.status,
                },
                "goal": config.goal.__dict__,
                "stop_conditions": config.stop_conditions,
                "allowed_updates": {
                    "max_param_changes": 3,
                    "search_space": _compact_search_space(config.search_space),
                },
                "latest_summary": _compact_summary(latest_summary),
                "latest_trial": {
                    "trial_id": latest_trial.trial_id,
                    "iteration": latest_trial.iteration,
                    "status": latest_trial.status,
                    "params": latest_trial.params,
                    "metrics": latest_trial.metrics,
                },
                "recent_trials": [
                    {
                        "trial_id": trial.trial_id,
                        "iteration": trial.iteration,
                        "status": trial.status,
                        "params": trial.params,
                        "metrics": trial.metrics,
                    }
                    for trial in recent_trials
                ],
            }
            try:
                proposal = request_next_step(payload)
            except LLMAdapterError as exc:
                raise ServiceError(str(exc)) from exc

        try:
            validated = validate_proposal(proposal, target_reached=target_reached)
        except ProposalValidationError as exc:
            raise ServiceError(str(exc)) from exc
        self.repo.update_experiment_status(experiment_id, STATE_AUTO_TUNE)
        self.repo.add_event(experiment_id, "NEXT_PROPOSAL", validated, latest_trial.trial_id)
        return validated

    def continue_experiment(self, experiment_id: str) -> dict[str, Any]:
        proposal = self.repo.latest_event(experiment_id, "NEXT_PROPOSAL")
        if proposal is None:
            raise ServiceError("no validated proposal found; run propose-next first")
        if proposal["decision"] == "stop":
            self.repo.update_experiment_status(experiment_id, STATE_COMPLETED)
            return {"status": STATE_COMPLETED, "decision": "stop", "reason": proposal["reason"]}

        trials = self.repo.list_trials(experiment_id)
        if not trials:
            raise ServiceError("cannot continue an experiment without trials")
        params = dict(trials[-1].params)
        params.update(proposal["param_updates"])
        result = self.run_trial(experiment_id, params=params)
        result["applied_updates"] = proposal["param_updates"]
        result["reason"] = proposal["reason"]
        return result

    def _completion_status(
        self,
        config: ExperimentConfig,
        summary: dict[str, Any],
        trial_count: int,
    ) -> str:
        metric_value = float(summary["final_metrics"].get(config.goal.metric, 0.0))
        if metric_value >= config.goal.target:
            return STATE_COMPLETED
        if trial_count >= int(config.stop_conditions["max_trials"]):
            return STATE_COMPLETED
        return STATE_WAITING

    def _notify_training_result(
        self,
        config: ExperimentConfig,
        trial_id: str,
        summary: dict[str, Any],
    ) -> None:
        try:
            session_id = _resolve_session_id(config.session_key)
            compact_summary = _notification_summary(summary)
            message = _build_notify_message(config, trial_id, compact_summary)
            _notify_openclaw_session(session_id, message)
            self.repo.add_event(
                config.experiment_id,
                "OPENCLAW_NOTIFY_SENT",
                {
                    "trial_id": trial_id,
                    "session_key": config.session_key,
                    "session_id": session_id,
                    "compact_summary": compact_summary,
                },
                trial_id,
            )
        except ServiceError as exc:
            self.repo.add_event(
                config.experiment_id,
                "OPENCLAW_NOTIFY_FAILED",
                {
                    "trial_id": trial_id,
                    "session_key": config.session_key,
                    "error": str(exc),
                },
                trial_id,
            )
