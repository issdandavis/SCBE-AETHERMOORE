param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "[grok-fix] $Message"
}

$npmRoot = (npm root -g).Trim()
if ([string]::IsNullOrWhiteSpace($npmRoot)) {
    throw "Unable to resolve global npm root."
}

$clientPath = Join-Path $npmRoot "@vibe-kit\grok-cli\dist\grok\client.js"
if (-not (Test-Path $clientPath)) {
    throw "grok client file not found: $clientPath"
}

$content = Get-Content -Path $clientPath -Raw
$original = $content

$patternBlock = '(?s)\s*// Add search parameters if specified\s*if \(searchOptions\?\.search_parameters\) \{\s*requestPayload\.search_parameters = searchOptions\.search_parameters;\s*\}\s*'
$content = [regex]::Replace($content, $patternBlock, [Environment]::NewLine)

$patternSearchMethod = '(?s)\s*const searchOptions = \{\s*search_parameters: searchParameters \|\| \{ mode: "on" \},\s*\};\s*return this\.chat\(\[searchMessage\], \[\], undefined, searchOptions\);'
$content = [regex]::Replace($content, $patternSearchMethod, "`n        return this.chat([searchMessage], [], undefined, undefined);")

if ($content -eq $original -and -not $Force) {
    Write-Info "No changes needed (already patched or package layout changed)."
    exit 0
}

$backup = "$clientPath.bak.$(Get-Date -Format 'yyyyMMddHHmmss')"
Copy-Item -Path $clientPath -Destination $backup -Force
Set-Content -Path $clientPath -Value $content -Encoding UTF8

$leftover = Select-String -Path $clientPath -Pattern 'requestPayload\.search_parameters' -SimpleMatch
if ($leftover) {
    throw "Patch incomplete: deprecated search_parameters assignment still present. Backup at: $backup"
}

Write-Info "Patched successfully."
Write-Info "Backup: $backup"
Write-Info "File: $clientPath"
