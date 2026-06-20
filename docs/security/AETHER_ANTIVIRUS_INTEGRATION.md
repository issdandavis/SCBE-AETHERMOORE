# Aether Antivirus Integration Layer

Aether Antivirus should sit above existing antivirus, EDR, SIEM, runtime, and
artifact-scanning tools. It does not need to replace them. The useful product
surface is a governed fusion layer:

1. Ingest alerts from tools customers already run.
2. Normalize severity, provider, artifact, and evidence fields.
3. Add SCBE semantic/artifact/governance scoring.
4. Emit one receipt with `ALLOW`, `QUARANTINE`, or `DENY`.
5. Make agents and CI obey that receipt before they run code, merge, deploy, or
   handle customer data.

## Market Stack

| Tier | Examples | What they provide | SCBE layer |
| --- | --- | --- | --- |
| Endpoint / EDR | Microsoft Defender for Endpoint, CrowdStrike Falcon, SentinelOne | Device, process, file, alert, incident, and response telemetry | Normalize alerts and convert them into agent/CI gates |
| SIEM / XDR middleware | Wazuh, Splunk, Elastic, Microsoft Sentinel | Log correlation, rule severity, incident workflow, active response | Add SCBE receipts, model-agent routing, and safer remediation decisions |
| Runtime security | Falco, eBPF/auditd feeds, Kubernetes admission/rules | Live behavior detection for hosts, containers, and workloads | Stop agent jobs or deployments when runtime behavior violates policy |
| Signature / static analysis | ClamAV, YARA, Sigma, Semgrep, CodeQL | File signatures, malware strings, log signatures, code patterns | Fuse static hits with artifact triage and harmonic-governance scoring |
| Agent layer | SCBE agent bus, GeoSeal, governance gate, SemanticAntivirus | Intent, routing, command authorization, receipts | Prevent AI/human agents from executing risky next steps |

## Traditional Controls Added

SCBE now includes a traditional local artifact-control layer before the more
semantic/agentic reasoning kicks in:

- SHA-256 allowlist/blocklist policy.
- High-risk extension detection for executable and script-capable files.
- Archive payload detection before unpacking.
- EICAR antivirus test-string detection.
- Double-extension detection.
- Magic-byte versus extension mismatch detection.
- PDF/OLE JavaScript marker detection.
- High-entropy binary detection.
- Download/temp path-zone detection.
- Trusted repo source/test/docs path tagging.

Policy file:

```text
config/security/traditional_security_policy.json
```

Standalone command:

```powershell
python scripts/security/traditional_security_layers.py .\download.bin
```

The artifact triage command automatically includes these controls:

```powershell
python scripts/security/artifact_triage.py .\download.bin
```

## Non-Artifact Event Controls

Security decisions also apply to things that are not files:

- Governed-output proxy decisions and `content_filter` interventions.
- Prompt/model-output text risk.
- Shell command execution.
- Dependency install commands and non-default package registries.
- Network targets outside the trusted-host policy.
- Secret environment-variable references.
- Sensitive config/key path references.
- Runtime/process telemetry from tools such as Wazuh and Falco.

Policy file:

```text
config/security/security_event_policy.json
```

Standalone command:

```powershell
python scripts/security/security_event_layers.py --input .\events.jsonl
```

Governance gate:

```powershell
python scripts/security/code_governance_gate.py security-events .\events.jsonl
```

The AV signal fusion receipt now includes an `event_report` and `event_risk`
field when the input contains command, model, network, dependency, or runtime
events.

Useful public integration facts:

- Microsoft Defender for Endpoint exposes an alerts API with fields such as
  `severity`, `status`, `detectionSource`, `category`, `evidence`, `sha256`,
  and `processCommandLine`.
- YARA is built for identifying and classifying malware samples with textual or
  binary pattern rules.
- ClamAV exposes direct scan and daemon scan flows, including `clamscan`,
  `clamdscan`, `clamonacc`, verdicts, logs, and signature database tooling.
- Wazuh rules convert logs into alerts and severity levels, and Wazuh Active
  Response can automate endpoint actions from rule IDs, levels, or groups.
- Sigma is a generic signature format for SIEM-style log detections.
- Falco detects runtime behavior in hosts, containers, and applications and can
  load custom rules.

## Implemented Code Surface

Primary command:

```powershell
python scripts/security/av_signal_fusion.py --input alerts.jsonl
```

With a local artifact:

```powershell
python scripts/security/av_signal_fusion.py --input alerts.jsonl --artifact .\download.bin
```

Governance gate:

```powershell
python scripts/security/code_governance_gate.py av-signals .\alerts.jsonl
```

SCBE CLI:

```powershell
python scripts/scbe-system-cli.py antivirus-fuse --input .\alerts.jsonl
```

Receipt schema: `scbe_av_signal_fusion_v1`.

Output directory:

```text
artifacts/security/av_signal_fusion/
```

## Current Decisions

`ALLOW` means the upstream tools and SCBE scoring did not find enough risk to
stop the workflow.

`QUARANTINE` means the workflow should move to isolated review. Agents should
not execute referenced artifacts or deploy changes until provenance is clear.

`DENY` means the event blocks execution, merge, or deploy until a human clears
it.

The current fusion is deterministic. It uses external alert severity, SCBE text
threat scanning, optional artifact triage, and the existing Python harmonic wall
chain to compute coherence, `d_star`, `H_eff`, harmonic score, and omega.

## Sources

- Microsoft Defender for Endpoint alerts API:
  <https://learn.microsoft.com/en-us/defender-endpoint/api/get-alerts>
- YARA documentation:
  <https://yara.readthedocs.io/en/stable/>
- ClamAV usage documentation:
  <https://docs.clamav.net/manual/Usage.html>
- Wazuh rules documentation:
  <https://documentation.wazuh.com/current/user-manual/ruleset/rules/index.html>
- Wazuh Active Response:
  <https://documentation.wazuh.com/current/user-manual/capabilities/active-response/index.html>
- Sigma specification:
  <https://sigmahq.io/sigma-specification/>
- Falco runtime security FAQ:
  <https://falco.org/about/faq/>
- Falco custom rules:
  <https://falco.org/docs/concepts/rules/default-custom/>
