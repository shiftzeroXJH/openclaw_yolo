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

### 3.1 Delete Experiment

Use the generic API:

```http
DELETE /api/experiments/{experiment_id}?keep_files=true&force=false
```

This deletes the experiment record, its trials, and related events from SQLite. File deletion depends on `keep_files`.

Query parameters:

- `keep_files=true`: keep the training files and only remove the experiment from the manager.
- `keep_files=false`: also delete `save_root/experiments/{experiment_id}`.
- `force=false`: only allow deletion when status is finalized.
- `force=true`: allow deletion even when status is active or waiting.

Finalized statuses:

- `COMPLETED`
- `CANCELLED`
- `FAILED`

Recommended frontend behavior:

- Put delete in an experiment settings menu, not as a primary action.
- Default to `keep_files=true`.
- Label the default action as "Remove from manager".
- Add a separate danger checkbox for "Also delete training files".
- If status is not `COMPLETED`, `CANCELLED`, or `FAILED`, require a second confirmation and call with `force=true`.

Example calls:

```http
DELETE /api/experiments/exp_008?keep_files=true&force=false
```

```http
DELETE /api/experiments/exp_008?keep_files=false&force=true
```

Success response:

```json
{
  "experiment_id": "exp_008",
  "deleted": true,
  "deleted_trials": 1,
  "deleted_events": 4,
  "files_deleted": false,
  "kept_files": true,
  "previous_status": "WAITING_USER_CONFIRM",
  "trial_ids": ["trial_007"],
  "warnings": []
}
```

After success:

- Clear selected experiment if it was deleted.
- Refresh `GET /api/experiments`.
- Show `warnings` if non-empty.

### 3.2 Delete Single Trial

Use this when the user wants to remove one training attempt from an experiment while keeping the experiment/task itself.

```http
DELETE /api/trials/{trial_id}?keep_files=true&force=false
```

This deletes one trial record and its trial events. The parent experiment remains.

Query parameters:

- `keep_files=true`: remove the trial from the manager only.
- `keep_files=false`: also delete files managed under `save_root/experiments/{experiment_id}/{trial_id}`.
- `force=false`: refuse to delete active trials in `TRAINING`, `RETRAINING`, or `ANALYZING`.
- `force=true`: allow deleting an active trial record.

Important safety behavior:

- If a trial was imported from an external YOLO `run_dir`, `keep_files=false` does not delete that external run directory.
- Only files inside this project's managed experiment directory are eligible for deletion.

Example calls:

```http
DELETE /api/trials/trial_007?keep_files=true&force=false
```

```http
DELETE /api/trials/trial_007?keep_files=false&force=true
```

Success response:

```json
{
  "experiment_id": "exp_008",
  "trial_id": "trial_007",
  "deleted": true,
  "deleted_trials": 1,
  "deleted_events": 3,
  "files_deleted": false,
  "deleted_paths": [],
  "kept_files": true,
  "previous_status": "WAITING_USER_CONFIRM",
  "remaining_trial_count": 2,
  "warnings": []
}
```

Recommended frontend behavior:

- Put this action in each trial row's overflow menu.
- Label default action as "Remove trial from manager".
- Default to `keep_files=true`.
- Add a separate danger checkbox for "Also delete managed trial files".
- After success, refresh experiment detail, comparison, params, and experiment list.

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

There are two status fields in the backend:

- `experiment.status`: status of the whole task/experiment.
- `trial.status`: status of one training attempt inside the experiment.

Use different frontend labels in context:

- For `experiment.status`, show it as "Task Status" or "Experiment Status".
- For `trial.status`, show it as "Training Status" or "Trial Status".

Both fields currently reuse the same status strings.

Known current statuses:

- `READY`
- `TRAINING`
- `ANALYZING`
- `WAITING_USER_CONFIRM`
- `RETRAINING`
- `COMPLETED`
- `FAILED`
- `CANCELLED`

Legacy records may also contain:

- `AUTO_TUNE_PENDING`

Treat `AUTO_TUNE_PENDING` like `WAITING_USER_CONFIRM` in the frontend.

### Experiment Status Meaning

| Status | Meaning | Suggested label |
|---|---|---|
| `READY` | Experiment was created and has not started training yet, or all trials were deleted. | 待开始 |
| `TRAINING` | First trial is currently running. | 训练中 |
| `RETRAINING` | A later trial is currently running. | 再训练中 |
| `ANALYZING` | Training finished and the backend is generating/parsing summary data. | 分析中 |
| `WAITING_USER_CONFIRM` | Latest trial finished, target is not reached yet, and the user should decide whether to tune params and run again. | 等待决策 |
| `COMPLETED` | Experiment is finished. It may have reached the target or hit the max-trials stop condition. | 已完成 |
| `FAILED` | Experiment failed due to training/environment/data/model errors. | 失败 |
| `CANCELLED` | User cancelled the experiment. | 已取消 |
| `AUTO_TUNE_PENDING` | Legacy status from older records; treat as waiting for tuning/next decision. | 等待调参 |

### Trial Status Meaning

| Status | Meaning | Suggested label |
|---|---|---|
| `TRAINING` | This trial is actively training. Usually the first run. | 训练中 |
| `RETRAINING` | This trial is actively training as a later run. | 再训练中 |
| `ANALYZING` | Trial output is being analyzed. This is usually transient. | 分析中 |
| `WAITING_USER_CONFIRM` | This trial completed, but the experiment has not reached the target yet. | 已完成，待决策 |
| `COMPLETED` | This trial completed and the experiment is finished. | 已完成 |
| `FAILED` | This trial failed. | 失败 |
| `CANCELLED` | This trial was cancelled. Current cancel behavior is mostly experiment-level. | 已取消 |
| `READY` | Usually not expected on a trial; handle as fallback. | 待开始 |
| `AUTO_TUNE_PENDING` | Legacy status; treat as waiting for tuning. | 等待调参 |

### Status Flow

Typical experiment flow:

```text
create experiment
  -> experiment.status = READY

first trial starts
  -> experiment.status = TRAINING
  -> trial.status = TRAINING

later trial starts
  -> experiment.status = RETRAINING
  -> trial.status = RETRAINING

training finished, summary being built
  -> experiment.status = ANALYZING

summary done, target reached or max trials reached
  -> experiment.status = COMPLETED
  -> trial.status = COMPLETED

summary done, target not reached and can continue
  -> experiment.status = WAITING_USER_CONFIRM
  -> trial.status = WAITING_USER_CONFIRM

training error
  -> experiment.status = FAILED
  -> trial.status = FAILED

user cancels task
  -> experiment.status = CANCELLED
```

### Suggested UI Mapping

Use a shared mapping for visual tone:

```ts
const STATUS_LABELS: Record<string, string> = {
  READY: "待开始",
  TRAINING: "训练中",
  RETRAINING: "再训练中",
  ANALYZING: "分析中",
  WAITING_USER_CONFIRM: "等待决策",
  COMPLETED: "已完成",
  FAILED: "失败",
  CANCELLED: "已取消",
  AUTO_TUNE_PENDING: "等待调参",
};

const STATUS_TONE: Record<
  string,
  "neutral" | "active" | "warning" | "success" | "danger" | "muted"
> = {
  READY: "neutral",
  TRAINING: "active",
  RETRAINING: "active",
  ANALYZING: "active",
  WAITING_USER_CONFIRM: "warning",
  COMPLETED: "success",
  FAILED: "danger",
  CANCELLED: "muted",
  AUTO_TUNE_PENDING: "warning",
};
```

For trial rows, override the label for `WAITING_USER_CONFIRM` to `已完成，待决策` if that reads better in the table.

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
