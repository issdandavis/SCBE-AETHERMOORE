"""Build the A-L prime-fog manifold navigator.

This is a feature-only trajectory readout, not a scorer. It embeds historical
rings A-L in the common frozen/regime moment space and projects the next Ring M
direction without building the M cache or reading M anchors.
"""

from __future__ import annotations

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "artifacts" / "prime_fog_manifold_navigator"

REGIME_V2_PATH = REPO_ROOT / "artifacts" / "range_regime_classifier" / "regime_classifier_v2.json"
CASCADE_V6_PATH = REPO_ROOT / "artifacts" / "range_regime_classifier" / "cascade_v6_spec.json"
RING_L_PATH = REPO_ROOT / "artifacts" / "ring_l_cascade_v5" / "ring_l_results.json"

FEATURES = ("frz_mean", "frz_std", "frz_skew", "frz_kurt", "cen_std")
RING_ORDER = tuple("ABCDEFGHIJKL")

V6_FROZEN_MEAN_THRESHOLD = 0.45
V6_FROZEN_SKEW_THRESHOLD = 1.0
V6_CEN_STD_THRESHOLD = 0.97974
V6_FRZ_SKEW_THRESHOLD = 0.4495
V6_FRZ_MEAN_EARLY_THRESHOLD = 0.15
V6_FRZ_MEAN_LATE_THRESHOLD = 0.27
V6_FRZ_STD_COMPRESSED_THRESHOLD = 0.9621
V6_FRZ_KURT_THRESHOLD = 0.80


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def predict_v6(features: dict[str, float]) -> str:
    if (
        features.get("frz_mean", 0.0) > V6_FROZEN_MEAN_THRESHOLD
        and features.get("frz_skew", 0.0) > V6_FROZEN_SKEW_THRESHOLD
    ):
        return "frozen_dominant"
    if features.get("cen_std", 1.0) < V6_CEN_STD_THRESHOLD:
        return "magnitude"
    if features.get("frz_skew", 0.0) > V6_FRZ_SKEW_THRESHOLD:
        compressed = (
            features.get("frz_mean", 0.0) > V6_FRZ_MEAN_EARLY_THRESHOLD
            and features.get("frz_std", 1.0) < V6_FRZ_STD_COMPRESSED_THRESHOLD
        )
        if compressed and features.get("frz_mean", 0.0) > V6_FRZ_MEAN_LATE_THRESHOLD:
            if features.get("frz_kurt", 0.0) < V6_FRZ_KURT_THRESHOLD:
                return "compressed_frozen_late_low_kurt"
            return "compressed_frozen_late_high_kurt"
        if compressed:
            return "compressed_frozen_early"
        return "frozen_coherent"
    return "dominant"


def collect_ring_features() -> list[dict[str, Any]]:
    regime_v2 = load_json(REGIME_V2_PATH)
    cascade_v6 = load_json(CASCADE_V6_PATH)
    ring_l = load_json(RING_L_PATH)

    rows: dict[str, dict[str, Any]] = {}
    v2_truth = regime_v2.get("retrodiction", {})
    for ring in "ABCDEFG":
        features = regime_v2["range_features"][ring]
        rows[ring] = {
            "ring": ring,
            "range": _range_for_ring(ring),
            "features": {name: float(features[name]) for name in FEATURES},
            "winner": v2_truth.get(ring, {}).get("truth", "unknown"),
            "anchor_count": _anchor_count_for_ring(regime_v2, ring),
            "source": "regime_classifier_v2",
        }

    for item in cascade_v6["validation"]["rings"]:
        ring = item["ring"]
        rows[ring] = {
            "ring": ring,
            "range": item["range"],
            "features": {name: float(item["features"][name]) for name in FEATURES},
            "winner": item["winner"],
            "anchor_count": int(item["total_anchors"]),
            "source": "cascade_v6_spec",
        }

    rows["L"] = {
        "ring": "L",
        "range": ring_l["range"],
        "features": {name: float(ring_l["ring_l_features"][name]) for name in FEATURES},
        "winner": ring_l["results"]["winner"],
        "anchor_count": int(ring_l["results"]["total_anchors"]),
        "source": "ring_l_cascade_v5",
    }

    return [rows[ring] for ring in RING_ORDER]


def _range_for_ring(ring: str) -> str:
    index = ord(ring) - ord("A")
    start = 100 + index * 50
    end = start + 50
    return f"{start}M-{end}M"


def _anchor_count_for_ring(regime_v2: dict[str, Any], ring: str) -> int | None:
    for item in regime_v2.get("range_features", {}):
        if item == ring:
            break
    target_lock = REPO_ROOT / "artifacts" / "prime_target_lock" / "target_lock_latest.json"
    if target_lock.exists():
        data = load_json(target_lock)
        for row in data.get("ranges", []):
            if row.get("range") == ring:
                return int(row.get("known_anchor_count", 0))
    return None


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def stdev(values: list[float]) -> float:
    mu = mean(values)
    return math.sqrt(sum((value - mu) ** 2 for value in values) / max(1, len(values) - 1))


def standardize(rows: list[dict[str, Any]]) -> tuple[list[list[float]], dict[str, dict[str, float]]]:
    stats: dict[str, dict[str, float]] = {}
    for feature in FEATURES:
        values = [row["features"][feature] for row in rows]
        sigma = stdev(values)
        stats[feature] = {"mean": mean(values), "std": sigma if sigma else 1.0}
    matrix = []
    for row in rows:
        matrix.append(
            [
                (row["features"][feature] - stats[feature]["mean"]) / stats[feature]["std"]
                for feature in FEATURES
            ]
        )
    return matrix, stats


def covariance(matrix: list[list[float]]) -> list[list[float]]:
    n = len(matrix)
    width = len(matrix[0])
    cov = [[0.0 for _ in range(width)] for _ in range(width)]
    for row in matrix:
        for i in range(width):
            for j in range(width):
                cov[i][j] += row[i] * row[j]
    denom = max(1, n - 1)
    return [[value / denom for value in line] for line in cov]


def mat_vec(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [sum(row[i] * vector[i] for i in range(len(vector))) for row in matrix]


def dot(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def norm(vector: list[float]) -> float:
    return math.sqrt(dot(vector, vector))


def power_component(matrix: list[list[float]], iterations: int = 128) -> tuple[float, list[float]]:
    width = len(matrix)
    vector = [1.0 / math.sqrt(width) for _ in range(width)]
    for _ in range(iterations):
        nxt = mat_vec(matrix, vector)
        length = norm(nxt)
        if length == 0.0:
            break
        vector = [value / length for value in nxt]
    eigenvalue = dot(vector, mat_vec(matrix, vector))
    return eigenvalue, vector


def deflate(matrix: list[list[float]], eigenvalue: float, vector: list[float]) -> list[list[float]]:
    width = len(vector)
    return [
        [matrix[i][j] - eigenvalue * vector[i] * vector[j] for j in range(width)]
        for i in range(width)
    ]


def orient_components(
    components: list[list[float]],
    scores: list[list[float]],
    rows: list[dict[str, Any]],
) -> tuple[list[list[float]], list[list[float]]]:
    ordinal = list(range(len(rows)))
    for component_index in range(len(components)):
        component_scores = [score[component_index] for score in scores]
        corr = _corr(component_scores, ordinal)
        if component_index == 0 and corr < 0:
            components[component_index] = [-value for value in components[component_index]]
            for score in scores:
                score[component_index] *= -1
    return components, scores


def _corr(left: list[float], right: list[float]) -> float:
    l_mu = mean(left)
    r_mu = mean(right)
    numerator = sum((a - l_mu) * (b - r_mu) for a, b in zip(left, right))
    denom = math.sqrt(sum((a - l_mu) ** 2 for a in left) * sum((b - r_mu) ** 2 for b in right))
    return numerator / denom if denom else 0.0


def pca2(matrix: list[list[float]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    cov = covariance(matrix)
    eig1, pc1 = power_component(cov)
    cov2 = deflate(cov, eig1, pc1)
    eig2, pc2 = power_component(cov2)
    components = [pc1, pc2]
    scores = [[dot(row, pc1), dot(row, pc2)] for row in matrix]
    components, scores = orient_components(components, scores, rows)
    total_var = sum(cov[i][i] for i in range(len(cov)))
    return {
        "components": components,
        "scores": scores,
        "eigenvalues": [eig1, eig2],
        "explained_variance": [eig1 / total_var if total_var else 0.0, eig2 / total_var if total_var else 0.0],
    }


def aitken_limit(x0: float, x1: float, x2: float) -> float | None:
    denom = x2 - 2 * x1 + x0
    if abs(denom) < 1e-9:
        return None
    return x0 - ((x1 - x0) ** 2 / denom)


def linear_next(values: list[float], start_index: int = 0) -> float:
    xs = list(range(start_index, start_index + len(values)))
    x_mu = mean([float(x) for x in xs])
    y_mu = mean(values)
    denom = sum((x - x_mu) ** 2 for x in xs)
    slope = sum((x - x_mu) * (y - y_mu) for x, y in zip(xs, values)) / denom if denom else 0.0
    intercept = y_mu - slope * x_mu
    return intercept + slope * (start_index + len(values))


def project_ring_m(rows: list[dict[str, Any]], stats: dict[str, dict[str, float]], pca: dict[str, Any]) -> dict[str, Any]:
    by_ring = {row["ring"]: row for row in rows}
    j = by_ring["J"]["features"]
    k = by_ring["K"]["features"]
    l = by_ring["L"]["features"]

    mean_limit = aitken_limit(j["frz_mean"], k["frz_mean"], l["frz_mean"])
    if mean_limit is None or mean_limit < l["frz_mean"]:
        mean_forecast = l["frz_mean"] + 0.5 * (l["frz_mean"] - k["frz_mean"])
        mean_note = "last-step damped"
    else:
        mean_forecast = l["frz_mean"] + 0.75 * (mean_limit - l["frz_mean"])
        mean_note = "Aitken J/K/L damped toward limit"

    forecast = {
        "frz_mean": mean_forecast,
        "frz_std": linear_next([j["frz_std"], k["frz_std"], l["frz_std"]], start_index=9),
        "frz_skew": linear_next([j["frz_skew"], k["frz_skew"], l["frz_skew"]], start_index=9),
        "frz_kurt": min(
            linear_next([j["frz_kurt"], k["frz_kurt"], l["frz_kurt"]], start_index=9),
            l["frz_kurt"] + 0.5,
        ),
        "cen_std": mean([j["cen_std"], k["cen_std"], l["cen_std"]]),
    }
    standardized = [
        (forecast[feature] - stats[feature]["mean"]) / stats[feature]["std"]
        for feature in FEATURES
    ]
    pc_scores = [dot(standardized, pca["components"][0]), dot(standardized, pca["components"][1])]
    l_scores = pca["scores"][-1]
    return {
        "ring": "M",
        "range": "700M-750M",
        "forecast_features": {key: round(value, 6) for key, value in forecast.items()},
        "forecast_method": {"frz_mean": mean_note, "frz_mean_aitken_limit": round(mean_limit, 6) if mean_limit else None},
        "v6_regime": predict_v6(forecast),
        "pc_scores": [round(value, 6) for value in pc_scores],
        "delta_from_l_pc": [round(pc_scores[i] - l_scores[i], 6) for i in range(2)],
        "threshold_margins": {
            "frz_mean_minus_0.45": round(forecast["frz_mean"] - V6_FROZEN_MEAN_THRESHOLD, 6),
            "frz_skew_minus_1.0": round(forecast["frz_skew"] - V6_FROZEN_SKEW_THRESHOLD, 6),
            "cen_std_minus_0.97974": round(forecast["cen_std"] - V6_CEN_STD_THRESHOLD, 6),
        },
    }


def build_report() -> dict[str, Any]:
    rows = collect_ring_features()
    matrix, stats = standardize(rows)
    pca = pca2(matrix, rows)
    projection_m = project_ring_m(rows, stats, pca)

    embedded_rows = []
    for row, z_values, scores in zip(rows, matrix, pca["scores"]):
        features = row["features"]
        embedded_rows.append(
            {
                "ring": row["ring"],
                "range": row["range"],
                "winner": row["winner"],
                "v6_regime": predict_v6(features),
                "anchor_count": row["anchor_count"],
                "features": {key: round(features[key], 6) for key in FEATURES},
                "z": {key: round(value, 6) for key, value in zip(FEATURES, z_values)},
                "pc1": round(scores[0], 6),
                "pc2": round(scores[1], 6),
                "source": row["source"],
            }
        )

    pc_loadings = []
    for idx, component in enumerate(pca["components"], start=1):
        pc_loadings.append(
            {
                "pc": f"PC{idx}",
                "explained_variance": round(pca["explained_variance"][idx - 1], 6),
                "loadings": {feature: round(value, 6) for feature, value in zip(FEATURES, component)},
            }
        )

    return {
        "schema": "prime_fog_manifold_navigator_v1",
        "date": datetime.now().isoformat(timespec="seconds"),
        "claim_boundary": "Feature-only A-L embedding. Ring M cache and anchors are not opened.",
        "features": list(FEATURES),
        "feature_stats": {feature: {k: round(v, 6) for k, v in item.items()} for feature, item in stats.items()},
        "pc_loadings": pc_loadings,
        "rings": embedded_rows,
        "ring_m_projection": projection_m,
        "readout": {
            "primary_axis": "PC1 is the concentration axis: frz_mean/skew/kurt rise while frz_std falls.",
            "ring_m_direction": "Projected M remains beyond L on the concentration axis and stays in frozen_dominant.",
            "controller": "cascade_v6 -> frozen_dominant -> raw frozen gate",
            "watch": "The next real boundary is not kurt alternation; it is whether skew drops below 1.0 or the raw frozen margin collapses.",
        },
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# Prime Fog Manifold Navigator",
        "",
        report["claim_boundary"],
        "",
        "## Axes",
        "",
        "| PC | Explained variance | frz_mean | frz_std | frz_skew | frz_kurt | cen_std |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["pc_loadings"]:
        load = row["loadings"]
        lines.append(
            "| {pc} | {ev:.1%} | {frz_mean:+.3f} | {frz_std:+.3f} | {frz_skew:+.3f} | {frz_kurt:+.3f} | {cen_std:+.3f} |".format(
                pc=row["pc"],
                ev=row["explained_variance"],
                **load,
            )
        )

    lines.extend(
        [
            "",
            "## Embedded Rings",
            "",
            "| Ring | Range | Winner | v6 regime | frz_mean | frz_std | frz_skew | frz_kurt | PC1 | PC2 |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in report["rings"]:
        feats = row["features"]
        lines.append(
            "| {ring} | {range} | {winner} | {v6_regime} | {frz_mean:.4f} | {frz_std:.4f} | {frz_skew:.4f} | {frz_kurt:.4f} | {pc1:.3f} | {pc2:.3f} |".format(
                ring=row["ring"],
                range=row["range"],
                winner=row["winner"],
                v6_regime=row["v6_regime"],
                pc1=row["pc1"],
                pc2=row["pc2"],
                **feats,
            )
        )

    projection = report["ring_m_projection"]
    feats = projection["forecast_features"]
    margins = projection["threshold_margins"]
    lines.extend(
        [
            "",
            "## Ring M Direction",
            "",
            "| Feature | Projection |",
            "| --- | ---: |",
        ]
    )
    for feature in FEATURES:
        lines.append(f"| {feature} | {feats[feature]:.4f} |")
    lines.extend(
        [
            "",
            f"Projected regime: `{projection['v6_regime']}`.",
            "",
            "| Margin | Value |",
            "| --- | ---: |",
            f"| frz_mean - 0.45 | {margins['frz_mean_minus_0.45']:+.4f} |",
            f"| frz_skew - 1.0 | {margins['frz_skew_minus_1.0']:+.4f} |",
            f"| cen_std - 0.97974 | {margins['cen_std_minus_0.97974']:+.4f} |",
            "",
            "Readout: M remains on the frozen-concentration path. The clean controller is still raw frozen unless the feature-first pass shows skew falling back below 1.0.",
            "",
            "## Artifacts",
            "",
            "- `artifacts/prime_fog_manifold_navigator/latest_report.json`",
            "- `artifacts/prime_fog_manifold_navigator/RESULTS.md`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    report = build_report()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "latest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, OUT_DIR / "RESULTS.md")
    print(json.dumps({
        "rings": len(report["rings"]),
        "pc1_explained": report["pc_loadings"][0]["explained_variance"],
        "pc2_explained": report["pc_loadings"][1]["explained_variance"],
        "ring_m_regime": report["ring_m_projection"]["v6_regime"],
        "ring_m_projection": report["ring_m_projection"]["forecast_features"],
        "out_dir": str(OUT_DIR.relative_to(REPO_ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()
