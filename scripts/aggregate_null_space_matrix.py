"""Cross-model cognitive null-space matrix aggregator.

Scans artifacts/ for biblical null-space eval results and generates
a comparative matrix showing which models have which blind spots.

Usage:
    python scripts/aggregate_null_space_matrix.py
"""

import os
import json
import glob


def generate_null_space_matrix(artifact_dir="artifacts"):
    files = glob.glob(os.path.join(artifact_dir, "biblical_null_space_*.json"))

    if not files:
        print(f"[-] No evaluation artifacts found in '{artifact_dir}/'.")
        return

    summary_data = []
    tongues = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']

    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            analysis = data.get("analysis", {})
            scores_list = data.get("scores", [])
            model_name = f"{data.get('provider', '?')} / {data.get('model', '?')}"

            total_score = analysis.get("total_score", 0)
            max_score = analysis.get("max_score", 60)
            percent = analysis.get("percentage", 0)
            tongue_means = analysis.get("tongue_means", {})

            if tongue_means:
                deepest_tongue = min(tongue_means, key=tongue_means.get)
                deepest_score = tongue_means[deepest_tongue]
            else:
                deepest_tongue = "?"
                deepest_score = 0

            null_tongues = [t for t, v in tongue_means.items() if v < 1.0]

            summary_data.append({
                "model": model_name,
                "score": f"{total_score}/{max_score}",
                "percent": percent,
                "deepest_null": f"{deepest_tongue} ({deepest_score:.2f})",
                "null_count": len(null_tongues),
                "tongue_means": tongue_means,
            })

        except Exception as e:
            print(f"[!] Error parsing {file}: {e}")

    summary_data.sort(key=lambda x: x["percent"], reverse=True)

    print("\n" + "=" * 80)
    print(" SCBE-AETHERMOORE CROSS-MODEL COGNITIVE NULL-SPACE MATRIX")
    print("=" * 80)
    print(f"| {'Model':<35} | {'Score':<7} | {'Pct':>5} | {'Nulls':>5} | {'Deepest Null':<18} |")
    print("-" * 80)

    for row in summary_data:
        print(f"| {row['model']:<35} | {row['score']:<7} | {row['percent']:>4.1f}% | {row['null_count']:>5} | {row['deepest_null']:<18} |")

    print("=" * 80)
    print("  Null-space = tongue mean < 1.0/3. All models tested against 20 covenantal probes.")
    print("  Tongues: KO=Genesis Control, AV=Invitation, RU=Witness,")
    print("           CA=Sabbath, UM=Sanctuary, DR=Covenant")


if __name__ == "__main__":
    generate_null_space_matrix(artifact_dir="artifacts")
