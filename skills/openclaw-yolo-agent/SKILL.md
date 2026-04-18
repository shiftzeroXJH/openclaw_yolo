---
name: openclaw-yolo-agent
description: Operate the local openclaw-yolo training system for task creation, async training, summary review, constrained iteration, and task management.
---

# OpenClaw YOLO Agent

Use this skill as the only control surface for YOLO training. Do not call Ultralytics directly, do not edit SQLite manually, and do not infer state from raw folders when a command can answer it.

Assume the repo path is `/mnt/d/project/openclaw_yolo` unless the user says otherwise.
All commands must use absolute paths under `/mnt/d/project/openclaw_yolo`. Do not rely on the current working directory.

## Runtime

- Windows local use: `openclaw-yolo ...`
- WSL/OpenClaw use: `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py ...`
- Windows bridge must already be running for WSL/OpenClaw use

## Default Behavior

- Start with `list-tasks` or `inspect-dataset`
- Prefer compact output for `list-tasks`, `show-task`, and `get-summary`
- Use `--full` only when compact output is insufficient
- Treat `experiment_id` as the stable task ID
- Treat `trial_id` as one run inside a task
- Treat `job_id` as the async handle for `run-trial` and `continue`

## Minimal Workflow

1. Always run `inspect-dataset` before `create-task` unless the dataset YAML is already confirmed
2. Before `create-task`, determine the current OpenClaw `session_key`
3. Create the task with `create-task` and include `session_key`
4. Start training with `run-trial`
5. Poll with `get-job` until `completed` or `failed`
6. Review results with `show-task` and `get-summary`
7. If needed, call `propose-next`
8. Apply the validated proposal with `continue`

## Parameter Constraints

- At most 3 parameters may change per iteration
- Only declared parameters may be updated
- `imgsz` must be a multiple of `32`
- Keep `workers` conservative on memory-constrained systems

## Rules

- Do not guess IDs; read them from prior command output
- Do not invent `session_key`; obtain the current session key before `create-task`
- Do not feed `stdout.log` or `stderr.log` into model context unless debugging a failure
- Do not manually edit parameters between iterations; use `propose-next` then `continue`
- Only report metrics returned by CLI JSON output; never invent or estimate results
- If the task is `COMPLETED`, do not call `continue`; suggest creating a new task instead
- If a weight file is invalid, stop and ask for a valid model path or filename
- If `create-task` returns a `session_key` validation error, stop and fix the session binding before training
- If `OPENCLAW_YOLO_LLM_COMMAND` is missing, explain that proposal generation is unavailable instead of inventing updates
- Use `delete-task` for cleanup instead of manual file or DB deletion

## References

- [references/commands.md](references/commands.md)
- [references/constraints.md](references/constraints.md)
