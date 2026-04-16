# Command Patterns

## Environment

For the current deployment shape:

- OpenClaw runs in WSL
- `yolo_env` and `openclaw-yolo` live on Windows
- A Windows bridge service must be running first

Start the bridge on Windows:

```powershell
powershell -ExecutionPolicy Bypass -File D:\project\openclaw_yolo\bin\openclaw-yolo-bridge-win.ps1
```

Use the WSL HTTP client:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py <subcommand> ...
```

## Core Commands

Inspect a dataset:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py inspect-dataset --dataset-root E:\datasets\jinqiu
```

Create a task:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py create-task --description "jinqiu baseline" --task-type detection --dataset-root E:\datasets\jinqiu --pretrained yolo26n.pt --save-root D:\project\openclaw_yolo\runs --goal metric=map50_95,target=0.65 --workers 2 --batch 8
```

Run the first trial:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py run-trial --experiment-id exp_001
```

Poll one async job:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py get-job --job-id job_xxx
```

Read the summary:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py get-summary --trial-id trial_001
```

Ask for the next step:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py propose-next --experiment-id exp_001
```

Apply the validated proposal:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py continue --experiment-id exp_001
```

List tasks:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py list-tasks
```

Show one task:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py show-task --experiment-id exp_001
```

Cancel one task:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py cancel-task --experiment-id exp_001 --reason "bad pretrained weight"
```

Delete one historical task:

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py delete-task --experiment-id exp_001
```

## Notes

- `experiment_id` identifies one full task.
- `trial_id` identifies one run inside an experiment.
- Do not guess IDs. Use the JSON returned by previous commands.
- `run-trial` returns log file paths. Treat them as debugging artifacts, not normal model context.
- Through the HTTP bridge, `run-trial` and `continue` return async `job_id` values first.
- `delete-task` removes both database records and the experiment directory unless `--keep-files` is used.
- `create-task` supports `--goal` in these forms:
  - `metric=map50_95,target=0.65`
  - `map50_95=0.65`
  - JSON object
