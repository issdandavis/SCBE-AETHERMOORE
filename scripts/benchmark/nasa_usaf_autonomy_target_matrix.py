from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = (
    ROOT
    / "artifacts"
    / "benchmarks"
    / "nasa_usaf_autonomy_target_matrix"
    / "latest_report.json"
)
DEFAULT_MD = ROOT / "docs" / "benchmarks" / "NASA_USAF_AUTONOMY_TARGET_MATRIX.md"


@dataclass(frozen=True)
class Source:
    source_id: str
    title: str
    organization: str
    url: str
    observed_standard: str


@dataclass(frozen=True)
class Target:
    target_id: str
    source_ids: tuple[str, ...]
    benchmark_target: str
    target_standard: str
    repo_evidence_paths: tuple[str, ...]
    current_status: str
    gap: str
    next_target: str


SOURCES: tuple[Source, ...] = (
    Source(
        source_id="NASA-SWE-ASSURANCE",
        title="NASA Software Engineering Procedural Requirements and Software Assurance Resources",
        organization="NASA",
        url="https://www.nasa.gov/intelligent-systems-division/software-management-office/nasa-software-engineering-procedural-requirements-standards-and-related-resources/",
        observed_standard=(
            "NPR 7150.2, NASA-STD-8739.8, IV&V, formal inspections, secure coding, and the "
            "NASA Software Engineering Handbook as agency-wide safe/reliable software guidance."
        ),
    ),
    Source(
        source_id="NASA-DAIDALUS",
        title="DAIDALUS Detect and Avoid Alerting Logic for Unmanned Systems",
        organization="NASA",
        url="https://nasa.github.io/daidalus/",
        observed_standard=(
            "Reference implementation of RTCA DO-365/DO-365A detect-and-avoid functional "
            "requirements with well-clear thresholds, alerting, maneuver guidance, recovery bands, "
            "sensor uncertainty mitigation, and batch encounter simulation tools."
        ),
    ),
    Source(
        source_id="NASA-UTM",
        title="UAS Traffic Management Project",
        organization="NASA",
        url="https://www.nasa.gov/directorates/armd/past-armd-projects/utm-project/",
        observed_standard=(
            "BVLOS low-altitude UAS integration through field demonstrations with FAA, industry, "
            "and academia for traffic management, airspace access, and deconfliction services."
        ),
    ),
    Source(
        source_id="NASA-CFS-JSC",
        title="JSC Software and Autonomous Subsystems",
        organization="NASA",
        url="https://www.nasa.gov/reference/jsc-software-autonomous-subsystems/",
        observed_standard=(
            "CMMI Level 3 organization using human-rated open-source Class A Core Flight Software "
            "framework, safety criticality assessments, standards, process requirements, and COFR."
        ),
    ),
    Source(
        source_id="USAF-SKYBORG-ACS",
        title="Skyborg Autonomy Core System First Flight",
        organization="U.S. Air Force",
        url="https://www.af.mil/News/Features/Article/2596671/skyborg-autonomy-core-system-has-successful-first-flight/",
        observed_standard=(
            "Flight-tested autonomy core system demonstrating navigation commands, geofence "
            "reaction, flight-envelope adherence, coordinated maneuvering, and monitored C2."
        ),
    ),
    Source(
        source_id="USAF-AGRA-CCA",
        title="Air Force validates open architecture, expands Collaborative Combat Aircraft ecosystem",
        organization="U.S. Air Force",
        url="https://www.af.mil/News/Article-Display/Article/4405471/air-force-validates-open-architecture-expands-collaborative-combat-aircraft-eco/",
        observed_standard=(
            "Government-owned Autonomy Government Reference Architecture across multiple platforms "
            "and vendors, decoupling mission software from vehicle hardware with modular open systems."
        ),
    ),
    Source(
        source_id="USAF-CCA-GROUND-TEST",
        title="DAF begins ground testing for Collaborative Combat Aircraft",
        organization="U.S. Air Force",
        url="https://www.af.mil/News/Article-Display/Article/4171208/daf-begins-ground-testing-for-collaborative-combat-aircraft-selects-beale-afb-a/",
        observed_standard=(
            "Ground testing evaluates propulsion systems, avionics, autonomy integration, and ground "
            "control interfaces before flight testing."
        ),
    ),
    Source(
        source_id="AFRL-STARS-RTA",
        title="Safe Trusted Autonomy for Responsible Spacecraft (STARS)",
        organization="AFRL",
        url="https://afresearchlab.com/wp-content/uploads/2024/03/AFRL_STARS_FS_240318.1.pdf",
        observed_standard=(
            "Runtime assurance safety filter for AI control outputs, reinforcement-learning "
            "multi-satellite control, close-proximity operations, and human-autonomy interfaces."
        ),
    ),
)


TARGETS: tuple[Target, ...] = (
    Target(
        target_id="assurance_traceability_ivv",
        source_ids=("NASA-SWE-ASSURANCE", "NASA-CFS-JSC"),
        benchmark_target="NASA-style software assurance and traceability",
        target_standard="Requirements, verification evidence, safety classification, IV&V/formal inspection trail.",
        repo_evidence_paths=(
            "tests/",
            "docs/legal/patent-workbench/",
            "packages/agent-bus/docs/benchmarks/agentic_os_cli_benchmark.json",
        ),
        current_status="PARTIAL",
        gap=(
            "Strong tests and receipts exist, but there is no NASA-style requirements-to-test "
            "trace matrix, independent review lane, safety classification map, or formal inspection record."
        ),
        next_target=(
            "Add a requirements trace matrix keyed by module/test/artifact and a generated IV&V-style "
            "readiness report with owners, hazards, verification method, and residual risk."
        ),
    ),
    Target(
        target_id="detect_avoid_well_clear",
        source_ids=("NASA-DAIDALUS",),
        benchmark_target="DAA well-clear detection, alerting, and maneuver guidance",
        target_standard="Ownship/traffic aircraft states, time-to-violation, alert bands, recovery maneuvers, encounter batches.",
        repo_evidence_paths=(
            "src/video_lattice/",
            "scripts/video_lattice/",
            "src/geoseal_cli.py",
        ),
        current_status="FAIL",
        gap=(
            "SCBE has geometric drift gates and video/pose lattices, but no ownship/traffic kinematics, "
            "well-clear thresholds, aircraft envelopes, or batch DAA encounter replay."
        ),
        next_target=(
            "Build a deterministic DAA-lite fixture: ownship plus intruder tracks, time-to-boundary, "
            "alert tier, recovery band, and maneuver recommendation. Score it against DAIDALUS-style cases."
        ),
    ),
    Target(
        target_id="utm_bvlos_deconfliction",
        source_ids=("NASA-UTM",),
        benchmark_target="UTM/BVLOS traffic-management service interoperability",
        target_standard="Strategic deconfliction, shared situational awareness, operator/service-provider workflows.",
        repo_evidence_paths=(
            "packages/agent-bus/",
            "external_repos/spiralverse-protocol/docs/SPACE_DEBRIS_FLEET.md",
        ),
        current_status="PARTIAL",
        gap=(
            "Agent bus and Spiralverse fleet docs model coordination, but there is no UTM service API, "
            "airspace volume model, BVLOS operation plan, or multi-operator deconfliction benchmark."
        ),
        next_target=(
            "Add an airspace-volume conflict benchmark with multiple planned routes, time windows, "
            "authorization state, and deconfliction decisions."
        ),
    ),
    Target(
        target_id="core_flight_framework",
        source_ids=("NASA-CFS-JSC",),
        benchmark_target="Flight-software framework readiness",
        target_standard="CFS/cFS-like modular flight app shape, command/telemetry interfaces, safety-critical process controls.",
        repo_evidence_paths=("src/spiralverse/", "src/fleet/", "packages/agent-bus/"),
        current_status="FAIL",
        gap=(
            "Repo has governance, fleet, and bus abstractions, but no cFS/F Prime/ROS2 adapter, command/telemetry "
            "dictionary, flight-app lifecycle model, or safety-critical runtime profile."
        ),
        next_target=(
            "Create a non-flight, simulation-only adapter target: command packet, telemetry packet, app lifecycle, "
            "fault event, and deterministic replay."
        ),
    ),
    Target(
        target_id="geofence_flight_envelope",
        source_ids=("USAF-SKYBORG-ACS",),
        benchmark_target="Geofence, flight-envelope, navigation-command, and coordinated maneuver checks",
        target_standard="Autonomy responds to navigation commands while respecting geofences and aircraft flight envelopes.",
        repo_evidence_paths=(
            "src/geoseal_cli.py",
            "src/video_lattice/",
            "external_repos/spiralverse-protocol/src/fleet/",
        ),
        current_status="FAIL",
        gap=(
            "SCBE can gate commands semantically, but it does not yet simulate geofence polygons, vehicle dynamics, "
            "control limits, flight envelope constraints, or coordinated maneuver timing."
        ),
        next_target=(
            "Add a geofence/envelope benchmark: command accepted only if route stays inside permitted polygons, "
            "speed/turn/altitude bounds, and coordinated maneuver separation limits."
        ),
    ),
    Target(
        target_id="open_autonomy_architecture",
        source_ids=("USAF-AGRA-CCA",),
        benchmark_target="Open modular autonomy architecture",
        target_standard="Mission autonomy decoupled from platform hardware; vendor/model swap without breaking control contracts.",
        repo_evidence_paths=(
            "packages/agent-bus/tools.json",
            "packages/agent-bus/src/hermes.ts",
            "packages/agent-bus/src/tools.ts",
        ),
        current_status="PARTIAL",
        gap=(
            "Agent-bus tool registry and model lanes are a good software-first start, but the repo lacks a "
            "vehicle/autonomy interface contract, versioned simulation harness, and cross-vendor conformance tests."
        ),
        next_target=(
            "Define an SCBE Autonomy Reference Interface with plan, observe, command, veto, explain, and receipt "
            "messages, then run two independent mock providers through the same conformance suite."
        ),
    ),
    Target(
        target_id="ground_control_integration",
        source_ids=("USAF-CCA-GROUND-TEST",),
        benchmark_target="Ground-control and autonomy-integration readiness",
        target_standard="Ground tests cover propulsion, avionics, autonomy integration, and ground control interfaces.",
        repo_evidence_paths=(
            "packages/agent-bus/",
            "scripts/video_lattice/ue5_server.py",
        ),
        current_status="FAIL",
        gap=(
            "Current harnesses are CLI/software tests. There is no ground-control UI contract, avionics/propulsion "
            "sim boundary, hardware abstraction, or operator intervention loop."
        ),
        next_target=(
            "Add a simulation-only ground-control contract with operator command, autonomy recommendation, veto, "
            "telemetry stream, and fault-injection transcript."
        ),
    ),
    Target(
        target_id="runtime_assurance_control_filter",
        source_ids=("AFRL-STARS-RTA",),
        benchmark_target="Runtime assurance safety filter for AI control outputs",
        target_standard="Monitor AI control output; modify or substitute unsafe control signal before environment execution.",
        repo_evidence_paths=(
            "src/governance/",
            "packages/agent-bus/src/pipeline.ts",
            "src/video_lattice/frame_corrector.py",
        ),
        current_status="PARTIAL",
        gap=(
            "SCBE has ALLOW/DENY/QUARANTINE and correction signals, but does not yet prove control-signal "
            "substitution against a vehicle/satellite dynamics model."
        ),
        next_target=(
            "Extend runtime gate fixtures with proposed-control, safety-filtered-control, substituted-control, "
            "environment-state-before/after, and hazard-avoidance proof."
        ),
    ),
)


def path_status(paths: tuple[str, ...]) -> dict[str, bool]:
    return {p: (ROOT / p).exists() for p in paths}


def build_report() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    counts = {"PASS": 0, "PARTIAL": 0, "FAIL": 0}
    for target in TARGETS:
        counts[target.current_status] += 1
        rows.append(
            {
                "target_id": target.target_id,
                "benchmark_target": target.benchmark_target,
                "source_ids": list(target.source_ids),
                "target_standard": target.target_standard,
                "current_status": target.current_status,
                "repo_evidence_paths": list(target.repo_evidence_paths),
                "repo_evidence_exists": path_status(target.repo_evidence_paths),
                "gap": target.gap,
                "next_target": target.next_target,
            }
        )
    return {
        "schema_version": "scbe_nasa_usaf_autonomy_target_matrix_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "decision": (
            "TARGETS_REQUIRED" if counts["FAIL"] or counts["PARTIAL"] else "PASS"
        ),
        "summary": {
            "target_count": len(TARGETS),
            "pass": counts["PASS"],
            "partial": counts["PARTIAL"],
            "fail": counts["FAIL"],
            "highest_value_next_targets": [
                "DAA-lite ownship/traffic encounter benchmark",
                "runtime assurance control-signal substitution fixture",
                "SCBE Autonomy Reference Interface conformance suite",
                "requirements-to-test trace matrix",
            ],
        },
        "sources": [source.__dict__ for source in SOURCES],
        "targets": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# NASA/USAF Autonomy Target Matrix",
        "",
        f"Generated: {report['generated_at']}",
        f"Decision: `{report['decision']}`",
        "",
        "## Summary",
        "",
        f"- Targets: {report['summary']['target_count']}",
        f"- Pass: {report['summary']['pass']}",
        f"- Partial: {report['summary']['partial']}",
        f"- Fail: {report['summary']['fail']}",
        "",
        "Highest-value next targets:",
    ]
    lines.extend(
        f"- {item}" for item in report["summary"]["highest_value_next_targets"]
    )
    lines.extend(
        [
            "",
            "## Target Matrix",
            "",
            "| Target | Status | Gap | Next Target |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in report["targets"]:
        lines.append(
            "| {target} | {status} | {gap} | {next_target} |".format(
                target=row["benchmark_target"].replace("|", "/"),
                status=row["current_status"],
                gap=row["gap"].replace("|", "/"),
                next_target=row["next_target"].replace("|", "/"),
            )
        )
    lines.extend(["", "## Sources", ""])
    for source in report["sources"]:
        lines.append(f"- `{source['source_id']}`: [{source['title']}]({source['url']})")
        lines.append(f"  - {source['observed_standard']}")
    lines.append("")
    return "\n".join(lines)


def write_report(report: dict[str, Any], json_out: Path, md_out: Path) -> None:
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(render_markdown(report), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md-out", type=Path, default=DEFAULT_MD)
    parser.add_argument(
        "--json", action="store_true", help="Print JSON report to stdout"
    )
    args = parser.parse_args()

    report = build_report()
    write_report(report, args.json_out, args.md_out)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"wrote {args.json_out}")
        print(f"wrote {args.md_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
