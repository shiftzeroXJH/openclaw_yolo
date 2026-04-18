# Command Patterns

WSL / OpenClaw should use:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py <subcommand> ...
```

Do not rely on the current working directory. Use absolute paths under `/mnt/d/project/openclaw_yolo`.

Core commands:

- `list-tasks`
- `show-task --experiment-id <id>`
- `inspect-dataset --dataset-root <path>`
- `create-task --description "<text>" --session-key "<session_key>" --task-type detection --dataset-root <path> --pretrained <model> --save-root <path> --goal metric=map50_95,target=<target>`
- `run-trial --experiment-id <id>`
- `get-job --job-id <id>`
- `get-summary --trial-id <id>`
- `continue --experiment-id <id> --reason "<text>" [--imgsz <value>] [--batch <value>] ...`
- `cancel-task --experiment-id <id> --reason "<text>"`
- `delete-task --experiment-id <id>`

Notes:

- Always run `inspect-dataset` before `create-task` unless the dataset YAML is already confirmed
- `create-task` requires a valid OpenClaw `session_key`; if unknown, resolve it before creating the task
- `run-trial` and `continue` are async through the bridge and return `job_id`
- after training completes, use `show-task` and `get-summary` to analyze the result before deciding whether to call `continue`
- use compact output by default; add `--full` only when needed
- use JSON returned by commands as the source of truth; do not invent metrics or IDs
- if a task is already `COMPLETED`, do not call `continue`; create a new task instead
- `create-task --goal` accepts `metric=map50_95,target=0.65`, `map50_95=0.65`, or JSON
