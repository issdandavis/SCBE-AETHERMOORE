param(
    [ValidateSet("quick", "full")]
    [string]$Action = "quick"
)

$ErrorActionPreference = "Continue"

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    try {
        & $Command
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Step exited with code $LASTEXITCODE" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "Step failed: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$vaultScript = "C:\Users\issda\.codex\skills\obsidian-vault-ops\scripts\list_obsidian_vaults.py"

Write-Host "SCBE Skill Tool Bridge" -ForegroundColor Green
Write-Host "Repo: $repoRoot"
Write-Host "Mode: $Action"

Invoke-Step -Name "Skill: obsidian-vault-ops (vault discovery)" -Command {
    if (Test-Path $vaultScript) {
        python $vaultScript
    } else {
        Write-Host "Vault discovery script not found at: $vaultScript" -ForegroundColor Yellow
    }
}

Invoke-Step -Name "Tool: code_prism/code_mesh tests" -Command {
    Set-Location $repoRoot
    pytest tests/code_prism -q
}

if ($Action -eq "full") {
    Invoke-Step -Name "Tool: TypeScript typecheck" -Command {
        Set-Location $repoRoot
        npm run typecheck
    }

    Invoke-Step -Name "Tool: MCP servers" -Command {
        Set-Location $repoRoot
        npm run mcp:servers
    }

    Invoke-Step -Name "Tool: MCP tools" -Command {
        Set-Location $repoRoot
        npm run mcp:tools
    }

    Invoke-Step -Name "Tool: Code Mesh smoke conversion" -Command {
        Set-Location $repoRoot
        $tmp = Join-Path $env:TEMP "scbe_skill_bridge_demo.py"
        @"
def add(a, b):
    return a + b
"@ | Set-Content -Path $tmp -Encoding UTF8
        python scripts/code_mesh_build.py --input $tmp --source-lang python --target-systems node_runtime --module-name bridge_demo --out-dir artifacts/code_mesh_bridge
    }
}

Write-Host ""
Write-Host "Bridge run complete." -ForegroundColor Green
