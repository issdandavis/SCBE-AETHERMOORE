# Stop all Docker processes
$procs = @('Docker Desktop', 'docker', 'docker-mcp', 'docker-sandbox', 'com.docker.backend', 'com.docker.proxy')
foreach ($p in $procs) {
    Get-Process -Name $p -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 5
$remaining = Get-Process -Name 'docker*' -ErrorAction SilentlyContinue
if ($remaining) {
    Write-Host "Still running:"
    $remaining | Select-Object Name, Id | Format-Table
} else {
    Write-Host "All Docker processes stopped"
}
