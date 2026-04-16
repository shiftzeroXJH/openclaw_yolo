---
name: openclaw-yolo-agent
description: Operate the local openclaw-yolo training system through its CLI for dataset inspection, task creation, trial execution, summary review, constrained parameter iteration, and task management. Use when OpenClaw needs to control YOLO training in the local `mamba` environment `yolo_env`, especially for commands like create-task, run-trial, get-summary, propose-next, continue, list-tasks, show-task, or cancel-task.
---

# OpenClaw YOLO Agent

Use the local `openclaw-yolo` CLI as the only control surface for training. Do not call Ultralytics directly, do not edit the SQLite state manually, and do not infer experiment state from raw run folders when a CLI command can provide the answer.

Assume the project repository lives at `/mnt/d/project/openclaw_yolo` unless the user explicitly says it has moved. Build all client-script calls from that absolute path. Do not rely on the current working directory.

## Quick Start

Run commands according to where OpenClaw is deployed.

- If OpenClaw runs on Windows inside `yolo_env`, call `openclaw-yolo ...` directly.
- If OpenClaw runs in WSL while `yolo_env` exists on Windows, call `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py ...`.
- The Windows side must have the bridge service running through `bin/openclaw-yolo-bridge-win.ps1`.

Start by checking available tasks or dataset structure before taking action. Prefer compact responses unless full detail is required:

- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py list-tasks`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py inspect-dataset --dataset-root <path>`

## Workflow

### 1. Create a task

Use `inspect-dataset` first if the dataset YAML is not already known.

Create a task with a short description that helps humans distinguish experiments:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py create-task --description "jinqiu baseline" --task-type detection --dataset-root E:\datasets\jinqiu --pretrained yolo26n.pt --save-root D:\project\openclaw_yolo\runs --goal metric=map50_95,target=0.65 --workers 2 --batch 8
```

Treat the returned `experiment_id` as the task identifier. It remains stable across all later iterations. Do not invent or guess IDs.

### 2. Run the first trial

Start the first training run with:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py run-trial --experiment-id exp_001
```

This returns a `job_id` immediately. Poll it with:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py get-job --job-id <job_id>
```

When the job reaches `completed`, read `trial_id`, `summary_path`, `stdout_log`, `stderr_log`, and `final_metrics` from the job result.
Do not inject `stdout.log` or `stderr.log` into model context by default.

### 3. Review the result

Use compact summary by default:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py get-summary --trial-id trial_001
```

Only use `--full` when compact fields are insufficient.

Focus on:

- `final_metrics`
- `delta_vs_prev`
- `training_dynamics`
- `warnings`

If the task has already met its goal or is marked `COMPLETED`, do not propose more training unless the user explicitly asks for a new optimization target.

### 4. Continue iteration

Only use:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py propose-next --experiment-id exp_001
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py continue --experiment-id exp_001
```

`continue` is also asynchronous through the bridge. Poll the returned `job_id` until completion.
Do not bypass `propose-next` by manually editing parameters between iterations. The code validates every suggested update before `continue`.

### 5. Manage tasks

Use these commands for visibility and recovery:

- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py list-tasks`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py show-task --experiment-id exp_001`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py cancel-task --experiment-id exp_001 --reason "bad pretrained weight"`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py delete-task --experiment-id exp_001`

Cancel broken or obsolete tasks instead of reusing them.

## Parameter Rules

First-trial parameters come from:

1. task baseline
2. explicit user overrides passed to `create-task`

Later iterations may only change parameters accepted by the code-level validator.

Use [references/constraints.md](references/constraints.md) when choosing or explaining parameter changes.

Important rules:

- At most 3 parameters may change in one iteration.
- Only declared parameters may be updated.
- Some parameters use numeric ranges.
- Some parameters use discrete choices.
- `imgsz` must be a multiple of `32`.
- `workers` defaults to `2` and should stay conservative on memory-constrained systems.

## Operating Rules

- Prefer `yolo26n.pt` or another known-good local weight if a local file looks truncated or invalid.
- If `create-task` or `run-trial` returns a weight-file error, stop and ask for a valid pretrained model path or filename.
- If `propose-next` fails because `OPENCLAW_YOLO_LLM_COMMAND` is unset, explain that the external LLM bridge is missing instead of guessing updates locally.
- Keep responses grounded in CLI JSON output; do not summarize imaginary metrics.
- Prefer `summary.json` over raw training logs. Only inspect `stdout.log` or `stderr.log` when debugging a failed run.
- Prefer compact `list-tasks`, `show-task`, and `get-summary` output. Only use `--full` when the user explicitly asks for full detail or compact output is insufficient.
- When the user asks to "continue" a completed task, explain that the current experiment has already reached `COMPLETED` and suggest creating a new experiment with a new goal.
- Use `delete-task` for historical cleanup instead of telling the user to delete folders or SQLite rows manually.
- Only delete non-finalized tasks when the user explicitly asks for forceful cleanup.

## References

- Read [references/commands.md](references/commands.md) for command patterns and expected usage.
- Read [references/constraints.md](references/constraints.md) when selecting parameter values or explaining why a suggested change is rejected.
