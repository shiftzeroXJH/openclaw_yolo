$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$frontendRoot = Join-Path $projectRoot "frontend"
$logDir = Join-Path $projectRoot "logs"
$stdoutLog = Join-Path $logDir "frontend.stdout.log"
$stderrLog = Join-Path $logDir "frontend.stderr.log"
$pidFile = Join-Path $logDir "frontend.pid"

New-Item -ItemType Directory -Force -Path $logDir | Out-Null

if (Test-Path -LiteralPath $pidFile) {
    $existingPidText = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    if ($existingPidText) {
        $existingProcess = Get-Process -Id ([int]$existingPidText) -ErrorAction SilentlyContinue
        if ($null -ne $existingProcess) {
            Write-Host "Frontend is already running."
            Write-Host "PID: $existingPidText"
            Write-Host "URL: http://127.0.0.1:5173/"
            Write-Host "stdout: $stdoutLog"
            Write-Host "stderr: $stderrLog"
            Write-Host "pid file: $pidFile"
            exit 0
        }
    }

    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

$process = Start-Process `
    -FilePath "npm.cmd" `
    -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1") `
    -WorkingDirectory $frontendRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -WindowStyle Hidden `
    -PassThru

Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ascii

Write-Host "Frontend started in background."
Write-Host "PID: $($process.Id)"
Write-Host "URL: http://127.0.0.1:5173/"
Write-Host "stdout: $stdoutLog"
Write-Host "stderr: $stderrLog"
Write-Host "pid file: $pidFile"
