#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIN_PS1="$(wslpath -w "${SCRIPT_DIR}/openclaw-yolo-win.ps1")"

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$WIN_PS1" "$@"
