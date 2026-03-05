param(
    [string]$RepoRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$OutDir = "",
    [string]$Agents = "",
    [string]$Tasks = "",
    [string]$Mission = "Execute scoped tasks with deterministic handoff packets.",
    [int]$MaxPackets = 20
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$scriptPath = Join-Path $RepoRoot "scripts\system\reference_center_build.py"
if (-not (Test-Path $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$argsList = @($scriptPath, "--mission", $Mission, "--max-packets", "$MaxPackets")
if (-not [string]::IsNullOrWhiteSpace($OutDir)) { $argsList += @("--out-dir", $OutDir) }
if (-not [string]::IsNullOrWhiteSpace($Agents)) {
    foreach ($a in ($Agents -split ",")) {
        $trimmed = $a.Trim()
        if (-not [string]::IsNullOrWhiteSpace($trimmed)) {
            $argsList += @("--agent", $trimmed)
        }
    }
}
if (-not [string]::IsNullOrWhiteSpace($Tasks)) {
    foreach ($t in ($Tasks -split ",")) {
        $trimmed = $t.Trim()
        if (-not [string]::IsNullOrWhiteSpace($trimmed)) {
            $argsList += @("--task", $trimmed)
        }
    }
}

python @argsList
if ($LASTEXITCODE -ne 0) {
    throw "Reference center build failed with exit code $LASTEXITCODE."
}
