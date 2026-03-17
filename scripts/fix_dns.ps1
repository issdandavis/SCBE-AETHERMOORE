# RIGHT-CLICK THIS FILE -> "Run with PowerShell" AS ADMIN
# Fixes aethermoorgames.com pointing to old Shopify IP

$hostsPath = "C:\Windows\System32\drivers\etc\hosts"
$marker = "# SCBE GitHub Pages"
$entries = @(
    "$marker"
    "185.199.108.153 aethermoorgames.com"
    "185.199.108.153 www.aethermoorgames.com"
)

# Remove old entries if present
$content = Get-Content $hostsPath -ErrorAction SilentlyContinue | Where-Object {
    $_ -notmatch "aethermoorgames\.com" -and $_ -ne $marker
}

# Add new entries
$content += ""
$content += $entries
Set-Content -Path $hostsPath -Value $content -Force

# Flush DNS cache
ipconfig /flushdns

Write-Host ""
Write-Host "DONE. aethermoorgames.com now points to GitHub Pages." -ForegroundColor Green
Write-Host "Open a NEW browser tab and go to: https://aethermoorgames.com" -ForegroundColor Cyan
Write-Host ""
Write-Host "Once DNS fully propagates (1-4 hours), you can remove these entries by running:" -ForegroundColor Yellow
Write-Host "  notepad C:\Windows\System32\drivers\etc\hosts" -ForegroundColor Yellow
Write-Host "  (delete the lines with aethermoorgames.com)" -ForegroundColor Yellow
Write-Host ""
pause
