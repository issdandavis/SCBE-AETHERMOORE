from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "black_box"


@dataclass
class Finding:
    severity: str
    code: str
    title: str
    evidence: list[str] = field(default_factory=list)
    explanation: str = ""
    action: str = ""


@dataclass
class BlackBoxReport:
    schema: str
    generated_at: str
    host: dict[str, Any]
    summary: str
    findings: list[Finding]
    signals: dict[str, Any]


def _run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def _powershell_json(script: str, timeout: int = 30) -> Any:
    executable = shutil.which("powershell") or shutil.which("pwsh")
    if not executable:
        return {"error": "powershell_not_found"}
    result = _run(
        [
            executable,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        timeout=timeout,
    )
    if result.returncode != 0:
        return {"error": "powershell_failed", "stderr": result.stderr[-1200:]}
    text = result.stdout.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"error": "bad_json", "stdout": text[-1200:]}


def collect_disk_signals() -> list[dict[str, Any]]:
    disks: list[dict[str, Any]] = []
    if platform.system().lower() == "windows":
        roots = sorted(
            {f"{chr(code)}:\\" for code in range(ord("A"), ord("Z") + 1) if Path(f"{chr(code)}:\\").exists()}
        )
    else:
        roots = ["/"]
    for root in roots:
        try:
            usage = shutil.disk_usage(root)
        except OSError:
            continue
        free_pct = (usage.free / usage.total * 100.0) if usage.total else 0.0
        disks.append(
            {
                "path": root,
                "total_gb": round(usage.total / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "free_percent": round(free_pct, 2),
            }
        )
    return disks


def collect_memory_signals() -> dict[str, Any]:
    if platform.system().lower() != "windows":
        return {"available": False, "reason": "windows_only_signal"}
    script = r"""
$os = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{
  total_gb = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
  free_gb = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
  free_percent = [math]::Round(($os.FreePhysicalMemory / [double]$os.TotalVisibleMemorySize) * 100, 2)
} | ConvertTo-Json -Compress
"""
    return _powershell_json(script) or {"available": False, "reason": "empty_memory_signal"}


def collect_windows_event_signals(hours: int = 24, max_events: int = 120) -> dict[str, Any]:
    if platform.system().lower() != "windows":
        return {"available": False, "reason": "windows_only_signal", "events": []}
    script = rf"""
$start = (Get-Date).AddHours(-{int(hours)})
$events = Get-WinEvent -FilterHashtable @{{LogName='System'; Level=1,2,3; StartTime=$start}} `
  -MaxEvents {int(max_events)} -ErrorAction SilentlyContinue |
  Select-Object TimeCreated, Id, ProviderName, LevelDisplayName, Message
$events | ForEach-Object {{
  $msg = $_.Message -replace '\s+', ' '
  [pscustomobject]@{{
    time = $_.TimeCreated.ToString('o')
    id = $_.Id
    provider = $_.ProviderName
    level = $_.LevelDisplayName
    message = $msg.Substring(0, [Math]::Min(360, $msg.Length))
  }}
}} | ConvertTo-Json -Compress
"""
    raw = _powershell_json(script, timeout=45)
    if raw is None:
        events: list[dict[str, Any]] = []
    elif isinstance(raw, list):
        events = raw
    elif isinstance(raw, dict) and "error" in raw:
        return {"available": False, **raw, "events": []}
    else:
        events = [raw]
    return {"available": True, "window_hours": hours, "events": events}


def collect_process_signals(limit: int = 8) -> dict[str, Any]:
    if platform.system().lower() != "windows":
        return {"available": False, "reason": "windows_only_signal", "top_memory": []}
    script = rf"""
Get-Process |
  Sort-Object WorkingSet64 -Descending |
  Select-Object -First {int(limit)} Name, Id, CPU, WorkingSet64, StartTime -ErrorAction SilentlyContinue |
  ForEach-Object {{
    [pscustomobject]@{{
      name = $_.Name
      pid = $_.Id
      cpu_seconds = if ($_.CPU -eq $null) {{ $null }} else {{ [math]::Round($_.CPU, 2) }}
      memory_mb = [math]::Round($_.WorkingSet64 / 1MB, 1)
      start_time = if ($_.StartTime -eq $null) {{ $null }} else {{ $_.StartTime.ToString('o') }}
    }}
  }} | ConvertTo-Json -Compress
"""
    raw = _powershell_json(script, timeout=30)
    if isinstance(raw, list):
        return {"available": True, "top_memory": raw}
    if isinstance(raw, dict) and "error" not in raw:
        return {"available": True, "top_memory": [raw]}
    return {"available": False, "top_memory": [], "error": raw}


def _event_text(event: dict[str, Any]) -> str:
    return f"{event.get('time', '?')} {event.get('provider', '?')} #{event.get('id', '?')}: {event.get('message', '')}"


def analyze(signals: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []

    for disk in signals.get("disks", []):
        if disk["free_gb"] < 5 or disk["free_percent"] < 5:
            findings.append(
                Finding(
                    severity="high",
                    code="disk_almost_full",
                    title=f"{disk['path']} is close to full",
                    evidence=[f"{disk['free_gb']} GB free ({disk['free_percent']}%)"],
                    explanation=(
                        "Jobs, browsers, model caches, and Windows updates can fail or force-shutdown workflows "
                        "when the system drive runs out of space."
                    ),
                    action="Clear cache/artifacts or move run outputs before starting long AI/browser/training jobs.",
                )
            )
        elif disk["free_gb"] < 15 or disk["free_percent"] < 10:
            findings.append(
                Finding(
                    severity="medium",
                    code="disk_low",
                    title=f"{disk['path']} has limited free space",
                    evidence=[f"{disk['free_gb']} GB free ({disk['free_percent']}%)"],
                    explanation=(
                        "This is not an immediate crash, but it is the common pre-failure state for long local jobs."
                    ),
                    action="Free space before running builds, model downloads, indexing, or video/browser automation.",
                )
            )

    memory = signals.get("memory", {})
    if isinstance(memory, dict) and memory.get("free_percent") is not None:
        if float(memory["free_percent"]) < 8:
            findings.append(
                Finding(
                    severity="high",
                    code="memory_pressure",
                    title="Physical memory is critically low",
                    evidence=[f"{memory.get('free_gb')} GB free ({memory.get('free_percent')}%)"],
                    explanation=(
                        "Heavy swapping can make a workstation look hung and can kill browser, Python, or Node jobs."
                    ),
                    action="Close high-memory processes or reduce local model/browser parallelism.",
                )
            )
        elif float(memory["free_percent"]) < 15:
            findings.append(
                Finding(
                    severity="medium",
                    code="memory_low",
                    title="Physical memory is low",
                    evidence=[f"{memory.get('free_gb')} GB free ({memory.get('free_percent')}%)"],
                    explanation="The machine can run, but long jobs are more likely to stall or fail under load.",
                    action="Avoid starting large scans or model jobs until memory pressure drops.",
                )
            )

    events = signals.get("windows_events", {}).get("events", [])
    event_ids = {int(e.get("id", 0)) for e in events if str(e.get("id", "")).isdigit()}
    providers = " ".join(str(e.get("provider", "")).lower() for e in events)

    if 41 in event_ids:
        findings.append(
            Finding(
                severity="high",
                code="unexpected_shutdown",
                title="Windows recorded an unexpected shutdown",
                evidence=[_event_text(e) for e in events if int(e.get("id", 0)) == 41][:3],
                explanation=(
                    "Event 41 means Windows restarted without a clean shutdown. It does not prove the root cause, "
                    "but it confirms the black-box event happened."
                ),
                action=(
                    "Correlate the minutes before this event with disk, driver, WHEA, BugCheck, and power events "
                    "below."
                ),
            )
        )

    if 1001 in event_ids or "bugcheck" in providers:
        findings.append(
            Finding(
                severity="high",
                code="bugcheck",
                title="Windows recorded a bugcheck/BSOD signal",
                evidence=[
                    _event_text(e)
                    for e in events
                    if int(e.get("id", 0)) == 1001 or "bugcheck" in str(e.get("provider", "")).lower()
                ][:3],
                explanation="This usually means a kernel driver, hardware path, or low-level subsystem failed.",
                action=(
                    "Preserve the dump path from the event, then check recent driver/storage/power events around "
                    "the same timestamp."
                ),
            )
        )

    disk_event_ids = {7, 11, 51, 55, 98, 129, 153, 157}
    disk_events = [
        e
        for e in events
        if int(e.get("id", 0)) in disk_event_ids
        or str(e.get("provider", "")).lower() in {"disk", "ntfs", "storahci", "iaStorAC".lower()}
    ]
    if disk_events:
        findings.append(
            Finding(
                severity="high",
                code="storage_warning",
                title="Storage or filesystem warnings found",
                evidence=[_event_text(e) for e in disk_events[:5]],
                explanation=(
                    "Disk/controller warnings before a crash are actionable. They often point to storage drivers, "
                    "link power management, cabling, disk health, or filesystem trouble."
                ),
                action=(
                    "Back up important work, check SMART/vendor tools, and review storage-controller driver and "
                    "power-management settings."
                ),
            )
        )

    whea_events = [
        e for e in events if "whea" in str(e.get("provider", "")).lower() or int(e.get("id", 0)) in {17, 18, 19, 47}
    ]
    if whea_events:
        findings.append(
            Finding(
                severity="high",
                code="hardware_error",
                title="Hardware error signals found",
                evidence=[_event_text(e) for e in whea_events[:5]],
                explanation=(
                    "WHEA events are hardware/firmware/driver-layer warnings. They matter before random shutdowns "
                    "or job crashes."
                ),
                action=(
                    "Check thermals, BIOS/firmware, memory stability, GPU/PCIe/storage devices, and recent driver "
                    "changes."
                ),
            )
        )

    service_events = [e for e in events if int(e.get("id", 0)) in {7000, 7001, 7009, 7011, 7031, 7034}]
    if len(service_events) >= 3:
        findings.append(
            Finding(
                severity="medium",
                code="service_instability",
                title="Multiple Windows service failures found",
                evidence=[_event_text(e) for e in service_events[:5]],
                explanation=(
                    "Repeated service crashes can explain broken networking, stuck background tools, or failed app "
                    "launches."
                ),
                action=(
                    "Identify the repeated service name in the event messages and disable/update/reinstall the "
                    "owning software."
                ),
            )
        )

    if not findings:
        findings.append(
            Finding(
                severity="low",
                code="no_immediate_failure_signal",
                title="No immediate black-box failure signal found",
                evidence=["No critical disk/memory/shutdown patterns detected in the scanned window."],
                explanation=(
                    "This does not prove the machine is perfect; it means the cheap signals did not show a current "
                    "failure pattern."
                ),
                action=(
                    "Run again after a crash/hang or schedule it before long jobs to catch changing "
                    "disk/memory/event patterns."
                ),
            )
        )
    return findings


def render_text(report: BlackBoxReport) -> str:
    lines = [
        "SCBE Black Box Report",
        f"Generated: {report.generated_at}",
        f"Host: {report.host.get('hostname')} ({report.host.get('platform')})",
        "",
        report.summary,
        "",
        "Findings:",
    ]
    for finding in report.findings:
        lines.extend(
            [
                f"- [{finding.severity.upper()}] {finding.title} ({finding.code})",
                f"  Why: {finding.explanation}",
                f"  Do:  {finding.action}",
            ]
        )
        for ev in finding.evidence[:5]:
            lines.append(f"  Evidence: {ev}")
    return "\n".join(lines) + "\n"


def build_report(hours: int = 24) -> BlackBoxReport:
    signals = {
        "disks": collect_disk_signals(),
        "memory": collect_memory_signals(),
        "windows_events": collect_windows_event_signals(hours=hours),
        "processes": collect_process_signals(),
    }
    findings = analyze(signals)
    highest = "low"
    if any(f.severity == "high" for f in findings):
        highest = "high"
    elif any(f.severity == "medium" for f in findings):
        highest = "medium"
    summary = {
        "high": "Action needed: SCBE Black Box found a likely failure or pre-failure signal.",
        "medium": "Watch this machine: SCBE Black Box found a condition that can break long jobs.",
        "low": "No immediate failure pattern found in the scanned signals.",
    }[highest]
    return BlackBoxReport(
        schema="scbe_black_box_report_v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        host={
            "hostname": platform.node(),
            "platform": platform.platform(),
            "python": sys.version.split()[0],
        },
        summary=summary,
        findings=findings,
        signals=signals,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SCBE Black Box: explain PC/workstation failure risk in plain English."
    )
    parser.add_argument("--hours", type=int, default=24, help="Windows Event Log lookback window.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT), help="Directory for JSON and text reports.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of the text report.")
    parser.add_argument(
        "--no-fail-on-high",
        action="store_true",
        help="Always exit 0 after writing the report. Useful for demos and scheduled report generation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(hours=args.hours)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    json_path = out_dir / "latest_black_box_report.json"
    text_path = out_dir / "latest_black_box_report.txt"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    text = render_text(report)
    text_path.write_text(text, encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(text)
        print(f"Wrote: {json_path}")
        print(f"Wrote: {text_path}")
    if args.no_fail_on_high:
        return 0
    return 0 if not any(f.severity == "high" for f in report.findings) else 1


if __name__ == "__main__":
    raise SystemExit(main())
