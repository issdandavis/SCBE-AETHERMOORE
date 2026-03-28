Param(
  [string]$GitLabBaseUrl = "https://gitlab.com",
  [string]$ProjectName = "scbe-pond-mirror-test",
  [ValidateSet("private", "internal", "public")]
  [string]$Visibility = "private",
  [string]$Branch = "mirror-smoke",
  [switch]$SkipCreate,
  [switch]$SkipPush,
  [switch]$CheckGhAuth
)

$ErrorActionPreference = "Stop"

function Get-EnvValueFromDotEnvFile {
  param(
    [Parameter(Mandatory = $true)][string]$DotEnvPath,
    [Parameter(Mandatory = $true)][string]$Key
  )

  if (!(Test-Path $DotEnvPath)) {
    throw "Missing env file: $DotEnvPath"
  }

  $lines = Get-Content $DotEnvPath
  foreach ($line in $lines) {
    if ($line -match "^\s*#") { continue }
    if ($line -match "^\s*$") { continue }
    if ($line -match ("^\s*" + [regex]::Escape($Key) + "\s*=\s*(.*)\s*$")) {
      $raw = $Matches[1].Trim()
      if ($raw.StartsWith('"') -and $raw.EndsWith('"')) { return $raw.Substring(1, $raw.Length - 2) }
      if ($raw.StartsWith("'") -and $raw.EndsWith("'")) { return $raw.Substring(1, $raw.Length - 2) }
      return $raw
    }
  }
  return $null
}

function Safe-Write {
  param([string]$Msg)
  Write-Host $Msg
}

function Get-OrCreate-Project {
  param(
    [Parameter(Mandatory = $true)][string]$BaseUrl,
    [Parameter(Mandatory = $true)][hashtable]$Headers,
    [Parameter(Mandatory = $true)][string]$Name,
    [Parameter(Mandatory = $true)][string]$Visibility,
    [Parameter(Mandatory = $true)][switch]$SkipCreate
  )

  $q = [Uri]::EscapeDataString($Name)
  $existing = Invoke-RestMethod -Method Get -Uri ($BaseUrl + "/api/v4/projects?owned=true&search=" + $q + "&per_page=100") -Headers $Headers
  foreach ($p in $existing) {
    if ($p.path -eq $Name) { return $p }
  }

  if ($SkipCreate) {
    throw "Project '$Name' not found (owned=true) and -SkipCreate was set."
  }

  Safe-Write ("Creating GitLab project '" + $Name + "' (visibility=" + $Visibility + ")…")
  $body = @{
    name = $Name
    visibility = $Visibility
    initialize_with_readme = $false
  }
  return Invoke-RestMethod -Method Post -Uri ($BaseUrl + "/api/v4/projects") -Headers $Headers -Body $body
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$dotEnv = Join-Path $repoRoot "config\\connector_oauth\\.env.connector.oauth"

$authOk = $false
$projectOk = $false
$pondFlushOk = $false
$mirrorPushOk = $false
$verifyOk = $false
$createdProject = $false

$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$tz = (Get-TimeZone).Id
Safe-Write ("SCBE GitLab Smoke Test @ " + $ts + " " + $tz)
Safe-Write ("RepoRoot: " + $repoRoot)

$token = Get-EnvValueFromDotEnvFile -DotEnvPath $dotEnv -Key "GITLAB_TOKEN"
if ([string]::IsNullOrWhiteSpace($token)) {
  throw "GITLAB_TOKEN not found in $dotEnv"
}

$headers = @{ "PRIVATE-TOKEN" = $token }

Safe-Write ("GitLab Base: " + $GitLabBaseUrl)

$user = Invoke-RestMethod -Method Get -Uri ($GitLabBaseUrl + "/api/v4/user") -Headers $headers
Safe-Write ("GitLab Auth: OK (" + $user.username + ")")
$authOk = $true

$proj = Get-OrCreate-Project -BaseUrl $GitLabBaseUrl -Headers $headers -Name $ProjectName -Visibility $Visibility -SkipCreate:$SkipCreate
Safe-Write ("Project: " + $proj.path_with_namespace + " (id=" + $proj.id + ", visibility=" + $proj.visibility + ", default_branch=" + $proj.default_branch + ")")
$projectOk = $true
if (!$SkipCreate -and ($proj.path -eq $ProjectName) -and ($proj.created_at)) {
  # Best-effort marker; GitLab returns created_at for both existing and new in some cases.
  $createdProject = $true
}

$repoUrl = $proj.http_url_to_repo
if ([string]::IsNullOrWhiteSpace($repoUrl)) {
  throw "Project missing http_url_to_repo. Cannot continue."
}

Safe-Write ("Repo: " + $repoUrl)
Safe-Write ""

if ($CheckGhAuth) {
  Safe-Write "[gh] auth status"
  try { gh auth status } catch { Safe-Write ("WARN: gh auth status failed. " + $_.Exception.Message) }
  Safe-Write ""
}

Safe-Write "[1/3] Pond Flush (read-only)"
$flushOut = & pwsh -NoProfile -File (Join-Path $repoRoot "scripts\\gitlab\\pond_flush.ps1") -GitLabRepoUrl $repoUrl 2>&1
$flushOut | Out-Host
if ($LASTEXITCODE -ne 0) {
  throw ("Pond Flush failed (exit=" + $LASTEXITCODE + ")")
}
$pondFlushOk = $true

if (!$SkipPush) {
  Safe-Write ""
  Safe-Write "[2/3] Mirror Push (write)"
  $pushOut = & pwsh -NoProfile -File (Join-Path $repoRoot "scripts\\gitlab\\mirror_push.ps1") -GitLabRepoUrl $repoUrl -Branch $Branch 2>&1
  $pushOut | Out-Host
  if ($LASTEXITCODE -ne 0) {
    throw ("Mirror Push failed (exit=" + $LASTEXITCODE + ")")
  }
  $mirrorPushOk = $true

  Safe-Write ""
  Safe-Write "[3/3] Verify latest commit via GitLab API"
  $ref = [Uri]::EscapeDataString($Branch)
  $commits = Invoke-RestMethod -Method Get -Uri ($GitLabBaseUrl + "/api/v4/projects/" + $proj.id + "/repository/commits?ref_name=" + $ref + "&per_page=1") -Headers $headers
  if (!($commits -and $commits.Count -ge 1)) {
    throw "Verify failed: no commits returned for that branch."
  }
  $c = $commits[0]
  $short = $c.id.Substring(0, 8)
  Safe-Write ("Latest: " + $short + " " + $c.title)
  $verifyOk = $true
} else {
  Safe-Write ""
  Safe-Write "[2/3] Mirror Push skipped (-SkipPush)"
  Safe-Write "[3/3] Verify skipped (-SkipPush)"
}

Safe-Write ""
Safe-Write "Smoke Test: OK"

$summary = [ordered]@{
  auth_ok = $authOk
  project_ok = $projectOk
  pond_flush_ok = $pondFlushOk
  mirror_push_ok = $mirrorPushOk
  verify_ok = $verifyOk
  skipped_push = [bool]$SkipPush
  skipped_create = [bool]$SkipCreate
  project_id = $proj.id
  repo_url = $repoUrl
  branch = $Branch
}
Safe-Write ("SUMMARY_JSON=" + ($summary | ConvertTo-Json -Compress))
