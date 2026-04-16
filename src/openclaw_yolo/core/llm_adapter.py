from __future__ import annotations

import json
import os
import subprocess
from typing import Any


class LLMAdapterError(RuntimeError):
    pass


def request_next_step(payload: dict[str, Any]) -> dict[str, Any]:
    command = os.environ.get("OPENCLAW_YOLO_LLM_COMMAND")
    if not command:
        raise LLMAdapterError(
            "OPENCLAW_YOLO_LLM_COMMAND is not set; configure an external LLM bridge command"
        )

    process = subprocess.run(
        command,
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        shell=True,
        check=False,
    )
    if process.returncode != 0:
        raise LLMAdapterError(process.stderr.strip() or "LLM command failed")
    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise LLMAdapterError("LLM command returned invalid JSON") from exc
