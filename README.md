# YOLO Experiment Manager

This project is a local backend for managing YOLO experiments. It keeps the useful parts of the original OpenClaw-oriented tool: experiment records, trial history, parameter validation, result summaries, and multi-trial metric comparison.

OpenClaw integration is still available as an adapter, but the core workflow is now useful without OpenClaw.

## What It Does

- Create a YOLO experiment for one dataset, model, and target metric.
- Run multiple trials under the same experiment.
- Validate editable training parameters before starting a trial.
- Import existing YOLO run directories that already contain `results.csv`.
- Generate `summary.json` for every trial.
- Return table-friendly comparison rows for frontend UI.
- Preserve the legacy `/tasks` and bridge client endpoints for OpenClaw compatibility.

The intended frontend is a React/Vue UI that talks to the `/api/experiments` endpoints.

## Core Concepts

- `experiment`
  - A dataset/model/goal container.
  - Example goal: `map50_95 >= 0.65`.

- `trial`
  - One training run or one imported YOLO run.
  - Trials are ordered by `iteration`.
  - Each trial stores params, metrics, summary path, source, note, and reason.

- `summary`
  - A structured summary generated from YOLO `results.csv`.
  - Includes final metrics, metric deltas, best epoch, training dynamics, warnings, resources, and params.

## Running

Install locally:

```powershell
pip install -e . --no-build-isolation
```

For tests and API development:

```powershell
pip install -e .[dev] --no-build-isolation
```

Start the backend bridge on Windows:

```powershell
.\start-bridge.bat
```

Default URL:

```text
http://127.0.0.1:8765
```

This single bridge serves both the Web UI API (`/api/...`) and the OpenClaw-compatible HTTP client endpoints (`/tasks`, `/trials`, `/jobs`).

Start the frontend Web UI:

```powershell
.\start-frontend.bat
```

Frontend URL:

```text
http://127.0.0.1:5173
```

Stop services with:

```powershell
.\stop-frontend.bat
.\stop-bridge.bat
```

For direct development without the background scripts, the backend module can still be run with `python -m openclaw_yolo_bridge.app`, and the frontend can be run from `frontend/` with `npm run dev -- --host 127.0.0.1`.

## Generic Experiment API

List experiments:

```http
GET /api/experiments
```

Create a local experiment:

```http
POST /api/experiments
```

```json
{
  "description": "jinqiu baseline",
  "task_type": "detection",
  "dataset_root": "E:/datasets/jinqiu",
  "pretrained": "yolo26n.pt",
  "save_root": "D:/project/openclaw_yolo/runs",
  "goal": {
    "metric": "map50_95",
    "target": 0.65
  },
  "initial_params": {
    "imgsz": 224,
    "batch": 8,
    "workers": 2
  }
}
```

`session_key` is optional. If it is omitted, no OpenClaw session validation or notification is attempted.

Get experiment detail:

```http
GET /api/experiments/{experiment_id}
```

Delete an experiment:

```http
DELETE /api/experiments/{experiment_id}?keep_files=true&force=false
```

Query parameters:

- `keep_files=true`: delete database records only, keep training files.
- `keep_files=false`: delete database records and the experiment directory under `save_root/experiments/{experiment_id}`.
- `force=false`: only delete finalized experiments.
- `force=true`: delete even if the experiment is not finalized.

Finalized statuses are `COMPLETED`, `CANCELLED`, and `FAILED`.

Delete a single trial record:

```http
DELETE /api/trials/{trial_id}?keep_files=true&force=false
```

This removes one training/import record from its experiment. The experiment remains.

Query parameters:

- `keep_files=true`: delete database record and trial events only.
- `keep_files=false`: also delete files managed under `save_root/experiments/{experiment_id}/{trial_id}`.
- `force=false`: refuse to delete trials currently in `TRAINING`, `RETRAINING`, or `ANALYZING`.
- `force=true`: allow deleting an active trial record.

For imported external YOLO runs, `keep_files=false` does not delete the external `run_dir`; it only deletes files managed inside this project's experiment directory.

Get editable parameter metadata:

```http
GET /api/experiments/{experiment_id}/params
```

Validate parameters before training:

```http
POST /api/experiments/{experiment_id}/params/validate
```

```json
{
  "param_updates": {
    "imgsz": 320,
    "batch": 16,
    "lr0": 0.005,
    "mosaic": 0.3
  }
}
```

Local UI parameter validation is not limited to three changed parameters. The three-parameter limit remains only on the legacy OpenClaw `continue` flow.

Run a new trial:

```http
POST /api/experiments/{experiment_id}/trials/run
```

```json
{
  "params": {
    "imgsz": 320,
    "batch": 16,
    "workers": 2,
    "epochs": 100,
    "lr0": 0.005,
    "weight_decay": 0.0005,
    "mosaic": 0.3,
    "mixup": 0.0,
    "degrees": 0.0,
    "translate": 0.1,
    "scale": 0.5,
    "fliplr": 0.5,
    "hsv_h": 0.015,
    "hsv_s": 0.7,
    "hsv_v": 0.4
  },
  "reason": "manual lower lr sweep",
  "note": "try less augmentation"
}
```

This returns a `job_id`; poll it with:

```http
GET /jobs/{job_id}
```

Import an existing YOLO run:

```http
POST /api/experiments/{experiment_id}/trials/import
```

```json
{
  "run_dir": "D:/project/openclaw_yolo/runs/detect/train42",
  "note": "old baseline"
}
```

The run directory must contain `results.csv`. If it also contains `config.json`, those params are used. Otherwise the latest experiment params are used unless `params` is provided.

Register and monitor a remote YOLO run over SFTP:

```http
POST /api/remote-servers
POST /api/experiments/{experiment_id}/trials/remote-register
POST /api/trials/{trial_id}/remote-sync
```

Remote monitoring does not start training and does not run local validation. The backend briefly reads remote files over SFTP, closes the remote handles, stores local copies under `save_root/remote_cache/{remote_server_id}/{trial_id}`, and parses `results.csv` for curves and metrics. Remote runs must include `args.yaml`; `results.csv` may still be growing while training is in progress. Weight files such as `best.pt` and `last.pt` are not downloaded in this version.

Compare trials:

```http
GET /api/experiments/{experiment_id}/comparison
```

The response contains:

- `columns`: recommended table columns for the frontend.
- `rows`: one row per trial.
- `best_trial`: best row by the experiment goal metric.
- `target_reached`: whether the goal target has been reached.

Get trial summary:

```http
GET /api/trials/{trial_id}/summary
```

## Editable Parameters

The current detection baseline is:

```json
{
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
  "hsv_v": 0.4
}
```

The backend exposes the exact editable schema through:

```http
GET /api/experiments/{experiment_id}/params
```

## OpenClaw Compatibility

The original bridge endpoints remain available:

- `GET /tasks`
- `POST /tasks`
- `GET /tasks/{experiment_id}`
- `DELETE /tasks/{experiment_id}`
- `POST /tasks/{experiment_id}/run`
- `POST /tasks/{experiment_id}/continue`
- `GET /trials/{trial_id}/summary`

The OpenClaw `create-task` path still requires `session_key`, validates it through WSL, and can notify OpenClaw after training. Generic `/api/experiments` does not require OpenClaw.

## Tests

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
$env:PYTHONPATH='src'
python -m pytest -q tests -p no:cacheprovider --basetemp .pytest-tmp
```

The tests use fake `results.csv` files and monkeypatch the YOLO training layer; they do not run real training.
