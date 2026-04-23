$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pidFile = Join-Path $projectRoot "logs\frontend.pid"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Host "frontend.pid not found. Frontend may already be stopped."
} else {
    $pidText = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    if ($pidText) {
        $frontendPid = [int]$pidText
        $process = Get-Process -Id $frontendPid -ErrorAction SilentlyContinue
        if ($null -eq $process) {
            Write-Host "Frontend process $frontendPid is not running. Removed stale pid file."
        } else {
            & taskkill /F /T /PID $frontendPid *>&1 | Out-Null
            Start-Sleep -Milliseconds 300
            Write-Host "Frontend process $frontendPid stopped."
        }
    } else {
        Write-Host "frontend.pid was empty and has been removed."
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

$ghosts = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue |
    Where-Object State -eq 'Listen' |
    Select-Object -ExpandProperty OwningProcess
if ($ghosts) {
    foreach ($ghostPid in $ghosts) {
        Stop-Process -Id $ghostPid -Force -ErrorAction SilentlyContinue
        Write-Host "Killed orphaned process $ghostPid still binding port 5173."
    }
}
