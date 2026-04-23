$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$logDir = Join-Path $projectRoot "logs"
$stdoutLog = Join-Path $logDir "bridge.stdout.log"
$stderrLog = Join-Path $logDir "bridge.stderr.log"
$pidFile = Join-Path $logDir "bridge.pid"
$dbPath = Join-Path $projectRoot "openclaw_yolo_state.sqlite"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (Test-Path -LiteralPath $pidFile) {
    $existingPidText = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    if ($existingPidText) {
        $existingProcess = Get-Process -Id ([int]$existingPidText) -ErrorAction SilentlyContinue
        if ($null -ne $existingProcess) {
            Write-Host "Bridge is already running."
            Write-Host "PID: $existingPidText"
            Write-Host "DB: $dbPath"
            Write-Host "stdout: $stdoutLog"
            Write-Host "stderr: $stderrLog"
            Write-Host "pid file: $pidFile"
            exit 0
        }
    }

    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

$command = @(
    "`$env:OPENCLAW_YOLO_BRIDGE_DB_PATH='$dbPath'"
    "Set-Location '$projectRoot'"
    "& mamba run -n yolo_env python -m openclaw_yolo_bridge.app"
) -join "; "

$process = Start-Process `
    -FilePath "powershell" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $command) `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden `
    -PassThru

Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii

Write-Host "Bridge started in background."
Write-Host "PID: $($process.Id)"
Write-Host "DB: $dbPath"
Write-Host "stdout: $stdoutLog"
Write-Host "stderr: $stderrLog"
Write-Host "pid file: $pidFile"
