$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pidFile = Join-Path $projectRoot "logs\\bridge.pid"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host "bridge.pid not found. Bridge may already be stopped."
    exit 0
}

$pidText = (Get-Content -LiteralPath $pidFile -Raw).Trim()
if (-not $pidText) {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host "bridge.pid was empty and has been removed."
    exit 0
}

$bridgePid = [int]$pidText
$process = Get-Process -Id $bridgePid -ErrorAction SilentlyContinue

if ($null -eq $process) {
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
    Write-Host "Bridge process $bridgePid is not running. Removed stale pid file."
} else {
    # Windows native Stop-Process does not kill child processes.
    # We must use taskkill /T to kill the entire process tree so that the python backend doesn't orphan.
    & taskkill /F /T /PID $bridgePid *>&1 | Out-Null
    Start-Sleep -Milliseconds 300
}

# Bulletproof cleanup: ensure anything left accidentally clinging to port 8765 is purged.
$ghosts = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue | Where-Object State -eq 'Listen' | Select-Object -ExpandProperty OwningProcess
if ($ghosts) {
    foreach ($gh in $ghosts) {
        Stop-Process -Id $gh -Force -ErrorAction SilentlyContinue
        Write-Host "Killed orphaned python process $gh that was still binding port 8765."
    }
}
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue

Write-Host "Bridge process $bridgePid stopped."
