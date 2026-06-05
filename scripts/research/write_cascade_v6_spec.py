"""Write the cascade-v6 controller spec.

Cascade v6 freezes the post-K rule before Ring L:

  frz_mean > 0.45 and frz_skew > 1.0 -> frozen_dominant

Ring K is not a blind validation point for v6; it is the postmortem that
introduced the branch. Ring L is the next unseen test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "range_regime_classifier"
V5_SPEC_PATH = OUT_DIR / "cascade_v5_spec.json"
RING_K_PATH = REPO_ROOT / "artifacts" / "ring_k_cascade_v5" / "ring_k_results.json"

CEN_STD_THRESHOLD = 0.97974
FRZ_SKEW_THRESHOLD = 0.4495
FRZ_MEAN_EARLY_THRESHOLD = 0.15
FRZ_MEAN_LATE_THRESHOLD = 0.27
FRZ_STD_COMPRESSED_THRESHOLD = 0.9621
FRZ_KURT_LATE_THRESHOLD = 0.80
FRZ_DOMINANT_MEAN_THRESHOLD = 0.45
FRZ_DOMINANT_SKEW_THRESHOLD = 1.0

WEIGHTS = {
    "frozen_dominant": {"w_f": 1.0, "w_a": 0.0, "w_c": 0.0},
    "dominant": {"w_f": -1.5, "w_a": 0.0, "w_c": 1.0},
    "magnitude": {"w_f": 0.5, "w_a": 2.0, "w_c": 2.0},
    "frozen_coherent": {"w_f": 1.0, "w_a": 0.0, "w_c": 1.5},
    "compressed_frozen_early": {"w_f": -1.5, "w_a": 0.0, "w_c": 1.0},
    "compressed_frozen_late_low_kurt": {"w_f": 0.5, "w_a": 2.0, "w_c": 2.0},
    "compressed_frozen_late_high_kurt": {"w_f": -1.5, "w_a": 0.0, "w_c": 1.0},
}


def predict_v6(features: dict[str, float]) -> tuple[str, list[str]]:
    if (
        features.get("frz_mean", 0.0) > FRZ_DOMINANT_MEAN_THRESHOLD
        and features.get("frz_skew", 0.0) > FRZ_DOMINANT_SKEW_THRESHOLD
    ):
        return "frozen_dominant", ["frz_mean>0.45", "frz_skew>1.0"]

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


def _expected_winner(regime: str) -> str:
    if regime == "frozen_dominant":
        return "frozen"
    if regime in {"magnitude", "compressed_frozen_late_low_kurt"}:
        return "magnitude"
    if regime in {"dominant", "compressed_frozen_early", "compressed_frozen_late_high_kurt"}:
        return "dominant"
    return "frozen_coherent"


def _v5_rows() -> list[dict[str, Any]]:
    data = json.loads(V5_SPEC_PATH.read_text(encoding="utf-8"))
    rows = []
    for row in data["validation"]["rings"]:
        rows.append(
            {
                "ring": row["ring"],
                "range": row["range"],
                "features": row["features"],
                "winner": row["winner"],
                "hits": row["hits"],
                "total_anchors": row["total_anchors"],
                "source": "cascade_v5_spec",
            }
        )
    return rows


def _ring_k_row() -> dict[str, Any]:
    data = json.loads(RING_K_PATH.read_text(encoding="utf-8"))
    return {
        "ring": "K",
        "range": data["range"],
        "features": data["ring_k_features"],
        "winner": data["results"]["winner"],
        "hits": data["results"]["frozen_hits"],
        "total_anchors": data["results"]["total_anchors"],
        "source": "ring_k_cascade_v5",
        "k_observation": {
            "frozen_hits": data["results"]["frozen_hits"],
            "dominant_hits": data["results"]["dominant_hits"],
            "magnitude_hits": data["results"]["magnitude_hits"],
            "frozen_coherent_hits": data["results"]["frozen_coherent_hits"],
        },
    }


def _evidence_rows() -> list[dict[str, Any]]:
    rows = [*_v5_rows(), _ring_k_row()]
    for row in rows:
        regime, fired = predict_v6(row["features"])
        row["v6_regime"] = regime
        row["v6_weights"] = WEIGHTS[regime]
        row["v6_fired"] = fired
        row["v6_expected_winner"] = _expected_winner(regime)
        row["correct"] = row["v6_expected_winner"] == row["winner"]
    return rows


def build_spec() -> dict[str, Any]:
    evidence = _evidence_rows()
    return {
        "schema": "range_regime_cascade_v6",
        "date": "2026-06-04",
        "purpose": "Frozen controller selection rule after Ring K, frozen before Ring L.",
        "claim_boundary": "Uses K postmortem truth to add frozen_dominant. Ring L is the next unseen validation.",
        "rules": [
            {
                "order": 1,
                "predicate": f"frz_mean > {FRZ_DOMINANT_MEAN_THRESHOLD} and frz_skew > {FRZ_DOMINANT_SKEW_THRESHOLD}",
                "regime": "frozen_dominant",
                "weights": WEIGHTS["frozen_dominant"],
                "reason": "Frozen distribution is concentrated and right-skewed enough that raw frozen top-20 is best.",
            },
            {
                "order": 2,
                "predicate": f"cen_std < {CEN_STD_THRESHOLD}",
                "regime": "magnitude",
                "weights": WEIGHTS["magnitude"],
                "reason": "D-anomaly / low centroid spread.",
            },
            {
                "order": 3,
                "predicate": (
                    f"frz_skew > {FRZ_SKEW_THRESHOLD} and frz_mean > {FRZ_MEAN_LATE_THRESHOLD} "
                    f"and frz_std < {FRZ_STD_COMPRESSED_THRESHOLD} and frz_kurt < {FRZ_KURT_LATE_THRESHOLD}"
                ),
                "regime": "compressed_frozen_late_low_kurt",
                "weights": WEIGHTS["compressed_frozen_late_low_kurt"],
                "reason": "Late compressed frozen with low kurtosis; activate magnitude.",
            },
            {
                "order": 4,
                "predicate": (
                    f"frz_skew > {FRZ_SKEW_THRESHOLD} and frz_mean > {FRZ_MEAN_LATE_THRESHOLD} "
                    f"and frz_std < {FRZ_STD_COMPRESSED_THRESHOLD} and frz_kurt >= {FRZ_KURT_LATE_THRESHOLD}"
                ),
                "regime": "compressed_frozen_late_high_kurt",
                "weights": WEIGHTS["compressed_frozen_late_high_kurt"],
                "reason": "Late compressed frozen with high kurtosis; use dominant/adversarial frozen.",
            },
            {
                "order": 5,
                "predicate": (
                    f"frz_skew > {FRZ_SKEW_THRESHOLD} and frz_mean > {FRZ_MEAN_EARLY_THRESHOLD} "
                    f"and frz_std < {FRZ_STD_COMPRESSED_THRESHOLD}"
                ),
                "regime": "compressed_frozen_early",
                "weights": WEIGHTS["compressed_frozen_early"],
                "reason": "Early compressed frozen phase; suppress over-compressed frozen lane.",
            },
            {
                "order": 6,
                "predicate": f"frz_skew > {FRZ_SKEW_THRESHOLD}",
                "regime": "frozen_coherent",
                "weights": WEIGHTS["frozen_coherent"],
                "reason": "High frozen tail without global compression; preserve frozen and add centroid.",
            },
            {
                "order": 7,
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
            "frozen_dominant_frz_mean": FRZ_DOMINANT_MEAN_THRESHOLD,
            "frozen_dominant_frz_skew": FRZ_DOMINANT_SKEW_THRESHOLD,
        },
        "weights": WEIGHTS,
        "validation": {
            "rings": evidence,
            "correct": sum(1 for row in evidence if row["correct"]),
            "total": len(evidence),
        },
        "next_test": {
            "ring": "L",
            "range": "650M-700M",
            "status": "unseen_anchor_boundary",
        },
    }


def write_markdown(spec: dict[str, Any], path: Path) -> None:
    lines = [
        "# Cascade v6 Spec",
        "",
        "Frozen rule update after Ring K.",
        "",
        "## Rule",
        "",
        "```text",
        f"if frz_mean > {FRZ_DOMINANT_MEAN_THRESHOLD} and frz_skew > {FRZ_DOMINANT_SKEW_THRESHOLD}:",
        "    frozen_dominant -> pure frozen gate",
        f"elif cen_std < {CEN_STD_THRESHOLD}:",
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
        "| Ring | frz_mean | frz_skew | frz_kurt | v6 regime | winner | correct |",
        "| --- | ---: | ---: | ---: | --- | --- | --- |",
    ]
    for row in spec["validation"]["rings"]:
        feats = row["features"]
        lines.append(
            f"| {row['ring']} | {feats['frz_mean']:.4f} | {feats['frz_skew']:.4f} | "
            f"{feats['frz_kurt']:.4f} | {row['v6_regime']} | {row['winner']} | "
            f"{'yes' if row['correct'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "Result: {correct}/{total} on H/I/J/K retrodiction.".format(**spec["validation"]),
            "",
            "## Boundary",
            "",
            "Cascade v6 uses Ring K truth to add the frozen_dominant branch. Ring L is still unopened.",
            "",
            "## Artifacts",
            "",
            "- `artifacts/range_regime_classifier/cascade_v6_spec.json`",
            "- `artifacts/range_regime_classifier/CASCADE_V6.md`",
            "- `artifacts/ring_k_cascade_v5/ring_k_results.json`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    spec = build_spec()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = OUT_DIR / "cascade_v6_spec.json"
    md_path = OUT_DIR / "CASCADE_V6.md"
    json_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    write_markdown(spec, md_path)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    print(f"Validation: {spec['validation']['correct']}/{spec['validation']['total']}")


if __name__ == "__main__":
    main()
