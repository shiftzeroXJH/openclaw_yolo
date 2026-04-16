$ErrorActionPreference = "Stop"

& mamba run -n yolo_env python -m openclaw_yolo_bridge.app
exit $LASTEXITCODE
