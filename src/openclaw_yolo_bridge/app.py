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
    except (ServiceError, FileNotFoundError, KeyError, ValueError) as exc:
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


@app.get("/tasks/{experiment_id}")
def show_task(experiment_id: str, compact: bool = False) -> dict[str, Any]:
    return _invoke_sync("show-task", lambda: service.show_task(experiment_id, compact=compact))


@app.post("/tasks")
def create_task(payload: dict[str, Any]) -> dict[str, Any]:
    known_keys = {
        "description",
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


@app.post("/tasks/{experiment_id}/propose-next")
def propose_next(experiment_id: str) -> dict[str, Any]:
    return _invoke_sync("propose-next", lambda: service.propose_next(experiment_id))


@app.post("/tasks/{experiment_id}/continue")
def continue_task(experiment_id: str) -> dict[str, Any]:
    return _invoke_async("continue", experiment_id, lambda: service.continue_experiment(experiment_id))


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
