param(
    [ValidateSet("none", "dry-run", "head", "all")]
    [string]$RunTrainer = "dry-run",

    [ValidateSet("KO", "AV", "RU", "CA", "UM", "DR")]
    [string]$Head = "KO",

    [switch]$PushHF,
    [switch]$TriggerColab,
    [switch]$PushModel,
    [switch]$AllowQuarantine,
    [int]$MaxRecords = 0
)

$ErrorActionPreference = "Stop"
Set-Location -Path "C:\Users\issda\SCBE-AETHERMOORE"

$argsList = @(
    "scripts/system/polly_cross_model_bootstrap.py",
    "--run-trainer", $RunTrainer,
    "--head", $Head
)

if ($PushHF) { $argsList += "--push-hf" }
if ($TriggerColab) { $argsList += "--trigger-colab" }
if ($PushModel) { $argsList += "--push-model" }
if ($AllowQuarantine) { $argsList += "--allow-quarantine" }
if ($MaxRecords -gt 0) { $argsList += @("--max-records", "$MaxRecords") }

python @argsList

