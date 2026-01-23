# Security Hardening + Anti-Malware Playbook

Purpose: ship an enterprise-grade yet user-friendly security posture (AV, EDR, malware defense, supply-chain controls, and a self-hosted coding platform) using modern, actively maintained open-source tooling wherever possible.

## Objectives

- Exceed current industry baselines (PQC-ready crypto, memory protection, behavior/rule-based detection).
- Stay evergreen: prioritize projects with active releases and broad community adoption.
- Offer **flex modes**: sensible defaults for normal users, opt-in stricter controls for regulated workloads.

## Tiered Profile

- **Baseline (everyone)**: always-on AV/EDR, auto-updates, DNS filtering, disk encryption, secure boot.
- **High Assurance**: baseline + kernel/eBPF runtime rules, device control, application allow/deny, strict USB, VPN-only network.
- **Isolation Mode**: ephemeral workspaces, microVM/container sandbox (gVisor/Kata), no host persistence, outbound egress allow-list.

## Endpoint Protection Stack

- **Windows**: Microsoft Defender with ASR rules, SmartScreen, Controlled Folder Access; enable tamper protection and cloud-delivered protection. Optional: WDAC/SR for allowlisting; Sysmon + Wazuh for log shipping.
- **macOS**: Built-in XProtect + MRT; add **Santa** (binary allow/deny), **LuLu** (egress firewall); Full Disk Access only for vetted agents.
- **Linux**: **ClamAV** (real-time + FreshClam updates), **YARA** rules for targeted sweeps, **Falco** (eBPF runtime detection), **osquery** for inventory, **AppArmor/SELinux** enforced profiles.
- **Cross-platform EDR/NDR (open-source first)**: **Wazuh** or **CrowdSec** for SIEM/behavior scoring; **Zeek** or **Suricata** for network telemetry/IDS; DNS sinkhole via **AdGuard Home** or **Pi-hole**.
- **Quarantine/response**: isolate process, snapshot indicators (hashes, paths, IPs), auto-create YARA rule, and open a ticket. Provide a one-click "resume" for false positives.

## Supply Chain + CI/CD Security

- **SCA + SBOM**: `syft` -> `grype` (or `trivy`) for images and deps; block known CVEs; publish SBOM in CI artifacts.
- **Static analysis**: `semgrep`, `bandit` (Python), `npm audit`/`pnpm audit`, `pip-audit`, `cargo audit`; optional `codeql` for deeper runs.
- **Secrets**: `gitleaks` in pre-commit and CI; block pushes with secrets.
- **Container/base images**: distroless or minimal images; sign images with **cosign**; enforce verified provenance (SLSA-style).
- **Runtime**: sandbox with **gVisor** or **Kata Containers**; enable seccomp/apparmor profiles and read-only rootfs where possible.

## Self-Hosted Coding Platform (for SCBE + users)

- **Platform**: self-host **Coder** or **Gitpod Self-Hosted** (or `code-server` behind zero-trust), backed by **devcontainers** or Nix flakes. Ephemeral workspaces by default; persistence only for vetted volumes.
- **Security guardrails**:
  - Workspace policy: signed base images, non-root user, read-only rootfs, egress allow-lists for prod tenants.
  - Pre-baked tooling: semgrep, trivy, syft/grype, gitleaks, ruff/flake8/black, npm/yarn/pnpm audit, pytest.
  - Pre-commit enforced locally and in CI; branch protection requires green security checks.
  - Optional auto-patching bot: weekly PRs for deps; nightly CVE sweeps with grype/trivy.
- **Isolation**: run workspaces inside gVisor/Kata or Firecracker-based microVMs; terminate idle sessions; wipe ephemeral storage on stop.

## Update + Patch Cadence

- Signatures/rules: FreshClam hourly; YARA/Falco rules nightly; Suricata/Zeek rulepacks weekly.
- OS/app updates: monthly patch windows; emergency fast-track (<24h) for critical CVEs.
- Tooling currency: pin to released versions, rotate every quarter; retire EOL tools immediately.

## Operational Runbook (condensed)

1. **Deploy agents** per OS (Defender/Santa/ClamAV+Falco+osquery), enroll in Wazuh/CrowdSec.
2. **Enable CI gates**: SBOM + vuln scan, SAST, secrets, signature verification; fail build on high severity.
3. **Provision coding platform**: launch Coder/Gitpod cluster with signed images, sandboxed runtimes, and pre-commit hooks.
4. **Monitor & respond**: forward logs to SIEM; auto-quarantine malicious artifacts; ticket with IOCs; allow override with approval + justification.
5. **Test continuously**: run weekly EICAR+GTUBE-style benign test, and quarterly tabletop for incident response.

## Quick Tool Reference (evergreen, open-source biased)

- AV/EDR: ClamAV, YARA, Falco, osquery, Wazuh, CrowdSec.
- IDS/NDR/DNS: Zeek, Suricata, AdGuard Home/Pi-hole.
- Supply chain: syft, grype, trivy, cosign, SLSA provenance tools.
- SAST/secrets: semgrep, bandit, ruff/flake8, gitleaks, npm/pnpm audit, pip-audit, cargo audit, codeql (optional).
- Sandbox/Isolation: gVisor, Kata Containers, Firecracker (via providers), AppArmor/SELinux.
- Dev platform: Coder, Gitpod Self-Hosted, code-server with devcontainers/Nix.
