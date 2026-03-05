param(
    [int]$MaxCharacters = 120,
    [switch]$RunAudit
)

$ErrorActionPreference = "Stop"
Set-Location -Path "C:\Users\issda\SCBE-AETHERMOORE"

$argsList = @(
    "scripts/system/polly_npc_roundtable_builder.py",
    "--max-characters", "$MaxCharacters"
)

if ($RunAudit) { $argsList += "--run-audit" }

python @argsList

