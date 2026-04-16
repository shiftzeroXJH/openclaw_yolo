param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$CliArgs
)

$ErrorActionPreference = "Stop"

& mamba run -n yolo_env openclaw-yolo @CliArgs
exit $LASTEXITCODE
