param(
    [string]$OutJson = "artifacts/pc_health/latest_pc_health.json",
    [switch]$Quiet
)

$ErrorActionPreference = "SilentlyContinue"

function New-Finding {
    param(
        [string]$Severity,
        [string]$Category,
        [string]$Message,
        [hashtable]$Data
    )
    [ordered]@{
        severity = $Severity
        category = $Category
        message = $Message
        data = $Data
    }
}

$report = [ordered]@{}
$report.timestamp = (Get-Date).ToString("o")
$report.hostname = $env:COMPUTERNAME

$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$cs = Get-CimInstance Win32_ComputerSystem

$totalMem = [double]$cs.TotalPhysicalMemory
$freeMem = [double]$os.FreePhysicalMemory * 1KB
$usedMem = $totalMem - $freeMem
if ($usedMem -lt 0) { $usedMem = 0 }

$report.system = [ordered]@{
    os = $os.Caption
    version = $os.Version
    build = $os.BuildNumber
    architecture = $os.OSArchitecture
    uptime_hours = [math]::Round(((Get-Date) - $os.LastBootUpTime).TotalHours, 2)
    cpu = $cpu.Name
    cpu_cores = $cpu.NumberOfCores
    cpu_logical = $cpu.NumberOfLogicalProcessors
}

$report.memory = [ordered]@{
    total_gb = [math]::Round($totalMem / 1GB, 2)
    used_gb = [math]::Round($usedMem / 1GB, 2)
    free_gb = [math]::Round($freeMem / 1GB, 2)
    used_pct = [math]::Round((($usedMem / $totalMem) * 100), 2)
}

$report.disks = @(Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object {
    [ordered]@{
        drive = $_.DeviceID
        size_gb = [math]::Round([double]$_.Size / 1GB, 2)
        free_gb = [math]::Round([double]$_.FreeSpace / 1GB, 2)
        free_pct = if ([double]$_.Size -gt 0) { [math]::Round(([double]$_.FreeSpace / [double]$_.Size) * 100, 2) } else { 0 }
    }
})

$phys = Get-PhysicalDisk
if ($phys) {
    $report.physical_disks = @($phys | ForEach-Object {
        [ordered]@{
            name = $_.FriendlyName
            media_type = [string]$_.MediaType
            health = [string]$_.HealthStatus
            operational = [string]$_.OperationalStatus
            size_gb = [math]::Round([double]$_.Size / 1GB, 2)
        }
    })
}

$since = (Get-Date).AddDays(-1)
$sysErr = Get-WinEvent -FilterHashtable @{ LogName = "System"; StartTime = $since } -MaxEvents 400 | Where-Object { $_.Level -eq 2 }
$appErr = Get-WinEvent -FilterHashtable @{ LogName = "Application"; StartTime = $since } -MaxEvents 400 | Where-Object { $_.Level -eq 2 }

$report.events = [ordered]@{
    system_errors_sampled_24h = ($sysErr | Measure-Object).Count
    application_errors_sampled_24h = ($appErr | Measure-Object).Count
    top_system_sources = @($sysErr | Group-Object ProviderName | Sort-Object Count -Descending | Select-Object -First 5 Name, Count)
    top_application_sources = @($appErr | Group-Object ProviderName | Sort-Object Count -Descending | Select-Object -First 5 Name, Count)
}

$report.pending_reboot = [ordered]@{
    cbs_reboot_pending = (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending')
    wu_reboot_required = (Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired')
    pending_file_rename = ((Get-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager' -Name 'PendingFileRenameOperations' -ErrorAction SilentlyContinue) -ne $null)
}

$report.top_process_mem = @(Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 ProcessName, Id, @{n='working_set_mb';e={[math]::Round($_.WorkingSet64/1MB,2)}}, @{n='cpu_sec';e={[math]::Round($_.CPU,2)}})

$findings = @()

if ($report.memory.used_pct -ge 92) {
    $findings += New-Finding -Severity "critical" -Category "memory" -Message "Memory pressure is critical" -Data @{ used_pct = $report.memory.used_pct }
} elseif ($report.memory.used_pct -ge 85) {
    $findings += New-Finding -Severity "high" -Category "memory" -Message "Memory pressure is high" -Data @{ used_pct = $report.memory.used_pct }
}

$sysDrive = $report.disks | Where-Object { $_.drive -eq "C:" } | Select-Object -First 1
if ($sysDrive) {
    if ($sysDrive.free_pct -lt 5) {
        $findings += New-Finding -Severity "critical" -Category "disk" -Message "System drive free space is critically low" -Data @{ drive = "C:"; free_pct = $sysDrive.free_pct; free_gb = $sysDrive.free_gb }
    } elseif ($sysDrive.free_pct -lt 15) {
        $findings += New-Finding -Severity "high" -Category "disk" -Message "System drive free space is low" -Data @{ drive = "C:"; free_pct = $sysDrive.free_pct; free_gb = $sysDrive.free_gb }
    }
}

if ($report.system.uptime_hours -ge 168) {
    $findings += New-Finding -Severity "medium" -Category "uptime" -Message "Long uptime may amplify leaks and stale handles" -Data @{ uptime_hours = $report.system.uptime_hours }
}

if ($report.events.system_errors_sampled_24h + $report.events.application_errors_sampled_24h -ge 8) {
    $findings += New-Finding -Severity "medium" -Category "events" -Message "Elevated error count in sampled event logs" -Data @{ system = $report.events.system_errors_sampled_24h; application = $report.events.application_errors_sampled_24h }
}

if ($report.pending_reboot.cbs_reboot_pending -or $report.pending_reboot.wu_reboot_required -or $report.pending_reboot.pending_file_rename) {
    $findings += New-Finding -Severity "medium" -Category "reboot" -Message "Reboot-pending indicators present" -Data $report.pending_reboot
}

if ($report.physical_disks) {
    foreach ($d in $report.physical_disks) {
        if ($d.health -ne "Healthy") {
            $findings += New-Finding -Severity "high" -Category "disk_health" -Message "A physical disk is not healthy" -Data $d
        }
    }
}

$report.findings = $findings

$recommendations = @()
if ($findings | Where-Object { $_.category -eq "disk" }) {
    $recommendations += "Free at least 25-30 GB on C: (target >15% free) to avoid paging and update failures."
}
if ($findings | Where-Object { $_.category -eq "memory" }) {
    $recommendations += "Reduce steady RAM footprint: close heavy background apps, cap WSL/Docker memory, and trim startup apps."
}
if ($findings | Where-Object { $_.category -eq "uptime" -or $_.category -eq "reboot" }) {
    $recommendations += "Perform a controlled reboot to clear pending operations and refresh kernel/runtime state."
}
if ($findings | Where-Object { $_.category -eq "events" }) {
    $recommendations += "Review top Event Viewer sources and suppress/fix recurring faults before long multi-agent runs."
}
if (-not $recommendations) {
    $recommendations += "System health baseline looks stable. Keep weekly patch/reboot and monthly storage cleanup cadence."
}
$report.recommendations = $recommendations

$dir = Split-Path -Parent $OutJson
if ($dir -and -not (Test-Path $dir)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

$report | ConvertTo-Json -Depth 7 | Set-Content -Path $OutJson -Encoding UTF8

if (-not $Quiet) {
    Write-Host "PC health report written: $OutJson"
    Write-Host "Findings: $($findings.Count)"
    foreach ($f in $findings) {
        Write-Host "- [$($f.severity)] $($f.category): $($f.message)"
    }
}
