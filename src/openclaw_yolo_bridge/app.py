from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
import uvicorn

from openclaw_yolo.service import OrchestratorService, ServiceError
from openclaw_yolo_bridge.jobs import JobStore

app = FastAPI(title="openclaw-yolo-bridge", version="0.1.0")
job_store = JobStore()
service = OrchestratorService(db_path=os.environ.get("OPENCLAW_YOLO_BRIDGE_DB_PATH"))


def _invoke_sync(action: str, callback: Any) -> dict[str, Any]:
    try:
        return callback()
    except (ServiceError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc), "action": action}) from exc


def _invoke_async(kind: str, experiment_id: str, callback: Any) -> dict[str, Any]:
    job = job_store.start(kind, experiment_id, callback)
    return {
        "job_id": job.job_id,
        "kind": job.kind,
        "experiment_id": job.experiment_id,
        "status": job.status,
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/tasks")
def list_tasks(compact: bool = False) -> dict[str, Any]:
    return _invoke_sync("list-tasks", lambda: service.list_tasks(compact=compact))


@app.get("/api/experiments")
def list_experiments() -> dict[str, Any]:
    return _invoke_sync("list-experiments", service.list_experiments)


@app.post("/api/experiments")
def create_experiment(payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    return _invoke_sync(
        "create-experiment",
        lambda: service.create_experiment(
            description=body.get("description", ""),
            task_type=body["task_type"],
            dataset_root=body["dataset_root"],
            dataset_yaml=body.get("dataset_yaml"),
            pretrained=body["pretrained"],
            save_root=body["save_root"],
            goal=body["goal"],
            initial_params=body.get("initial_params"),
            session_key=body.get("session_key"),
            auto_iterate=bool(body.get("auto_iterate", False)),
            confirm_timeout=int(body.get("confirm_timeout", 60)),
        ),
    )


@app.get("/api/experiments/{experiment_id}")
def get_experiment(experiment_id: str) -> dict[str, Any]:
    return _invoke_sync("get-experiment", lambda: service.get_experiment_detail(experiment_id))


@app.delete("/api/experiments/{experiment_id}")
def delete_experiment(experiment_id: str, keep_files: bool = False, force: bool = False) -> dict[str, Any]:
    return _invoke_sync(
        "delete-experiment",
        lambda: service.delete_task(experiment_id, keep_files=keep_files, force=force),
    )


@app.get("/api/experiments/{experiment_id}/comparison")
def compare_experiment(experiment_id: str) -> dict[str, Any]:
    return _invoke_sync("compare-experiment", lambda: service.compare_experiment(experiment_id))


@app.get("/api/experiments/{experiment_id}/params")
def get_experiment_params(experiment_id: str) -> dict[str, Any]:
    return _invoke_sync("get-experiment-params", lambda: service.get_param_metadata(experiment_id))


@app.post("/api/experiments/{experiment_id}/params/validate")
def validate_experiment_params(experiment_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    return _invoke_sync(
        "validate-experiment-params",
        lambda: service.validate_params(
            experiment_id,
            params=body.get("params"),
            param_updates=body.get("param_updates"),
        ),
    )


@app.post("/api/experiments/{experiment_id}/trials/run")
def run_experiment_trial(experiment_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = dict(payload or {})
    return _invoke_async(
        "run-experiment-trial",
        experiment_id,
        lambda: service.run_trial(
            experiment_id,
            params=body.get("params"),
            note=body.get("note"),
            reason=body.get("reason"),
        ),
    )


@app.post("/api/experiments/{experiment_id}/trials/import")
def import_experiment_trial(experiment_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    return _invoke_sync(
        "import-experiment-trial",
        lambda: service.import_run(
            experiment_id,
            run_dir=body["run_dir"],
            params=body.get("params"),
            note=body.get("note"),
        ),
    )


@app.get("/api/trials/{trial_id}/summary")
def get_api_summary(trial_id: str, compact: bool = False) -> dict[str, Any]:
    return _invoke_sync("get-api-summary", lambda: service.get_summary(trial_id, compact=compact))


@app.delete("/api/trials/{trial_id}")
def delete_trial(trial_id: str, keep_files: bool = False, force: bool = False) -> dict[str, Any]:
    return _invoke_sync(
        "delete-trial",
        lambda: service.delete_trial(trial_id, keep_files=keep_files, force=force),
    )


@app.get("/tasks/{experiment_id}")
def show_task(experiment_id: str, compact: bool = False) -> dict[str, Any]:
    return _invoke_sync("show-task", lambda: service.show_task(experiment_id, compact=compact))


@app.post("/tasks")
def create_task(payload: dict[str, Any]) -> dict[str, Any]:
    known_keys = {
        "description",
        "session_key",
        "task_type",
        "dataset_root",
        "dataset_yaml",
        "pretrained",
        "save_root",
        "goal",
        "auto_iterate",
        "confirm_timeout",
    }
    body = dict(payload)
    initial_overrides = {key: body.pop(key) for key in list(body.keys()) if key not in known_keys}
    body["initial_overrides"] = initial_overrides
    return _invoke_sync("create-task", lambda: service.create_task(**body))


@app.post("/tasks/{experiment_id}/run")
def run_trial(experiment_id: str) -> dict[str, Any]:
    return _invoke_async("run-trial", experiment_id, lambda: service.run_trial(experiment_id))


@app.post("/tasks/{experiment_id}/continue")
def continue_task(experiment_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = dict(payload or {})
    return _invoke_async(
        "continue",
        experiment_id,
        lambda: service.continue_experiment(
            experiment_id,
            param_updates=body.get("param_updates"),
            reason=body.get("reason"),
        ),
    )


@app.post("/tasks/{experiment_id}/cancel")
def cancel_task(experiment_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = dict(payload or {})
    return _invoke_sync("cancel-task", lambda: service.cancel_task(experiment_id, body.get("reason")))


@app.delete("/tasks/{experiment_id}")
def delete_task(experiment_id: str, keep_files: bool = False, force: bool = False) -> dict[str, Any]:
    return _invoke_sync(
        "delete-task",
        lambda: service.delete_task(experiment_id, keep_files=keep_files, force=force),
    )


@app.get("/trials/{trial_id}/summary")
def get_summary(trial_id: str, compact: bool = False) -> dict[str, Any]:
    return _invoke_sync("get-summary", lambda: service.get_summary(trial_id, compact=compact))


@app.get("/inspect-dataset")
def inspect_dataset(dataset_root: str) -> dict[str, Any]:
    return _invoke_sync("inspect-dataset", lambda: service.inspect_dataset(dataset_root))


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    return _invoke_sync("get-job", lambda: job_store.get(job_id).to_dict())


def main() -> None:
    uvicorn.run(
        "openclaw_yolo_bridge.app:app",
        host="127.0.0.1",
        port=8765,
        reload=False,
    )


if __name__ == "__main__":  # pragma: no cover
    main()
