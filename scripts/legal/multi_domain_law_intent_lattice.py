#!/usr/bin/env python3
"""Multi-domain law intent lattice.

This harness treats legal intent as a trace-backed semantic classification
problem across law cultures. It does not give legal advice and does not decide
real cases. It tests whether the same evidence packet supports intent under
different domain vocabularies:

- common law / MPC-style mens rea,
- civil-law dolus/culpa framing,
- international criminal law Article 30 intent and knowledge,
- Islamic-law criminal responsibility framing,
- restorative/customary responsibility framing.

The point for SCBE is narrow: intent is inferred from observable traces under a
burden of proof. This gives the governance lattice a legal comparison layer.
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "docs" / "legal" / "patent-workbench" / "benchmarks"

AXES: tuple[str, ...] = (
    "volition",
    "knowledge",
    "foreseeability",
    "risk_disregard",
    "preparation",
    "concealment",
    "harm_link",
    "repair_response",
)


@dataclass(frozen=True)
class LawDomain:
    domain_id: str
    label: str
    basis: str
    weights: tuple[float, ...]
    threshold: float
    caution: str


@dataclass(frozen=True)
class EvidencePacket:
    packet_id: str
    label: str
    facts: tuple[str, ...]
    vector: tuple[float, ...]
    expected_high_domains: tuple[str, ...]


DOMAINS: tuple[LawDomain, ...] = (
    LawDomain(
        domain_id="common_law_mens_rea",
        label="Common law / MPC mens rea",
        basis="Purpose, knowledge, recklessness, negligence; intent inferred from acts and circumstances.",
        weights=(0.24, 0.19, 0.14, 0.14, 0.10, 0.09, 0.07, 0.03),
        threshold=0.56,
        caution="Distinguish motive from intent and read the governing statute.",
    ),
    LawDomain(
        domain_id="civil_law_dolus_culpa",
        label="Civil-law dolus / culpa",
        basis="Direct or indirect intent, conditional intent, and negligence framed through codes.",
        weights=(0.20, 0.22, 0.18, 0.12, 0.08, 0.07, 0.10, 0.03),
        threshold=0.55,
        caution="Code text controls; dolus eventualis treatment varies by jurisdiction.",
    ),
    LawDomain(
        domain_id="icc_article_30",
        label="International criminal law Article 30",
        basis="Intent and knowledge: means to engage in conduct or is aware consequence will occur ordinarily.",
        weights=(0.26, 0.26, 0.20, 0.05, 0.07, 0.04, 0.10, 0.02),
        threshold=0.60,
        caution="Rome Statute crimes may include special mental elements outside Article 30.",
    ),
    LawDomain(
        domain_id="islamic_criminal_responsibility",
        label="Islamic-law criminal responsibility",
        basis="Guilty intention/criminal responsibility with strict proof rules in some offense categories.",
        weights=(0.22, 0.20, 0.12, 0.10, 0.08, 0.08, 0.11, 0.09),
        threshold=0.58,
        caution="Evidentiary rules vary strongly by offense class and jurisdiction.",
    ),
    LawDomain(
        domain_id="restorative_customary_responsibility",
        label="Restorative/customary responsibility",
        basis="Responsibility inferred through harm, relational breach, warnings, repair, and community context.",
        weights=(0.13, 0.14, 0.14, 0.13, 0.06, 0.06, 0.18, 0.16),
        threshold=0.50,
        caution="This is a comparative abstraction, not one unified formal code.",
    ),
)


PACKETS: tuple[EvidencePacket, ...] = (
    EvidencePacket(
        packet_id="planned_targeted_action",
        label="Planned targeted action with concealment",
        facts=(
            "Actor researched the target system.",
            "Actor selected a method that predictably caused the prohibited effect.",
            "Actor concealed logs afterward.",
        ),
        vector=(0.90, 0.85, 0.80, 0.65, 0.88, 0.78, 0.82, 0.10),
        expected_high_domains=("common_law_mens_rea", "civil_law_dolus_culpa", "icc_article_30"),
    ),
    EvidencePacket(
        packet_id="reckless_known_risk",
        label="Known risk consciously disregarded",
        facts=(
            "Actor received a warning.",
            "Actor proceeded without safeguards.",
            "The harm matched the warned-of risk.",
        ),
        vector=(0.45, 0.72, 0.82, 0.92, 0.30, 0.20, 0.78, 0.25),
        expected_high_domains=("common_law_mens_rea", "civil_law_dolus_culpa", "restorative_customary_responsibility"),
    ),
    EvidencePacket(
        packet_id="accident_with_repair",
        label="Accident with immediate repair behavior",
        facts=(
            "Actor did not prepare the harmful event.",
            "Actor lacked notice of the specific risk.",
            "Actor stopped and repaired damage immediately.",
        ),
        vector=(0.12, 0.18, 0.20, 0.14, 0.05, 0.02, 0.35, 0.90),
        expected_high_domains=(),
    ),
    EvidencePacket(
        packet_id="knowledge_without_purpose",
        label="Knowledge without desire to cause the consequence",
        facts=(
            "Actor did not desire the consequence.",
            "Actor knew the consequence would occur in ordinary course.",
            "Actor continued the conduct anyway.",
        ),
        vector=(0.42, 0.94, 0.88, 0.45, 0.40, 0.22, 0.86, 0.18),
        expected_high_domains=("civil_law_dolus_culpa", "icc_article_30"),
    ),
)


def dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(x * y for x, y in zip(a, b))


def norm(v: tuple[float, ...]) -> float:
    return math.sqrt(sum(x * x for x in v))


def cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    denom = norm(a) * norm(b)
    if denom <= 1e-12:
        return 0.0
    return dot(a, b) / denom


def weighted_support(packet: EvidencePacket, domain: LawDomain) -> float:
    return dot(packet.vector, domain.weights) / max(sum(domain.weights), 1e-12)


def classify_support(score: float, threshold: float) -> str:
    if score >= threshold + 0.12:
        return "strong"
    if score >= threshold:
        return "supported"
    if score >= threshold - 0.12:
        return "borderline"
    return "weak"


def dark_space_score(packet: EvidencePacket) -> float:
    """Inverse/legal-dark score.

    High values mean the packet sits in an adverse inference region: knowledge,
    foreseeability, disregard, preparation, concealment, and harm are high while
    repair response is low. This is the "no stars are born" region: few lawful
    or restorative anchors appear from the trace.
    """

    axis = dict(zip(AXES, packet.vector))
    adverse = (
        0.18 * axis["knowledge"]
        + 0.16 * axis["foreseeability"]
        + 0.16 * axis["risk_disregard"]
        + 0.16 * axis["preparation"]
        + 0.18 * axis["concealment"]
        + 0.16 * axis["harm_link"]
    )
    repair_credit = 0.30 * axis["repair_response"]
    return max(0.0, min(1.0, adverse - repair_credit))


def dark_space_class(score: float) -> str:
    if score >= 0.70:
        return "dark_core"
    if score >= 0.48:
        return "shadow_region"
    if score >= 0.28:
        return "gray_region"
    return "star_bearing"


def evaluate_packet(packet: EvidencePacket) -> dict[str, Any]:
    domains = []
    for domain in DOMAINS:
        score = weighted_support(packet, domain)
        domains.append(
            {
                "domain_id": domain.domain_id,
                "label": domain.label,
                "basis": domain.basis,
                "semantic_similarity": round(cosine(packet.vector, domain.weights), 4),
                "support_score": round(score, 4),
                "threshold": domain.threshold,
                "classification": classify_support(score, domain.threshold),
                "caution": domain.caution,
            }
        )
    domains.sort(key=lambda item: item["support_score"], reverse=True)
    high = tuple(
        item["domain_id"]
        for item in domains
        if item["classification"] in {"strong", "supported"}
    )
    dark_score = dark_space_score(packet)
    return {
        "packet_id": packet.packet_id,
        "label": packet.label,
        "facts": list(packet.facts),
        "axis_values": dict(zip(AXES, packet.vector)),
        "inverse_criminality_space": {
            "dark_space_score": round(dark_score, 4),
            "class": dark_space_class(dark_score),
            "meaning": (
                "Adverse-inference region: high knowledge/risk/preparation/concealment/harm "
                "with low repair response. This is not a conviction metric."
            ),
        },
        "expected_high_domains": list(packet.expected_high_domains),
        "supported_domains": list(high),
        "domains": domains,
    }


def run_lattice() -> dict[str, Any]:
    cases = [evaluate_packet(packet) for packet in PACKETS]
    exact_or_subset = 0
    for case in cases:
        expected = set(case["expected_high_domains"])
        supported = set(case["supported_domains"])
        if expected.issubset(supported):
            exact_or_subset += 1
    return {
        "schema": "scbe_multi_domain_law_intent_lattice_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Map observable intent evidence onto multi-domain legal semantic bases.",
        "axes": list(AXES),
        "law_domains": [asdict(domain) for domain in DOMAINS],
        "case_count": len(cases),
        "metrics": {
            "expected_domain_coverage_cases": exact_or_subset,
            "expected_domain_coverage_rate": round(exact_or_subset / len(cases), 4),
            "domain_count": len(DOMAINS),
            "axis_count": len(AXES),
            "dark_core_cases": sum(
                1 for case in cases if case["inverse_criminality_space"]["class"] == "dark_core"
            ),
            "star_bearing_cases": sum(
                1 for case in cases if case["inverse_criminality_space"]["class"] == "star_bearing"
            ),
        },
        "sources": [
            {
                "name": "Cornell Wex intent",
                "url": "https://www.law.cornell.edu/wex/intent",
                "use": "Common-law intent and circumstantial evidence framing.",
            },
            {
                "name": "Cornell Wex criminal intent",
                "url": "https://www.law.cornell.edu/wex/criminal_intent",
                "use": "MPC-style culpability categories.",
            },
            {
                "name": "Rome Statute Article 30",
                "url": "https://ihl-databases.icrc.org/en/ihl-treaties/icc-statute-1998/article-30",
                "use": "International criminal law intent and knowledge standard.",
            },
            {
                "name": "Islam, mental health and law overview",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC5498891/",
                "use": "Islamic-law recognition of mens rea/criminal responsibility.",
            },
        ],
        "cases": cases,
        "cautious_language": (
            "This lattice compares semantic support for intent-like mental elements across selected legal "
            "traditions. The inverse criminality space marks adverse-inference darkness, not guilt. Real "
            "legal outcomes depend on the jurisdiction, offense, evidence rules, burden of proof, and fact finder."
        ),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Multi-Domain Law Intent Lattice",
        "",
        report["cautious_language"],
        "",
        "## Semantic Axes",
        "",
        ", ".join(f"`{axis}`" for axis in report["axes"]),
        "",
        "## Metrics",
        "",
    ]
    for key, value in report["metrics"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(
        [
            "",
            "## Case Table",
            "",
            "| Packet | Top domain | Top score | Dark class | Supported domains |",
            "| --- | --- | ---: | --- | --- |",
        ]
    )
    for case in report["cases"]:
        top = case["domains"][0]
        lines.append(
            f"| {case['packet_id']} | {top['domain_id']} | {top['support_score']} | "
            f"{case['inverse_criminality_space']['class']} | "
            f"{', '.join(case['supported_domains']) or 'none'} |"
        )
    lines.extend(
        [
            "",
            "## Domain Bases",
            "",
        ]
    )
    for domain in report["law_domains"]:
        lines.extend(
            [
                f"### {domain['label']}",
                "",
                f"- Basis: {domain['basis']}",
                f"- Threshold: `{domain['threshold']}`",
                f"- Caution: {domain['caution']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Sources",
            "",
        ]
    )
    for source in report["sources"]:
        lines.append(f"- [{source['name']}]({source['url']}) - {source['use']}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the multi-domain law intent lattice.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--json-name", default="multi_domain_law_intent_lattice.json")
    parser.add_argument("--md-name", default="multi_domain_law_intent_lattice.md")
    args = parser.parse_args(argv)

    report = run_lattice()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / args.json_name
    md_path = args.output_dir / args.md_name
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_markdown(report, md_path)
    print(
        json.dumps(
            {
                "json": _display_path(json_path),
                "markdown": _display_path(md_path),
                **report["metrics"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
