param(
    [ValidateSet('audit','publish','gate-audit','gate-disable','images-dry','images-upload','full-live','mesh-audit','mesh-live')]
    [string]$Mode = 'audit',
    [string]$RepoRoot = 'C:\Users\issda\SCBE-AETHERMOORE',
    [string]$Store = 'aethermore-code.myshopify.com'
)

$ErrorActionPreference = 'Stop'
Set-Location $RepoRoot

function Load-EnvVar {
    param([string]$Name)
    $userValue = [Environment]::GetEnvironmentVariable($Name, 'User')
    if ($userValue) {
        Set-Item -Path "Env:$Name" -Value $userValue
        return
    }

    $machineValue = [Environment]::GetEnvironmentVariable($Name, 'Machine')
    if ($machineValue) {
        Set-Item -Path "Env:$Name" -Value $machineValue
    }
}

"SHOPIFY_ACCESS_TOKEN","SHOPIFY_ADMIN_TOKEN","SHOPIFY_SHOP","SHOPIFY_SHOP_DOMAIN","SHOPIFY_API_VERSION" | ForEach-Object {
    Load-EnvVar -Name $_
}

if (-not $env:SHOPIFY_SHOP -and $env:SHOPIFY_SHOP_DOMAIN) {
    $env:SHOPIFY_SHOP = $env:SHOPIFY_SHOP_DOMAIN
}

switch ($Mode) {
    'audit' {
        python scripts/system/shopify_store_launch_pack.py --store $Store --run-both-side-test
    }
    'publish' {
        python scripts/system/shopify_store_launch_pack.py --store $Store --run-both-side-test --publish-live
    }
    'gate-audit' {
        python scripts/system/shopify_toggle_password_gate.py --store $Store
    }
    'gate-disable' {
        python scripts/system/shopify_toggle_password_gate.py --store $Store --apply --headed
    }
    'images-dry' {
        python scripts/system/shopify_upload_images.py
    }
    'images-upload' {
        python scripts/system/shopify_upload_images.py --upload
    }
    'full-live' {
        python scripts/system/profit_autopilot.py --publish-live
    }
    'mesh-audit' {
        powershell -ExecutionPolicy Bypass -File scripts/system/run_hydra_terminal_lanes.ps1 -Store $Store
    }
    'mesh-live' {
        powershell -ExecutionPolicy Bypass -File scripts/system/run_hydra_terminal_lanes.ps1 -Store $Store -PublishLive
    }
}
