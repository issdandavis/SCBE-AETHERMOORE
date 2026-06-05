"""Write the cascade-v5 controller spec.

Cascade v5 freezes the post-J rule:

  late compressed frozen + frz_kurt < 0.80  -> magnitude
  late compressed frozen + frz_kurt >= 0.80 -> dominant

It is validated retrodictively on H/I/J and should be treated as the frozen
rule for the next unseen ring after the feature-only pass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "range_regime_classifier"
RING_I_PATH = REPO_ROOT / "artifacts" / "ring_i_cascade_v4" / "ring_i_results.json"
RING_J_PATH = REPO_ROOT / "artifacts" / "ring_j_cascade_v4" / "ring_j_results.json"

CEN_STD_THRESHOLD = 0.97974
FRZ_SKEW_THRESHOLD = 0.4495
FRZ_MEAN_EARLY_THRESHOLD = 0.15
FRZ_MEAN_LATE_THRESHOLD = 0.27
FRZ_STD_COMPRESSED_THRESHOLD = 0.9621
FRZ_KURT_LATE_THRESHOLD = 0.80

WEIGHTS = {
    "dominant": {"w_f": -1.5, "w_a": 0.0, "w_c": 1.0},
    "magnitude": {"w_f": 0.5, "w_a": 2.0, "w_c": 2.0},
    "frozen_coherent": {"w_f": 1.0, "w_a": 0.0, "w_c": 1.5},
    "compressed_frozen_early": {"w_f": -1.5, "w_a": 0.0, "w_c": 1.0},
    "compressed_frozen_late_low_kurt": {"w_f": 0.5, "w_a": 2.0, "w_c": 2.0},
    "compressed_frozen_late_high_kurt": {"w_f": -1.5, "w_a": 0.0, "w_c": 1.0},
}

RING_H_FEATURES = {
    "frz_mean": 0.3232,
    "frz_std": 0.8769,
    "frz_skew": 0.8094,
    "frz_kurt": 0.5594,
    "cen_std": 1.0118,
}


def predict_v5(features: dict[str, float]) -> tuple[str, list[str]]:
    if features.get("cen_std", 1.0) < CEN_STD_THRESHOLD:
        return "magnitude", ["cen_std"]

    if features.get("frz_skew", 0.0) > FRZ_SKEW_THRESHOLD:
        compressed = (
            features.get("frz_mean", 0.0) > FRZ_MEAN_EARLY_THRESHOLD
            and features.get("frz_std", 1.0) < FRZ_STD_COMPRESSED_THRESHOLD
        )
        if compressed and features.get("frz_mean", 0.0) > FRZ_MEAN_LATE_THRESHOLD:
            fired = ["frz_skew", "frz_mean", "frz_std", "frz_kurt"]
            if features.get("frz_kurt", 0.0) < FRZ_KURT_LATE_THRESHOLD:
                return "compressed_frozen_late_low_kurt", fired
            return "compressed_frozen_late_high_kurt", fired
        if compressed:
            return "compressed_frozen_early", ["frz_skew", "frz_mean", "frz_std"]
        return "frozen_coherent", ["frz_skew"]

    return "dominant", []


def _ring_i_evidence() -> dict[str, Any]:
    data = json.loads(RING_I_PATH.read_text(encoding="utf-8"))
    winner = data["results"]["winner"]
    return {
        "features": data["ring_i_features"],
        "winner": winner,
        "hits": data["results"][f"{winner}_hits"],
        "total_anchors": data["results"]["total_anchors"],
    }


def _ring_j_evidence() -> dict[str, Any]:
    data = json.loads(RING_J_PATH.read_text(encoding="utf-8"))
    return {
        "features": data["ring_j_features"],
        "winner": data["results"]["winner"],
        "hits": data["results"][f"{data['results']['winner']}_hits"],
        "total_anchors": data["results"]["total_anchors"],
    }


def _expected_winner(regime: str) -> str:
    if regime in {"magnitude", "compressed_frozen_late_low_kurt"}:
        return "magnitude"
    if regime in {"dominant", "compressed_frozen_early", "compressed_frozen_late_high_kurt"}:
        return "dominant"
    return "frozen_coherent"


def _evidence_rows() -> list[dict[str, Any]]:
    rows = [
        {
            "ring": "H",
            "range": "450M-500M",
            "features": RING_H_FEATURES,
            "winner": "magnitude",
            "hits": 11,
            "total_anchors": 221,
        },
        {"ring": "I", "range": "500M-550M", **_ring_i_evidence()},
        {"ring": "J", "range": "550M-600M", **_ring_j_evidence()},
    ]
    for row in rows:
        regime, fired = predict_v5(row["features"])
        row["v5_regime"] = regime
        row["v5_weights"] = WEIGHTS[regime]
        row["v5_fired"] = fired
        row["v5_expected_winner"] = _expected_winner(regime)
        row["correct"] = row["v5_expected_winner"] == row["winner"]
    return rows


def main() -> None:
    evidence = _evidence_rows()
    spec: dict[str, Any] = {
        "schema": "range_regime_cascade_v5",
        "date": "2026-06-04",
        "purpose": "Frozen controller selection rule after Ring J.",
        "claim_boundary": (
            "Uses H/I/J postmortem geometry. Do not tune with Ring K anchor truth; "
            "compute Ring K features first, then apply this cascade."
        ),
        "rules": [
            {
                "order": 1,
                "predicate": f"cen_std < {CEN_STD_THRESHOLD}",
                "regime": "magnitude",
                "weights": WEIGHTS["magnitude"],
                "reason": "D-anomaly / low centroid spread.",
            },
            {
                "order": 2,
                "predicate": (
                    f"frz_skew > {FRZ_SKEW_THRESHOLD} and "
                    f"frz_mean > {FRZ_MEAN_LATE_THRESHOLD} and "
                    f"frz_std < {FRZ_STD_COMPRESSED_THRESHOLD} and "
                    f"frz_kurt < {FRZ_KURT_LATE_THRESHOLD}"
                ),
                "regime": "compressed_frozen_late_low_kurt",
                "weights": WEIGHTS["compressed_frozen_late_low_kurt"],
                "reason": "Late compressed frozen with low kurtosis; activate magnitude.",
            },
            {
                "order": 3,
                "predicate": (
                    f"frz_skew > {FRZ_SKEW_THRESHOLD} and "
                    f"frz_mean > {FRZ_MEAN_LATE_THRESHOLD} and "
                    f"frz_std < {FRZ_STD_COMPRESSED_THRESHOLD} and "
                    f"frz_kurt >= {FRZ_KURT_LATE_THRESHOLD}"
                ),
                "regime": "compressed_frozen_late_high_kurt",
                "weights": WEIGHTS["compressed_frozen_late_high_kurt"],
                "reason": "Late compressed frozen with high kurtosis; use dominant/adversarial frozen.",
            },
            {
                "order": 4,
                "predicate": (
                    f"frz_skew > {FRZ_SKEW_THRESHOLD} and "
                    f"frz_mean > {FRZ_MEAN_EARLY_THRESHOLD} and "
                    f"frz_std < {FRZ_STD_COMPRESSED_THRESHOLD}"
                ),
                "regime": "compressed_frozen_early",
                "weights": WEIGHTS["compressed_frozen_early"],
                "reason": "Early compressed frozen phase; suppress over-compressed frozen lane.",
            },
            {
                "order": 5,
                "predicate": f"frz_skew > {FRZ_SKEW_THRESHOLD}",
                "regime": "frozen_coherent",
                "weights": WEIGHTS["frozen_coherent"],
                "reason": "High frozen tail without global compression; preserve frozen and add centroid.",
            },
            {
                "order": 6,
                "predicate": "default",
                "regime": "dominant",
                "weights": WEIGHTS["dominant"],
                "reason": "Default centroid-friendly/adversarial frozen controller.",
            },
        ],
        "thresholds": {
            "cen_std": CEN_STD_THRESHOLD,
            "frz_skew": FRZ_SKEW_THRESHOLD,
            "frz_mean_early": FRZ_MEAN_EARLY_THRESHOLD,
            "frz_mean_late": FRZ_MEAN_LATE_THRESHOLD,
            "frz_std_compressed": FRZ_STD_COMPRESSED_THRESHOLD,
            "frz_kurt_late": FRZ_KURT_LATE_THRESHOLD,
        },
        "weights": WEIGHTS,
        "validation": {
            "rings": evidence,
            "correct": sum(1 for row in evidence if row["correct"]),
            "total": len(evidence),
        },
        "next_test": {
            "ring": "K",
            "range": "600M-650M",
            "status": "unseen_anchor_boundary",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "cascade_v5_spec.json"
    out_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Cascade v5 Spec",
        "",
        "Frozen rule update after Ring J.",
        "",
        "## Rule",
        "",
        "```text",
        f"if cen_std < {CEN_STD_THRESHOLD}:",
        "    magnitude",
        f"elif frz_skew > {FRZ_SKEW_THRESHOLD} and frz_mean > {FRZ_MEAN_LATE_THRESHOLD} and frz_std < {FRZ_STD_COMPRESSED_THRESHOLD} and frz_kurt < {FRZ_KURT_LATE_THRESHOLD}:",
        "    compressed_frozen_late_low_kurt -> magnitude weights",
        f"elif frz_skew > {FRZ_SKEW_THRESHOLD} and frz_mean > {FRZ_MEAN_LATE_THRESHOLD} and frz_std < {FRZ_STD_COMPRESSED_THRESHOLD} and frz_kurt >= {FRZ_KURT_LATE_THRESHOLD}:",
        "    compressed_frozen_late_high_kurt -> dominant weights",
        f"elif frz_skew > {FRZ_SKEW_THRESHOLD} and frz_mean > {FRZ_MEAN_EARLY_THRESHOLD} and frz_std < {FRZ_STD_COMPRESSED_THRESHOLD}:",
        "    compressed_frozen_early -> dominant weights",
        f"elif frz_skew > {FRZ_SKEW_THRESHOLD}:",
        "    frozen_coherent",
        "else:",
        "    dominant",
        "```",
        "",
        "## Validation",
        "",
        "| Ring | frz_mean | frz_kurt | v5 regime | winner | correct |",
        "| --- | ---: | ---: | --- | --- | --- |",
    ]
    for row in evidence:
        feats = row["features"]
        lines.append(
            f"| {row['ring']} | {feats['frz_mean']:.4f} | {feats['frz_kurt']:.4f} | "
            f"{row['v5_regime']} | {row['winner']} | {'yes' if row['correct'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            f"Result: {spec['validation']['correct']}/{spec['validation']['total']} on H/I/J.",
            "",
            "## Boundary",
            "",
            "This is the frozen controller for Ring K feature routing. Do not tune with Ring K anchor truth.",
            "",
            "## Artifacts",
            "",
            "- `artifacts/range_regime_classifier/cascade_v5_spec.json`",
            "- `artifacts/ring_j_cascade_v4/ring_j_results.json`",
            "- `artifacts/ring_i_cascade_v4/ring_i_results.json`",
        ]
    )
    report_path = OUT_DIR / "CASCADE_V5.md"
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
