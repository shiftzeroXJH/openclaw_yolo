$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pidFile = Join-Path $projectRoot "logs\bridge.pid"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host "bridge.pid not found. Bridge may already be stopped."
} else {
    $pidText = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    if ($pidText) {
        $bridgePid = [int]$pidText
        $process = Get-Process -Id $bridgePid -ErrorAction SilentlyContinue
        if ($null -eq $process) {
            Write-Host "Bridge process $bridgePid is not running. Removed stale pid file."
        } else {
            & taskkill /F /T /PID $bridgePid *>&1 | Out-Null
            Start-Sleep -Milliseconds 300
            Write-Host "Bridge process $bridgePid stopped."
        }
    } else {
        Write-Host "bridge.pid was empty and has been removed."
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

$ghosts = Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue |
    Where-Object State -eq 'Listen' |
    Select-Object -ExpandProperty OwningProcess
if ($ghosts) {
    foreach ($ghostPid in $ghosts) {
        Stop-Process -Id $ghostPid -Force -ErrorAction SilentlyContinue
        Write-Host "Killed orphaned process $ghostPid still binding port 8765."
    }
}
