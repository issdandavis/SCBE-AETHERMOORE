# Security Advisory: Browser Sandbox + Container Escape (March 2026)

**Date:** 2026-03-17
**Severity:** HIGH
**Affects:** Any SCBE deployment running headless Chromium or multi-tenant containers

## Active Threats

### CVE-2026-3909 / CVE-2026-3910 — Chrome Zero-Days
- **CVSS:** ~8.8 (High)
- **Status:** Actively exploited in the wild
- **Impact:** Arbitrary code execution inside browser sandbox via crafted web content
- **Patched:** Google emergency patches released mid-March 2026

### CrackArmor — AppArmor MAC Bypass (9 vulnerabilities)
- **Impact:** Unprivileged local users can bypass mandatory access control, escalate to root, escape containers
- **Affects:** Major Linux distributions' default kernel security profiles
- **Status:** Disclosed, patches rolling out

## Impact on SCBE Stack

| Component | Risk | Action |
|-----------|------|--------|
| AetherBrowser (Playwright) | HIGH — runs headless Chromium | Pin to patched Chrome, enforce --no-sandbox only in gVisor |
| Browserless Docker | HIGH — Chromium in container | Update base image, add seccomp + read-only rootfs |
| Kernel-runner (Docker sandbox) | MEDIUM — Node in container, no browser | Already has resource limits; add gVisor if multi-tenant |
| Word Add-in server | LOW — no browser engine | No action |
| FastAPI (main) | LOW — no browser | No action |

## Required Mitigations

### Immediate (before any browser fleet deployment)
1. **Pin Chromium version** to post-patch build (>= 134.0.6958.xx)
2. **Drop capabilities** in all browser containers: `--cap-drop=ALL --cap-add=SYS_CHROOT`
3. **Read-only rootfs**: `--read-only --tmpfs /tmp:rw,noexec,nosuid`
4. **Unprivileged user**: never run as root inside containers
5. **Seccomp profile**: use Docker's default + block `ptrace`, `mount`, `unshare`

### Before Production
6. **gVisor or Firecracker** for untrusted workload isolation (not bare containers)
7. **Network isolation**: browser containers get `--network=none` or egress-only to allowlisted domains
8. **Audit logging**: hash-only metadata to append-only store with signed timestamps
9. **Update kernel** on host to patch CrackArmor AppArmor vulnerabilities
10. **Verify Chromium provenance**: use open-source Chromium builds, not proprietary Chrome

### In SCBE Governance
- Browser actions already pass through the 14-layer pipeline
- Add `CVE_CHECK` step to browser chain dispatcher preflight
- Antivirus membrane should scan page content BEFORE it enters the pipeline
- Quarantine any page that triggers exploit-like patterns (unusual JIT, WASM bombs, V8 heap sprays)

## Docker Run Template (Hardened)

```bash
docker run \
  --rm \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=512m \
  --cap-drop=ALL \
  --cap-add=SYS_CHROOT \
  --security-opt=no-new-privileges \
  --security-opt seccomp=default \
  --user 1000:1000 \
  --memory=1g \
  --cpus=1 \
  --pids-limit=256 \
  --network=none \
  -p 3000:3000 \
  ghcr.io/browserless/chromium
```

## Attack Chain (SCBE-Specific)

```
Malicious page (agent navigates to untrusted URL)
   |
Chrome sandbox escape (CVE-2026-3909/3910)
   |
Container breakout (CrackArmor AppArmor bypass)
   |
Host access / lateral movement
   |
Credential theft (cookies, tokens, secrets in userDataDir)
```

### Why HYDRA is a High-Value Target
- Persistent Playwright profiles (`userDataDir`) store cookies, session tokens, localStorage
- HYDRA "limbs" reuse sessions = high-value persistence target
- Multiple agents hitting same Chromium service = cross-session contamination
- Agents autonomously click links, run scripts, extract content = automated exploit trigger

## Fastest 3 Upgrades (80% Risk Reduction)

1. **Run browsers in gVisor/Firecracker** (not bare containers)
2. **Per-agent persistent storage** (no shared sessions): `/data/playwright/userdata/<agentId>/`
3. **Pre-navigation policy gate** (ALLOW/DENY/QUARANTINE via 14-layer pipeline)

## SCBE Layer Mapping

| SCBE Layer | Real-world Control |
|------------|-------------------|
| Intent validation (L1-4) | Pre-navigation risk scoring |
| Harmonic constraints (L12) | Rate + capability limits |
| Entropic defense (L8) | Session isolation + rotation |
| SpiralSeal (PQC) | Encrypted audit + signing |
| Sacred Tongues | Domain-specific browsing policies |

## Chromium Hardening Flags

```
--no-sandbox=false
--disable-dev-shm-usage
--disable-gpu
--js-flags="--noexpose_wasm"
--disable-webassembly
--disable-site-isolation-trials=false
--enable-strict-mixed-content-checking
```

## Network Containment

Browsers must NOT have open outbound internet. Route through proxy:

```
Browser VM → Proxy Gateway (policy enforced) → Internet
```

Add: domain allowlists, DNS filtering, rate limits per agent.

## Secrets Isolation

Never expose API keys, cookies, or tokens inside browser runtime. Use:
- Short-lived signed tokens (per-task)
- Per-agent credentials with TTL
- Encrypt `userDataDir` at rest

## Observability

- Falco for container escape detection
- eBPF tracing for syscall anomaly detection
- Log: navigation events, JS execution spikes, abnormal syscalls

## References
- https://thehackernews.com/2026/03/google-fixes-two-chrome-zero-days.html
- https://www.itpro.com/software/linux/alert-issued-over-critical-vulnerabilities-in-linuxs-apparmor-security-layer
