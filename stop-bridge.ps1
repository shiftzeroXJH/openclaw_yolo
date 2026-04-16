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
    exit 0
}

Stop-Process -Id $bridgePid -Force
Start-Sleep -Milliseconds 300
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue

Write-Host "Bridge process $bridgePid stopped."
