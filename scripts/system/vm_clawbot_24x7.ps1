param(
    [ValidateSet("bootstrap", "start", "status", "logs", "stop", "deploy-research", "deploy-remote-workers")]
    [string]$Action = "status",
    [string]$VmHost = "",
    [string]$User = "ubuntu",
    [string]$KeyPath = "",
    [string]$ProjectRoot = "C:\Users\issda\SCBE-AETHERMOORE",
    [string]$RemoteRepo = "/home/ubuntu/SCBE-AETHERMOORE",
    [int]$Tail = 120
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($VmHost)) {
    throw "VmHost is required. Example: -VmHost 129.146.x.x"
}
if ([string]::IsNullOrWhiteSpace($KeyPath)) {
    throw "KeyPath is required. Example: -KeyPath C:\keys\oracle_a1.key"
}
if (-not (Test-Path $KeyPath)) {
    throw "SSH key not found: $KeyPath"
}

$remote = "$User@$VmHost"
$setupScript = Join-Path $ProjectRoot "deploy\oracle_vm_setup.sh"
if (($Action -eq "bootstrap") -and -not (Test-Path $setupScript)) {
    throw "Missing setup script: $setupScript"
}

function Invoke-Remote {
    param([string]$Command)
    ssh -i $KeyPath $remote $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Remote command failed: $Command"
    }
}

function Copy-ToRemote {
    param([string]$Source, [string]$Target)
    scp -i $KeyPath $Source "${remote}:$Target"
    if ($LASTEXITCODE -ne 0) {
        throw "SCP failed: $Source -> ${remote}:$Target"
    }
}

switch ($Action) {
    "bootstrap" {
        Write-Host "[VM] Uploading bootstrap script..."
        Copy-ToRemote -Source $setupScript -Target "/tmp/oracle_vm_setup.sh"
        Write-Host "[VM] Running bootstrap (this can take several minutes)..."
        Invoke-Remote -Command "bash -lc 'chmod +x /tmp/oracle_vm_setup.sh && /tmp/oracle_vm_setup.sh'"
        Write-Host "[VM] Bootstrap complete. Starting services..."
        Invoke-Remote -Command "bash -lc 'sudo systemctl daemon-reload && sudo systemctl enable aethercode hydra-clawbot && sudo systemctl restart aethercode hydra-clawbot'"
        Invoke-Remote -Command "bash -lc 'sudo systemctl --no-pager --full status aethercode hydra-clawbot | sed -n \"1,80p\"'"
    }
    "start" {
        Invoke-Remote -Command "bash -lc 'sudo systemctl restart aethercode hydra-clawbot && sudo systemctl --no-pager --full status aethercode hydra-clawbot | sed -n \"1,80p\"'"
    }
    "status" {
        Invoke-Remote -Command "bash -lc 'systemctl is-active aethercode hydra-clawbot; systemctl --no-pager --full status aethercode hydra-clawbot | sed -n \"1,80p\"'"
    }
    "logs" {
        Invoke-Remote -Command "bash -lc 'sudo journalctl -u hydra-clawbot -n $Tail --no-pager; echo \"-----\"; sudo journalctl -u aethercode -n $Tail --no-pager'"
    }
    "stop" {
        Invoke-Remote -Command "bash -lc 'sudo systemctl stop hydra-clawbot aethercode; systemctl is-active hydra-clawbot aethercode'"
    }
    "deploy-research" {
        Invoke-Remote -Command "bash -lc 'cd $RemoteRepo && docker compose -f docker-compose.research.yml up -d --build && docker compose -f docker-compose.research.yml ps'"
    }
    "deploy-remote-workers" {
        Invoke-Remote -Command "bash -lc 'cd $RemoteRepo && docker compose -f docker-compose.hydra-remote.yml up -d --build && docker compose -f docker-compose.hydra-remote.yml ps'"
    }
    default {
        throw "Unsupported action: $Action"
    }
}
