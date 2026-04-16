---
name: openclaw-yolo-agent
description: Operate the local openclaw-yolo training system for task creation, async training, summary review, constrained iteration, and task management.
---

# OpenClaw YOLO Agent

Use this skill as the only control surface for YOLO training. Do not call Ultralytics directly, do not edit SQLite manually, and do not infer state from raw folders when a command can answer it.

Assume the repo path is `/mnt/d/project/openclaw_yolo` unless the user says otherwise.

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

1. If dataset YAML is unknown, run `inspect-dataset`
2. Create the task with `create-task`
3. Start training with `run-trial`
4. Poll with `get-job` until `completed` or `failed`
5. Review results with `show-task` and `get-summary`
6. If needed, call `propose-next`
7. Apply the validated proposal with `continue`

## Rules

- Do not guess IDs; read them from prior command output
- Do not feed `stdout.log` or `stderr.log` into model context unless debugging a failure
- Do not manually edit parameters between iterations; use `propose-next` then `continue`
- If the task is already `COMPLETED`, do not continue unless the user explicitly wants a new optimization target
- If a weight file is invalid, stop and ask for a valid model path or filename
- If `OPENCLAW_YOLO_LLM_COMMAND` is missing, explain that proposal generation is unavailable instead of inventing updates
- Use `delete-task` for cleanup instead of manual file or DB deletion

## References

- [references/commands.md](references/commands.md)
- [references/constraints.md](references/constraints.md)
