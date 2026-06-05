"""Write the frozen cascade-v4 controller spec.

Cascade v4 is a rule update, not a benchmark run. It freezes the controller
selection rule before Ring I anchors are available.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "range_regime_classifier"
BRIDGE_PATH = REPO_ROOT / "artifacts" / "inverse_bridge_map" / "bridge_map.json"

CEN_STD_THRESHOLD = 0.97974
FRZ_SKEW_THRESHOLD = 0.4495
FRZ_MEAN_EARLY_THRESHOLD = 0.15
FRZ_STD_COMPRESSED_THRESHOLD = 0.9621
FRZ_MEAN_LATE_THRESHOLD = 0.27

WEIGHTS = {
    "dominant": {"w_f": -1.5, "w_a": 0.0, "w_c": 1.0},
    "magnitude": {"w_f": 0.5, "w_a": 2.0, "w_c": 2.0},
    "frozen_coherent": {"w_f": 1.0, "w_a": 0.0, "w_c": 1.5},
    "compressed_frozen_early": {"w_f": -1.5, "w_a": 0.0, "w_c": 1.0},
    "compressed_frozen_late": {"w_f": 0.5, "w_a": 2.0, "w_c": 2.0},
}


def predict_v4(features: dict[str, float]) -> tuple[str, list[str]]:
    if features.get("cen_std", 1.0) < CEN_STD_THRESHOLD:
        return "magnitude", ["cen_std"]
    if features.get("frz_skew", 0.0) > FRZ_SKEW_THRESHOLD:
        if (
            features.get("frz_mean", 0.0) > FRZ_MEAN_LATE_THRESHOLD
            and features.get("frz_std", 1.0) < FRZ_STD_COMPRESSED_THRESHOLD
        ):
            return "compressed_frozen_late", ["frz_skew", "frz_mean", "frz_std"]
        if (
            features.get("frz_mean", 0.0) > FRZ_MEAN_EARLY_THRESHOLD
            and features.get("frz_std", 1.0) < FRZ_STD_COMPRESSED_THRESHOLD
        ):
            return "compressed_frozen_early", ["frz_skew", "frz_mean", "frz_std"]
        return "frozen_coherent", ["frz_skew"]
    return "dominant", []


def main() -> None:
    bridge = json.loads(BRIDGE_PATH.read_text(encoding="utf-8"))
    prediction_i = bridge["prediction_I"]
    i_features = prediction_i["features"]
    i_regime, i_fired = predict_v4(i_features)

    spec: dict[str, Any] = {
        "schema": "range_regime_cascade_v4",
        "date": "2026-06-04",
        "purpose": "Frozen pre-anchor controller selection rule for Ring I.",
        "claim_boundary": (
            "Uses A-H postmortem geometry and inverse_bridge_map prediction. "
            "Does not use Ring I anchor truth."
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
                    f"frz_std < {FRZ_STD_COMPRESSED_THRESHOLD}"
                ),
                "regime": "compressed_frozen_late",
                "weights": WEIGHTS["compressed_frozen_late"],
                "reason": "Late compressed frozen phase; activate absolute frozen magnitude.",
            },
            {
                "order": 3,
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
                "order": 4,
                "predicate": f"frz_skew > {FRZ_SKEW_THRESHOLD}",
                "regime": "frozen_coherent",
                "weights": WEIGHTS["frozen_coherent"],
                "reason": "High frozen tail without global compression; preserve frozen and add centroid.",
            },
            {
                "order": 5,
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
        },
        "weights": WEIGHTS,
        "ring_i_prediction": {
            "features": i_features,
            "v3_regime": prediction_i.get("v3_regime"),
            "v3_weights": prediction_i.get("v3_w"),
            "fitted_weights": prediction_i.get("fitted_w"),
            "v4_regime": i_regime,
            "v4_fired": i_fired,
            "v4_weights": WEIGHTS[i_regime],
            "gap_to_fitted_line": prediction_i.get("gap_to_fill"),
            "gap_norm_v3": prediction_i.get("gap_norm"),
        },
        "next_test": {
            "ring": "I",
            "range": "500M-550M",
            "status": "unseen_anchor_boundary",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "cascade_v4_spec.json"
    out_path.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

    report_path = OUT_DIR / "CASCADE_V4.md"
    lines = [
        "# Cascade v4 Spec",
        "",
        "Frozen rule update before Ring I anchor truth is available.",
        "",
        "## Rule",
        "",
        "```text",
        f"if cen_std < {CEN_STD_THRESHOLD}:",
        "    magnitude",
        f"elif frz_skew > {FRZ_SKEW_THRESHOLD} and frz_mean > {FRZ_MEAN_LATE_THRESHOLD} and frz_std < {FRZ_STD_COMPRESSED_THRESHOLD}:",
        "    compressed_frozen_late -> magnitude weights",
        f"elif frz_skew > {FRZ_SKEW_THRESHOLD} and frz_mean > {FRZ_MEAN_EARLY_THRESHOLD} and frz_std < {FRZ_STD_COMPRESSED_THRESHOLD}:",
        "    compressed_frozen_early -> dominant weights",
        f"elif frz_skew > {FRZ_SKEW_THRESHOLD}:",
        "    frozen_coherent",
        "else:",
        "    dominant",
        "```",
        "",
        "## Ring I Prediction",
        "",
        f"- features: `{i_features}`",
        f"- v3 regime: `{prediction_i.get('v3_regime')}`",
        f"- v4 regime: `{i_regime}`",
        f"- v4 weights: `{WEIGHTS[i_regime]}`",
        "",
        "## Boundary",
        "",
        "This spec uses A-H postmortem geometry and does not use Ring I anchor truth.",
        "",
        "## Artifacts",
        "",
        "- `artifacts/range_regime_classifier/cascade_v4_spec.json`",
        "- `artifacts/inverse_bridge_map/bridge_map.json`",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
