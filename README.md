# openclaw-yolo

这是一个给 OpenClaw 调用的本地 YOLO 训练编排系统。它负责把训练任务、实验状态、参数约束、结果分析和多轮迭代统一收口到本地工具里，而不是让大模型直接操作 YOLO 训练细节。

## 项目功能总览

当前整体链路是：

`飞书 -> OpenClaw -> HTTP client -> openclaw-yolo bridge -> YOLO`

这个项目现在已经具备的主要能力有：

- 数据集探测
  - 扫描 `dataset_root` 下常见的 YOLO 数据集配置文件，比如 `data.yaml`
  - 用于在创建任务前确认训练数据入口

- 任务创建
  - 创建一个训练任务，并生成稳定的 `experiment_id`
  - 一个任务对应一个完整目标，例如“把某个 detection 数据集训练到 `map50_95 >= 0.65`”
  - 支持 `description`，方便区分不同实验

- 首轮参数生成
  - 首轮训练参数不是由 LLM 决定，而是由代码基于任务类型 baseline 生成
  - 当前第一版支持 `detection`
  - 用户可以在创建任务时覆盖部分参数，例如 `imgsz`、`batch`、`workers`、数据增强参数等

- 参数约束与白名单控制
  - 后续迭代时，大模型不能随意改任意参数
  - 系统会对参数做代码级校验
  - 当前支持“范围 + 枚举混合约束”
  - 每轮最多只允许改 3 个参数

- 训练执行
  - 调用 Ultralytics YOLO 做真实训练
  - 本地预训练模型支持从 `src/openclaw_yolo/models/` 自动解析
  - 会在训练前检查明显损坏的权重文件，避免训练启动后才报错

- 实验状态管理
  - 使用 SQLite 持久化实验状态
  - 区分：
    - `experiment_id`：一个完整任务
    - `trial_id`：该任务中的某一轮训练
  - 支持任务状态流转，例如 `READY`、`TRAINING`、`WAITING`、`COMPLETED`、`FAILED`、`CANCELLED`

- 训练结果分析
  - 每轮训练后会生成结构化 `summary.json`
  - 包含最终指标、相对上一轮的变化、训练动态和告警信息
  - OpenClaw 后续决策应优先读取 summary，而不是直接读取原始训练日志

- 多轮迭代
  - 支持 `propose-next`
  - 支持 `continue`
  - 也就是首轮训练完成后，可以基于结果决定下一轮是否继续，以及修改哪些参数
  - 这里仍然是“LLM 给建议，代码做校验”

- 任务管理
  - 支持：
    - `list-tasks`
    - `show-task`
    - `cancel-task`
    - `delete-task`
  - 可以查看历史任务、取消坏任务、删除已经完成或废弃的任务

- OpenClaw 集成
  - 由于 OpenClaw 跑在 WSL，而 `yolo_env` 在 Windows，本项目已经额外实现了 HTTP bridge
  - 当前推荐链路不是直接跨系统调 shell，而是：
    - OpenClaw -> `openclaw-yolo-http-client.py`
    - client -> Windows 本地 bridge
    - bridge -> Python service / YOLO

- 异步训练调用
  - 通过 bridge 调用 `run-trial` 和 `continue` 时，已经是异步模式
  - 不会让 OpenClaw 卡在一个长请求上
  - 会先返回 `job_id`，再通过 `get-job` 轮询状态

- 日志隔离
  - 训练日志默认写入 trial 目录中的 `stdout.log` / `stderr.log`
  - 不会把大段训练日志直接塞进大模型上下文

- Token 优化
  - `list-tasks`、`show-task`、`get-summary` 现在默认走 compact 视图
  - 默认只返回高价值字段，减少 OpenClaw 的上下文消耗
  - 只有在明确需要时才用 `--full`

你可以把这个项目理解成三层：

1. 编排层
   - 负责任务、trial、状态、summary、参数验证
2. 执行层
   - 负责实际 YOLO 训练
3. Agent 接入层
   - 负责让 OpenClaw 稳定调用，而不是直接碰训练细节

## 运行环境

- 预期运行环境：`mamba activate yolo_env`
- 本地安装：`pip install -e . --no-build-isolation`
- 真实训练依赖：`ultralytics`
- 本地预训练权重可以放在 `src/openclaw_yolo/models/`

## 系统分工

整体控制流为：

`飞书 -> OpenClaw -> HTTP bridge client -> 本地训练系统 -> YOLO`

训练系统负责：

- 数据集探测
- 实验和 trial 状态管理
- 首轮 baseline 参数生成
- YOLO 训练执行
- summary 生成
- 参数更新校验

OpenClaw 负责：

- 理解用户意图
- 决定调用哪个命令
- 读取结构化 JSON 输出
- 在需要时调用外部 LLM 做下一步参数建议

## 核心概念

- `experiment_id`
  - 表示一个完整任务
  - 在整个任务生命周期内保持不变

- `trial_id`
  - 表示某个任务中的一轮训练
  - 一个 `experiment` 可以有多个 `trial`

- 首轮训练参数
  - 来自 baseline + 用户显式覆盖
  - 不是由 LLM 决定

- 后续迭代参数
  - 只能修改通过代码校验的参数

## CLI 命令

所有命令都返回 JSON，便于 OpenClaw 调用：

- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py inspect-dataset --dataset-root <path>`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py create-task --description "<文本>" --session-key "<session_key>" --task-type detection --dataset-root <path> --pretrained <model> --save-root <path> --goal metric=map50_95,target=0.65`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py run-trial --experiment-id exp_001`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py get-summary --trial-id trial_001`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py list-tasks`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py show-task --experiment-id exp_001`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py cancel-task --experiment-id exp_001 --reason "<文本>"`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py delete-task --experiment-id exp_001`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py propose-next --experiment-id exp_001`
- `python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py continue --experiment-id exp_001`

如果 OpenClaw 运行在 WSL，而 Python 环境在 Windows，优先使用 HTTP bridge：

- Windows 侧启动 bridge：`bin/openclaw-yolo-bridge-win.ps1`
- WSL / OpenClaw 侧调用：`python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py ...`

## 初始参数策略

首轮 trial 参数不由 LLM 决定，而是由下面两部分组成：

1. 任务类型 baseline
2. `create-task` 时传入的用户覆盖参数

`create-task` 现在必须传入有效的 OpenClaw `session_key`，系统会在创建任务时校验该会话是否存在。

当前 `detection` baseline 为：

- `imgsz=640`
- `batch=16`
- `workers=2`
- `epochs=100`
- `lr0=0.01`
- `weight_decay=0.0005`
- `mosaic=0.5`
- `mixup=0.0`
- `degrees=0.0`
- `translate=0.1`
- `scale=0.5`
- `fliplr=0.5`
- `hsv_h=0.015`
- `hsv_s=0.7`
- `hsv_v=0.4`

示例：

```powershell
python .\bin\openclaw-yolo-http-client.py create-task --description "jinqiu low-memory baseline" --session-key "agent:main:feishu:direct:ou_xxx" --task-type detection --dataset-root E:\datasets\jinqiu --pretrained yolo26n.pt --save-root D:\project\openclaw_yolo\runs --goal metric=map50_95,target=0.65 --imgsz 224 --batch 8 --workers 2
```

## 参数约束

LLM 不能修改任意参数。所有参数更新都会经过 `src/openclaw_yolo/constants.py` 中定义的约束校验。

当前是“范围 + 枚举混合约束”，不是纯枚举。

典型约束示例：

- `imgsz`
  - 整数
  - 范围 `224..1536`
  - 必须是 `32` 的倍数

- `epochs`
  - 整数
  - 范围 `1..1000`

- `lr0`
  - 浮点数
  - 范围 `0.00001..0.1`

- `mosaic`
  - 浮点数
  - 范围 `0.0..1.0`

- `mixup`
  - 浮点数
  - 范围 `0.0..1.0`

- `batch`
  - 离散值
  - `[4, 8, 16, 32]`

- `workers`
  - 离散值
  - `[0, 1, 2, 4, 8]`

当前仍然会强制执行这些规则：

- 只能改声明过的参数
- 每轮最多改 3 个参数
- 必须通过类型 / 范围 / 步长 / 离散值校验
- 如果目标已经达成，则拒绝继续训练

## LLM 对接

`propose-next` 依赖外部桥接命令 `OPENCLAW_YOLO_LLM_COMMAND`。

这个桥接命令会从 stdin 接收 JSON，并从 stdout 返回 JSON。例如：

```json
{
  "decision": "continue",
  "param_updates": {
    "imgsz": 224,
    "mosaic": 0.33
  },
  "reason": "降低显存压力并减弱增强强度"
}
```

代码会在执行 `continue` 前再次校验这个输出是否合法。

## HTTP Bridge

如果 OpenClaw 无法在 WSL 中直接执行 Windows 命令，就使用本地 bridge。

Windows 侧启动方式：

```powershell
powershell -ExecutionPolicy Bypass -File D:\project\openclaw_yolo\bin\openclaw-yolo-bridge-win.ps1
```

更方便的项目根目录启动方式：

```powershell
powershell -ExecutionPolicy Bypass -File D:\project\openclaw_yolo\start-bridge.ps1
```

或者直接运行：

```text
D:\project\openclaw_yolo\start-bridge.bat
```

启动脚本会在后台拉起 bridge，并写入：

- `logs/bridge.stdout.log`
- `logs/bridge.stderr.log`
- `logs/bridge.pid`

停止 bridge：

```powershell
powershell -ExecutionPolicy Bypass -File D:\project\openclaw_yolo\stop-bridge.ps1
```

或者：

```text
D:\project\openclaw_yolo\stop-bridge.bat
```

默认 bridge 地址：

```text
http://127.0.0.1:8765
```

WSL 侧 client 调用示例：

```bash
python3 /mnt/d/project/openclaw_yolo/bin/openclaw-yolo-http-client.py list-tasks
```

更简单的项目根目录调用方式：

```bash
bash /mnt/d/project/openclaw_yolo/start-http-client.sh list-tasks
```

当前 client 支持的命令：

- `list-tasks`
- `show-task`
- `inspect-dataset`
- `create-task`
- `run-trial`
- `get-job`
- `get-summary`
- `propose-next`
- `continue`
- `cancel-task`
- `delete-task`

## 清理历史数据

如果要安全删除历史任务，请使用：

```powershell
python .\bin\openclaw-yolo-http-client.py delete-task --experiment-id exp_002
```

默认行为：

- 只允许删除 `COMPLETED`、`CANCELLED`、`FAILED` 状态的任务
- 删除数据库里的 experiment、trials、events
- 删除 `runs/experiments/<experiment_id>` 下的实验目录

可选项：

- 仅删数据库，保留磁盘文件：`--keep-files`
- 强制删除未结束任务：`--force`

如果从 WSL 通过 HTTP client 调：

```bash
bash /mnt/d/project/openclaw_yolo/start-http-client.sh delete-task --experiment-id exp_002
```

## 预训练模型解析规则

当你传入 `--pretrained yolo11n.pt` 时，系统会按这个顺序解析：

- 如果是存在的绝对路径，直接使用
- `src/openclaw_yolo/models/yolo11n.pt`
- 当前工作目录下的相对路径
- 最后才把原始值交给 Ultralytics

代码还会在训练前拦截明显异常的本地文件，例如特别小、明显截断的权重文件。

## 典型使用流程

1. 检查数据集：

```powershell
python .\bin\openclaw-yolo-http-client.py inspect-dataset --dataset-root E:\datasets\jinqiu
```

2. 创建任务：

```powershell
python .\bin\openclaw-yolo-http-client.py create-task --description "jinqiu baseline" --session-key "agent:main:feishu:direct:ou_xxx" --task-type detection --dataset-root E:\datasets\jinqiu --pretrained yolo26n.pt --save-root D:\project\openclaw_yolo\runs --goal metric=map50_95,target=0.65 --workers 2 --batch 8
```

3. 启动首轮训练：

```powershell
python .\bin\openclaw-yolo-http-client.py run-trial --experiment-id exp_002
```

CLI 模式仍然是同步的，但通过 HTTP bridge 时已经是异步模式。通过 bridge / client 调 `run-trial` 时会先返回 `job_id`，然后再轮询这个 job 是否完成。

bridge 轮询方式：

```bash
bash /mnt/d/project/openclaw_yolo/start-http-client.sh get-job --job-id <job_id>
```

训练日志会写到 trial 目录下的 `stdout.log` 和 `stderr.log`，最终结果里也会返回这两个路径。

4. 读取 summary：

```powershell
python .\bin\openclaw-yolo-http-client.py get-summary --trial-id trial_001
```

5. 生成下一轮建议：

```powershell
python .\bin\openclaw-yolo-http-client.py propose-next --experiment-id exp_002
```

6. 应用通过校验的建议并继续：

```powershell
python .\bin\openclaw-yolo-http-client.py continue --experiment-id exp_002
```

## 当前还可以继续增强的方向

目前还没有做，或者后续可以继续加强的方向主要有：

- 更强的 bridge 鉴权
- 更稳定的并发 ID 生成
- 更轻量的 `propose-next` LLM payload
- 更完善的批量清理和归档
- 更瘦的 OpenClaw skill 提示词
