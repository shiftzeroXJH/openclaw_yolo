---
name: openclaw-yolo-agent
description: Operate the local openclaw-yolo training system for task creation, async training, summary review, constrained iteration, and task management.
---

# OpenClaw YOLO Agent

Use this skill as the only control surface for YOLO training through the local bridge client. Do not call Ultralytics directly, do not edit SQLite manually, and do not infer state from raw folders when a command can answer it.

Assume the repo path is `/mnt/d/project/openclaw_yolo` unless the user says otherwise.
All commands must use absolute paths under `/mnt/d/project/openclaw_yolo`. Do not rely on the current working directory.

## Runtime

- Use the bridge client everywhere: `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py ...`
- Windows bridge must already be running for WSL/OpenClaw use

## Default Behavior

- For a user-confirmed new training request, use the Fast Path below.
- Use `list-tasks` first only when the user asks about existing tasks or does not identify the dataset/task.
- Prefer compact output for `list-tasks`, `show-task`, and `get-summary`
- Use `--full` only when compact output is insufficient
- Treat `experiment_id` as the stable task ID
- Treat `trial_id` as one run inside a task
- Treat `job_id` as the async handle for `run-trial` and `continue`
- Use the real task type when it is known: `detection`, `segment`, or `obb`. The training worker follows the model file, but summary parsing depends on `task_type`.

## Fast Path for User-Confirmed Training

Use this path when the user asks to start training and provides or clearly implies a dataset root.

1. Run exactly one `inspect-dataset`.
2. If it returns exactly one YAML candidate, do not read the YAML file manually.
3. Obtain the current OpenClaw `session_key` using the shortest available method.
4. Run `create-task`; omit `--save-root` unless the user explicitly requested a custom output directory.
5. Immediately run `run-trial`.
6. Do not call `list-tasks`, `show-task`, or `get-summary` before training starts.
7. After `run-trial`, report only `experiment_id` and `job_id`.

If `inspect-dataset` fails because the path is in the wrong OS format, convert between Windows and WSL path forms once and retry once. Do not explore parent directories unless the retry also fails.

## Callback Fast Path

Use this path when receiving an automatic training-completed callback.

1. If the callback includes a summary payload, do not call tools by default.
2. Reply in Chinese with only the key metrics, target judgment, training dynamics, and next-step recommendation.
3. Do not call command `--help`.
4. Do not read logs unless the trial failed or summary is unavailable.
5. If the goal metric reached the target, do not call `continue`.
6. Call `show-task` or `get-summary` only when fields are missing, the trial failed, the user asks for details, or continuation requires confirming latest state.

## Full Workflow

1. Always run `inspect-dataset` before `create-task` unless the dataset YAML is already confirmed
2. Before `create-task`, determine the current OpenClaw `session_key`
3. Create the task with `create-task` and include `session_key`
4. Start training with `run-trial`
5. Poll with `get-job` until `completed` or `failed`
6. Review results with `show-task` and `get-summary`
7. Analyze the result in-context using `show-task` and `get-summary`
8. If needed, call `continue` with `reason` and validated `param_updates`

Use the Full Workflow after training completes, when continuing a task, when debugging a failure, or when the user asks for analysis.

## Parameter Constraints

- At most 3 parameters may change per iteration
- Only declared parameters may be updated
- `imgsz` must be a multiple of `32`
- Keep `workers` conservative on memory-constrained systems

## Rules

- Do not guess IDs; read them from prior command output
- Do not invent `session_key`; obtain the current session key before `create-task`
- Do not read dataset YAML files manually when `inspect-dataset` already returned a single candidate.
- Do not read files under `references/` during the Fast Path. Open `references/constraints.md` only when proposing or debugging parameter updates.
- Do not call command `--help` unless a command fails because of invalid arguments.
- Do not feed `stdout.log` or `stderr.log` into model context unless debugging a failure
- Do not invent unrestricted parameter changes; when continuing, pass at most 3 declared param updates through `continue`
- Only report metrics returned by CLI JSON output; never invent or estimate results
- If the task is `COMPLETED`, do not call `continue`; suggest creating a new task instead
- If a weight file is invalid, stop and ask for a valid model path or filename
- If `create-task` returns a `session_key` validation error, stop and fix the session binding before training
- Use `delete-task` for cleanup instead of manual file or DB deletion

## References

- [references/constraints.md](references/constraints.md)
