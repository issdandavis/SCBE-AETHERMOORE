param(
    [ValidateSet("health", "call")]
    [string]$Mode = "health",
    [string]$ConfigPath = "config/governance/terminal_ai_router_profiles.json",
    [string]$Checks = "openai,anthropic,xai,huggingface",
    [string]$Output = "",
    [switch]$Strict,
    [switch]$SyncAliases = $true,
    [string]$Prompt = "",
    [string]$PromptFile = "",
    [ValidateSet("auto", "easy", "medium", "hard")]
    [string]$Complexity = "auto",
    [string]$Providers = "",
    [double]$Temperature = 0.2,
    [int]$MaxOutputTokens = 420,
    [switch]$PrintResponse
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "python not found in PATH"
}

if ([string]::IsNullOrWhiteSpace($Output)) {
    if ($Mode -eq "health") {
        $Output = "artifacts/ai_router/terminal_ai_health.json"
    }
    else {
        $Output = "artifacts/ai_router/terminal_ai_router_last.json"
    }
}

$argsList = @(
    "scripts/system/terminal_ai_router.py",
    "--config", $ConfigPath,
    $Mode,
    "--output", $Output
)

if ($SyncAliases) {
    $argsList += "--sync-aliases"
}

if ($Mode -eq "health") {
    $argsList += @("--checks", $Checks)
    if ($Strict) { $argsList += "--strict" }
}
else {
    if ([string]::IsNullOrWhiteSpace($Prompt) -and [string]::IsNullOrWhiteSpace($PromptFile)) {
        throw "For call mode, provide -Prompt or -PromptFile"
    }
    if (-not [string]::IsNullOrWhiteSpace($Prompt)) {
        $argsList += @("--prompt", $Prompt)
    }
    if (-not [string]::IsNullOrWhiteSpace($PromptFile)) {
        $argsList += @("--prompt-file", $PromptFile)
    }
    $argsList += @("--complexity", $Complexity)
    $argsList += @("--temperature", "$Temperature")
    $argsList += @("--max-output-tokens", "$MaxOutputTokens")
    if (-not [string]::IsNullOrWhiteSpace($Providers)) {
        $argsList += @("--providers", $Providers)
    }
    if ($PrintResponse) { $argsList += "--print-response" }
}

python @argsList
