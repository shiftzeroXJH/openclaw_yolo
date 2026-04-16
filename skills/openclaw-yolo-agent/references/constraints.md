# Parameter Constraints

The training system validates parameter updates in code. The LLM or OpenClaw may suggest changes, but invalid updates are rejected.

## First-Trial Baseline

Current `detection` defaults:

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

## Validation Model

### Choice-based

- `batch`: `4, 8, 16, 32`
- `workers`: `0, 1, 2, 4, 8`

### Range-based

- `imgsz`: integer `224..1536`, multiple of `32`
- `epochs`: integer `1..1000`
- `lr0`: float `0.00001..0.1`
- `weight_decay`: float `0.0..0.01`
- `mosaic`: float `0.0..1.0`
- `mixup`: float `0.0..1.0`
- `degrees`: float `0.0..45.0`
- `translate`: float `0.0..0.5`
- `scale`: float `0.0..1.0`
- `fliplr`: float `0.0..1.0`
- `hsv_h`: float `0.0..0.1`
- `hsv_s`: float `0.0..1.0`
- `hsv_v`: float `0.0..1.0`

## Iteration Rules

- Modify at most 3 parameters in one iteration.
- Do not suggest undeclared parameters.
- Keep `workers` conservative on memory-limited machines.
- Use `batch` and `imgsz` reductions first when troubleshooting memory pressure.
- If instability appears, prefer lowering `lr0` or reducing aggressive augmentation.
