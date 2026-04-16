# Command Patterns

WSL / OpenClaw should use:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py <subcommand> ...
```

Core commands:

- `list-tasks`
- `show-task --experiment-id <id>`
- `inspect-dataset --dataset-root <path>`
- `create-task --description "<text>" --task-type detection --dataset-root <path> --pretrained <model> --save-root <path> --goal metric=map50_95,target=<target>`
- `run-trial --experiment-id <id>`
- `get-job --job-id <id>`
- `get-summary --trial-id <id>`
- `propose-next --experiment-id <id>`
- `continue --experiment-id <id>`
- `cancel-task --experiment-id <id> --reason "<text>"`
- `delete-task --experiment-id <id>`

Notes:

- `run-trial` and `continue` are async through the bridge and return `job_id`
- use compact output by default; add `--full` only when needed
- `create-task --goal` accepts `metric=map50_95,target=0.65`, `map50_95=0.65`, or JSON
