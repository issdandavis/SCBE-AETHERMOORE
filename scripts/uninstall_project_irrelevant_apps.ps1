param(
    [string]$OutJson = "artifacts/pc_health/uninstall_run.json"
)

$ErrorActionPreference = "Continue"

$results = New-Object System.Collections.Generic.List[object]

function Add-Result {
    param(
        [string]$Type,
        [string]$Target,
        [bool]$Success,
        [string]$Message
    )
    $results.Add([pscustomobject]@{
        timestamp = (Get-Date).ToString("o")
        type = $Type
        target = $Target
        success = $Success
        message = $Message
    }) | Out-Null
}

# Phase 1: Remove user-level WinGet targets.
$wingetTargets = @(
    "Perplexity.Comet",
    "Nvidia.GeForceNow"
)

foreach ($id in $wingetTargets) {
    try {
        $p = Start-Process -FilePath "winget" -ArgumentList @("uninstall","--id",$id,"-e","--silent","--accept-source-agreements") -Wait -PassThru -NoNewWindow
        if ($p.ExitCode -eq 0) {
            Add-Result -Type "winget" -Target $id -Success $true -Message "uninstalled"
        } else {
            Add-Result -Type "winget" -Target $id -Success $false -Message "exit_code=$($p.ExitCode)"
        }
    } catch {
        Add-Result -Type "winget" -Target $id -Success $false -Message $_.Exception.Message
    }
}

# Phase 2: Remove consumer/gaming AppX packages for current user.
$appxNamePatterns = @(
    "4DF9E0F8.Netflix",
    "HULULLC.HULUPLUS",
    "FACEBOOK.FACEBOOK",
    "PricelinePartnerNetwork.Booking.comUSABigsavingson",
    "WildTangentGames.63435CFB65F55",
    "www.youtube.com-54E21B02",
    "59867MatthiasDuyck.QRCodeScanner",
    "48453EusoftwareStudio.WizardbrushDemo",
    "33294AmanMehara.Programming",
    "Microsoft.XboxApp",
    "Microsoft.XboxGamingOverlay",
    "Microsoft.XboxGameOverlay",
    "Microsoft.XboxIdentityProvider",
    "Microsoft.XboxSpeechToTextOverlay",
    "Microsoft.Xbox.TCUI",
    "Microsoft.GamingServices"
)

foreach ($name in $appxNamePatterns) {
    $pkgs = @(Get-AppxPackage -Name $name -ErrorAction SilentlyContinue)
    if (-not $pkgs -or $pkgs.Count -eq 0) {
        Add-Result -Type "appx" -Target $name -Success $true -Message "not_installed"
        continue
    }

    foreach ($pkg in $pkgs) {
        try {
            Remove-AppxPackage -Package $pkg.PackageFullName -ErrorAction Stop
            Add-Result -Type "appx" -Target $pkg.PackageFullName -Success $true -Message "removed"
        } catch {
            Add-Result -Type "appx" -Target $pkg.PackageFullName -Success $false -Message $_.Exception.Message
        }
    }
}

# Persist report
$dir = Split-Path -Parent $OutJson
if ($dir -and -not (Test-Path $dir)) {
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

$payload = [pscustomobject]@{
    run_at = (Get-Date).ToString("o")
    is_admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    result_count = $results.Count
    succeeded = @($results | Where-Object { $_.success }).Count
    failed = @($results | Where-Object { -not $_.success }).Count
    results = $results
}

$payload | ConvertTo-Json -Depth 6 | Set-Content -Path $OutJson -Encoding UTF8

Write-Host "Uninstall batch completed: $OutJson"
Write-Host "Succeeded: $($payload.succeeded)  Failed: $($payload.failed)"
