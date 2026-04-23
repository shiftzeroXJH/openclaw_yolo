# YOLO Experiment Manager Frontend Brief

Build a React or Vue frontend for a local YOLO experiment management backend.

The frontend should focus on practical experiment work: create experiments, tune training parameters, run or import trials, and compare multiple trial results in a dense table.

## Backend

- Base URL: `http://127.0.0.1:8765`
- Health check: `GET /health`
- API returns JSON.
- Errors use HTTP 400 with this shape:

```json
{
  "detail": {
    "error": "human readable error",
    "action": "action-name"
  }
}
```

Use only the generic `/api/*` endpoints for the main UI. Ignore legacy `/tasks/*` endpoints unless adding an OpenClaw compatibility panel.

## Product Goal

The app is a local YOLO experiment manager, not a marketing site.

The first screen should be the actual workspace:

- Left or top area: experiment list and create button.
- Main area: selected experiment overview, trial comparison table, parameter editor, and actions.
- Detail area: selected trial summary.

Do not build a landing page.

## Core Pages

### 1. Experiments Workspace

Default page.

Load:

```http
GET /api/experiments
```

Expected response:

```json
{
  "experiments": [
    {
      "experiment_id": "exp_001",
      "description": "jinqiu baseline",
      "status": "WAITING_USER_CONFIRM",
      "task_type": "detection",
      "dataset_root": "E:/datasets/jinqiu",
      "dataset_yaml": "E:/datasets/jinqiu/data.yaml",
      "pretrained_model": "yolo26n.pt",
      "goal": {
        "metric": "map50_95",
        "target": 0.65
      },
      "trial_count": 3,
      "best_metric": {
        "trial_id": "trial_002",
        "iteration": 2,
        "metric": "map50_95",
        "value": 0.6123
      },
      "latest_trial": {
        "trial_id": "trial_003",
        "iteration": 3,
        "status": "WAITING_USER_CONFIRM",
        "metrics": {
          "precision": 0.7,
          "recall": 0.6,
          "map50": 0.75,
          "map50_95": 0.61
        },
        "source": "trained"
      }
    }
  ]
}
```

UI requirements:

- Show experiments in a compact list with status, trial count, best metric, and description.
- Selecting an experiment loads detail, comparison, and params.
- Provide a refresh button.
- Show empty state when no experiments exist.

### 2. Create Experiment Dialog

Submit:

```http
POST /api/experiments
```

Request:

```json
{
  "description": "jinqiu baseline",
  "task_type": "detection",
  "dataset_root": "E:/datasets/jinqiu",
  "dataset_yaml": "E:/datasets/jinqiu/data.yaml",
  "pretrained": "yolo26n.pt",
  "save_root": "D:/project/openclaw_yolo/runs",
  "goal": {
    "metric": "map50_95",
    "target": 0.65
  },
  "initial_params": {
    "imgsz": 224,
    "batch": 8,
    "workers": 2,
    "epochs": 100
  }
}
```

Required fields:

- `description`
- `task_type`, default `detection`
- `dataset_root`
- `pretrained`
- `save_root`
- `goal.metric`, default `map50_95`
- `goal.target`

Optional fields:

- `dataset_yaml`
- `initial_params`
- `session_key`

If response status is `needs_dataset_yaml`, show the returned `yaml_candidates` and let the user choose one, then resubmit with `dataset_yaml`.

Response:

```json
{
  "status": "READY",
  "experiment_id": "exp_001",
  "description": "jinqiu baseline",
  "session_key": "",
  "dataset_yaml": "E:/datasets/jinqiu/data.yaml",
  "initial_params": {},
  "experiment_dir": "D:/project/openclaw_yolo/runs/experiments/exp_001"
}
```

### 3. Experiment Detail

Load:

```http
GET /api/experiments/{experiment_id}
```

Use this for:

- dataset/model/goal overview
- trial count
- latest params
- quick trial list

Response shape:

```json
{
  "experiment": {
    "experiment_id": "exp_001",
    "description": "jinqiu baseline",
    "session_key": "",
    "task_type": "detection",
    "dataset_root": "E:/datasets/jinqiu",
    "dataset_yaml": "E:/datasets/jinqiu/data.yaml",
    "pretrained_model": "yolo26n.pt",
    "save_root": "D:/project/openclaw_yolo/runs",
    "goal": {
      "metric": "map50_95",
      "target": 0.65
    },
    "status": "WAITING_USER_CONFIRM",
    "initial_params": {},
    "search_space": {},
    "stop_conditions": {}
  },
  "trial_count": 2,
  "latest_params": {},
  "search_space": {},
  "trials": []
}
```

### 4. Trial Comparison Table

Load:

```http
GET /api/experiments/{experiment_id}/comparison
```

Response:

```json
{
  "experiment_id": "exp_001",
  "goal": {
    "metric": "map50_95",
    "target": 0.65
  },
  "target_reached": false,
  "best_trial": {
    "trial_id": "trial_002",
    "iteration": 2,
    "metric": "map50_95",
    "value": 0.6123
  },
  "columns": [
    {
      "key": "iteration",
      "label": "Iteration"
    }
  ],
  "rows": [
    {
      "iteration": 1,
      "trial_id": "trial_001",
      "status": "WAITING_USER_CONFIRM",
      "source": "trained",
      "precision": 0.72,
      "recall": 0.58,
      "map50": 0.75,
      "map50_95": 0.58,
      "delta_map50_95": 0.58,
      "delta_recall": 0.58,
      "best_epoch": 82,
      "epochs_completed": 100,
      "train_time_sec": 320.5,
      "gpu_mem_peak": 4096,
      "params": {
        "imgsz": 224,
        "batch": 8,
        "workers": 2,
        "epochs": 100,
        "lr0": 0.01,
        "weight_decay": 0.0005,
        "mosaic": 0.5,
        "mixup": 0,
        "degrees": 0,
        "translate": 0.1,
        "scale": 0.5,
        "fliplr": 0.5,
        "hsv_h": 0.015,
        "hsv_s": 0.7,
        "hsv_v": 0.4
      },
      "run_dir": "D:/project/openclaw_yolo/runs/experiments/exp_001/trial_001",
      "summary_path": "D:/project/openclaw_yolo/runs/experiments/exp_001/trial_001/summary.json",
      "note": "baseline",
      "reason": "initial run",
      "logs": {
        "stdout": "D:/.../stdout.log",
        "stderr": "D:/.../stderr.log"
      },
      "is_best": true
    }
  ]
}
```

Table requirements:

- Dense, scannable, sortable table.
- Highlight `is_best` row.
- Show target status near the table header.
- Format metrics to 4 decimal places.
- Show positive deltas in green and negative deltas in red.
- Keep parameter columns compact. Recommended approach:
  - Show key params inline: `imgsz`, `batch`, `epochs`, `lr0`, `mosaic`, `mixup`.
  - Show full params in row expansion or side drawer.
- Clicking a row loads trial summary.

Recommended visible columns:

- iteration
- trial_id
- status
- source
- map50_95
- delta_map50_95
- map50
- precision
- recall
- best_epoch
- epochs_completed
- imgsz
- batch
- epochs
- lr0
- mosaic
- note

### 5. Parameter Editor

Load:

```http
GET /api/experiments/{experiment_id}/params
```

Response:

```json
{
  "experiment_id": "exp_001",
  "task_type": "detection",
  "baseline": {},
  "initial_params": {},
  "latest_params": {},
  "editable_schema": {
    "imgsz": {
      "type": "int",
      "min": 224,
      "max": 1536,
      "step": 32,
      "name": "imgsz",
      "required": true
    },
    "batch": {
      "type": "choice",
      "values": [4, 8, 16, 32],
      "name": "batch",
      "required": true
    }
  },
  "search_space": {}
}
```

Render controls by schema:

- `type=int`: number input or slider with min/max/step.
- `type=float`: number input with min/max.
- `type=choice`: select or segmented control.

Important behavior:

- Start from `latest_params`.
- Allow editing any number of params.
- Validate before run.
- Show validation errors next to fields.
- Provide reset actions:
  - reset to latest params
  - reset to baseline

Validate:

```http
POST /api/experiments/{experiment_id}/params/validate
```

Request:

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
    "mixup": 0,
    "degrees": 0,
    "translate": 0.1,
    "scale": 0.5,
    "fliplr": 0.5,
    "hsv_h": 0.015,
    "hsv_s": 0.7,
    "hsv_v": 0.4
  }
}
```

Response:

```json
{
  "valid": true,
  "normalized_params": {},
  "errors": {},
  "warnings": []
}
```

### 6. Run Trial

Submit:

```http
POST /api/experiments/{experiment_id}/trials/run
```

Request:

```json
{
  "params": {},
  "reason": "increase imgsz and lower lr0",
  "note": "manual sweep"
}
```

Response:

```json
{
  "job_id": "job_xxx",
  "kind": "run-experiment-trial",
  "experiment_id": "exp_001",
  "status": "queued"
}
```

Poll:

```http
GET /jobs/{job_id}
```

Job response:

```json
{
  "job_id": "job_xxx",
  "kind": "run-experiment-trial",
  "experiment_id": "exp_001",
  "status": "running",
  "created_at": "2026-04-23T00:00:00+00:00",
  "updated_at": "2026-04-23T00:00:00+00:00",
  "result": null,
  "error": null,
  "metadata": {}
}
```

When `status=completed`, refresh:

- experiment detail
- comparison
- params
- experiment list

### 7. Import Existing YOLO Run

Submit:

```http
POST /api/experiments/{experiment_id}/trials/import
```

Request:

```json
{
  "run_dir": "D:/project/openclaw_yolo/runs/detect/train42",
  "note": "old baseline"
}
```

Optional `params` can be provided if the run does not have `config.json` and the latest params are not correct.

Response:

```json
{
  "status": "WAITING_USER_CONFIRM",
  "trial_id": "trial_003",
  "run_dir": "D:/project/openclaw_yolo/runs/detect/train42",
  "summary_path": "D:/project/openclaw_yolo/runs/experiments/exp_001/trial_003/summary.json",
  "final_metrics": {
    "precision": 0.7,
    "recall": 0.6,
    "map50": 0.75,
    "map50_95": 0.61
  }
}
```

### 8. Trial Summary Drawer

Load:

```http
GET /api/trials/{trial_id}/summary
```

Use this in a side drawer or modal after clicking a table row.

Important fields:

- `trial`
- `final_metrics`
- `metric_breakdown`
- `delta_vs_prev`
- `training_dynamics`
- `warnings`
- `resource`
- `params`

Show:

- final metrics cards
- metric breakdown table
- warnings list
- training dynamics
- full params table
- run directory and logs paths

## Status Values

Known statuses:

- `READY`
- `TRAINING`
- `ANALYZING`
- `WAITING_USER_CONFIRM`
- `RETRAINING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

Suggested UI mapping:

- `READY`: neutral
- `TRAINING`, `RETRAINING`, `ANALYZING`: active / spinner
- `WAITING_USER_CONFIRM`: warning or attention
- `COMPLETED`: success
- `FAILED`, `CANCELLED`: danger or muted

## Parameter Fields

Current editable fields:

- `imgsz`
- `batch`
- `workers`
- `epochs`
- `lr0`
- `weight_decay`
- `mosaic`
- `mixup`
- `degrees`
- `translate`
- `scale`
- `fliplr`
- `hsv_h`
- `hsv_s`
- `hsv_v`

Use labels that are still compact. Do not hide the original parameter names, because YOLO users recognize them.

## UX Requirements

- The UI should feel like an engineering dashboard, not a consumer landing page.
- Use a dense layout with clear hierarchy.
- Use tables for trial comparison.
- Use a form or drawer for parameter editing.
- Use icons for refresh, run, import, settings, and detail actions.
- Use tooltips for less obvious fields like `mosaic`, `mixup`, `hsv_h`, `hsv_s`, `hsv_v`.
- Do not put cards inside cards.
- Do not use a one-color purple/blue dashboard theme.
- Make long paths readable with truncation and copy buttons.
- Avoid horizontal layout breakage on smaller screens; the comparison table can scroll horizontally.

## Recommended App Structure

Suggested components:

- `App`
- `ExperimentList`
- `CreateExperimentDialog`
- `ExperimentHeader`
- `TrialComparisonTable`
- `TrialSummaryDrawer`
- `ParameterEditor`
- `RunTrialDialog`
- `ImportRunDialog`
- `StatusBadge`
- `MetricCell`
- `PathCell`

Suggested client functions:

- `listExperiments()`
- `createExperiment(payload)`
- `getExperiment(experimentId)`
- `getComparison(experimentId)`
- `getParams(experimentId)`
- `validateParams(experimentId, payload)`
- `runTrial(experimentId, payload)`
- `importTrial(experimentId, payload)`
- `getJob(jobId)`
- `getTrialSummary(trialId)`

## Refresh Strategy

- Refresh experiment list after create, import, run completion.
- Refresh comparison after import or run completion.
- Refresh params after import or run completion because latest params may change.
- Poll jobs every 2 seconds while running.
- Stop polling when job status is `completed` or `failed`.

## Out Of Scope For First Frontend

- User authentication.
- Multi-user collaboration.
- Real-time WebSocket logs.
- Training curve charts.
- Automatic hyperparameter suggestions.
- OpenClaw-specific UI.

The first version should be a reliable local dashboard for creating experiments, tuning parameters, importing runs, and comparing trials.
