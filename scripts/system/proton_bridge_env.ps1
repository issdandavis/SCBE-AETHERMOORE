param(
  [Parameter(Mandatory = $false)] [string]$Username = "",
  [Parameter(Mandatory = $false)] [string]$Password = "",
  [string]$BridgeHost = "127.0.0.1",
  [int]$ImapPort = 1143,
  [int]$SmtpPort = 1025,
  [string]$FolderPrefix = "Labels"
)

if (-not $Username) {
  $Username = Read-Host "Bridge username"
}

if (-not $Password) {
  $secure = Read-Host "Bridge password" -AsSecureString
  $ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try {
    $Password = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
  }
  finally {
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
  }
}

$env:PROTON_BRIDGE_HOST = $BridgeHost
$env:PROTON_BRIDGE_IMAP_PORT = [string]$ImapPort
$env:PROTON_BRIDGE_SMTP_PORT = [string]$SmtpPort
$env:PROTON_BRIDGE_USERNAME = $Username
$env:PROTON_BRIDGE_PASSWORD = $Password
$env:PROTON_BRIDGE_FOLDER_PREFIX = $FolderPrefix

Write-Host "Proton Bridge env loaded into the current shell." -ForegroundColor Green
Write-Host ""
Write-Host "Next checks:" -ForegroundColor Cyan
Write-Host "  python scripts/system/proton_mail_ops.py doctor --json"
Write-Host "  python scripts/system/proton_mail_ops.py folders --json"
Write-Host "  python scripts/system/proton_mail_ops.py triage --folder INBOX --limit 20 --json"
Write-Host ""
Write-Host "These values only live in the current PowerShell session." -ForegroundColor Yellow
