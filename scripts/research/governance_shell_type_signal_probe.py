"""Governance shell type-signal probe.

This turns the user's "winding shell" idea into a falsifiable research harness:

    height / radial coordination = severity
    compass winding              = regional risk type
    surface density              = local SCBE coherence proxy

The important test is not whether a class-colored shell is pretty. That would be
tautological. The test is whether local prompt features can recover typed risk
families better than severity-only coordinates and better than a label-shuffle
null. If they cannot, the winding is decorative. If they can, the winding carries
independent information.

This is intentionally Zone-4/research-only. It consumes the adversarial harness
as a read-side signal and does not change runtime governance.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
import statistics
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.adversarial.attack_corpus import get_full_corpus
from tests.adversarial.scbe_harness import SCBEDetectionGate

DEFAULT_OUT_DIR = REPO_ROOT / "artifacts" / "governance_shell_type_signal"

FLAG_NAMES = (
    "spin_drift",
    "tongue_imbalance",
    "cost_exceeded",
    "boundary_violation",
    "adversarial_lexical",
    "cross_lingual_override",
    "dispersal_shift",
    "detected",
)

ATOMIC_FEATURE_NAMES = (
    "log_chars",
    "log_words",
    "unique_ratio",
    "digit_ratio",
    "uppercase_ratio",
    "punct_ratio",
    "non_ascii_ratio",
    "url_marker",
    "secret_marker",
    "command_marker",
    "override_marker",
    "exfil_marker",
    "encoding_marker",
    "tool_marker",
    "policy_marker",
    "destructive_marker",
)


@dataclass(frozen=True)
class GovernanceShellRecord:
    attack_id: str
    attack_class: str
    prompt: str
    is_attack: bool
    severity_raw: float
    severity_norm: float
    coherence_raw: float
    coherence_norm: float
    compass_angle_rad: float
    compass_x: float
    compass_y: float
    shell_x: float
    shell_y: float
    shell_z: float
    magnetic_alignment: float
    spin_magnitude: int
    dispersal_cost: float
    harmonic_cost: float
    dominant_tongue: str
    tongue_coords: tuple[float, ...]
    atomic_embedding: tuple[float, ...]
    flags: tuple[float, ...]
    detection_signals: tuple[str, ...]


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def atomic_embedding(text: str) -> tuple[float, ...]:
    """Small deterministic atom vector for prompt text.

    This is not a model embedding. It is a stable lexical atom surface that gives
    the null test a cheap, inspectable feature source.
    """
    words = re.findall(r"[A-Za-z0-9_]+", text)
    lowered = text.lower()
    chars = max(len(text), 1)
    word_count = max(len(words), 1)
    unique_ratio = len({word.lower() for word in words}) / word_count
    digit_ratio = sum(ch.isdigit() for ch in text) / chars
    uppercase_ratio = sum(ch.isupper() for ch in text) / chars
    punct_ratio = sum(ch in ".,;:!?-_/()[]{}@#$%^&*`'\"" for ch in text) / chars
    non_ascii_ratio = sum(ord(ch) > 127 for ch in text) / chars

    def has_any(patterns: Iterable[str]) -> float:
        return 1.0 if any(re.search(pattern, lowered) for pattern in patterns) else 0.0

    return (
        clamp01(math.log1p(chars) / math.log1p(2000.0)),
        clamp01(math.log1p(len(words)) / math.log1p(300.0)),
        clamp01(unique_ratio),
        clamp01(digit_ratio * 10.0),
        clamp01(uppercase_ratio * 8.0),
        clamp01(punct_ratio * 8.0),
        clamp01(non_ascii_ratio * 10.0),
        has_any((r"https?://", r"\bwww\.", r"\.onion\b")),
        has_any(
            (
                r"\bapi[_ -]?key\b",
                r"\btoken\b",
                r"\bpassword\b",
                r"\bsecret\b",
                r"sk-[a-z0-9]",
            )
        ),
        has_any(
            (r"\bcurl\b", r"\bpowershell\b", r"\bbash\b", r"\bexec\b", r"\bsystem\(")
        ),
        has_any(
            (
                r"\bignore\b",
                r"\boverride\b",
                r"\bdeveloper\b",
                r"\bsystem prompt\b",
                r"\bjailbreak\b",
            )
        ),
        has_any((r"\bexfil", r"\bleak\b", r"\bextract\b", r"\bprint\b", r"\bdump\b")),
        has_any(
            (r"\bbase64\b", r"\brot13\b", r"\bhex\b", r"\bdecode\b", r"\bbackwards\b")
        ),
        has_any(
            (
                r"\btool\b",
                r"\bfunction\b",
                r"\bterminal\b",
                r"\bshell\b",
                r"\bbrowser\b",
            )
        ),
        has_any(
            (
                r"\bpolicy\b",
                r"\brules?\b",
                r"\bguardrail\b",
                r"\bgovernance\b",
                r"\bdeny\b",
            )
        ),
        has_any(
            (r"\bdelete\b", r"\bdestroy\b", r"\bwipe\b", r"\bmalware\b", r"\bransom\b")
        ),
    )


def _zscore_columns(rows: Sequence[Sequence[float]]) -> list[list[float]]:
    if not rows:
        return []
    width = len(rows[0])
    means = [statistics.fmean(row[idx] for row in rows) for idx in range(width)]
    stds: list[float] = []
    for idx in range(width):
        variance = statistics.fmean((row[idx] - means[idx]) ** 2 for row in rows)
        stds.append(math.sqrt(variance) or 1.0)
    return [
        [(row[idx] - means[idx]) / stds[idx] for idx in range(width)] for row in rows
    ]


def stratified_split(
    labels: Sequence[str], seed: int = 17, train_fraction: float = 0.7
) -> tuple[list[int], list[int]]:
    rng = random.Random(seed)
    by_label: dict[str, list[int]] = defaultdict(list)
    for idx, label in enumerate(labels):
        by_label[label].append(idx)

    train: list[int] = []
    test: list[int] = []
    for indices in by_label.values():
        shuffled = list(indices)
        rng.shuffle(shuffled)
        if len(shuffled) <= 1:
            train.extend(shuffled)
            continue
        cut = max(1, min(len(shuffled) - 1, int(round(len(shuffled) * train_fraction))))
        train.extend(shuffled[:cut])
        test.extend(shuffled[cut:])
    return sorted(train), sorted(test)


def nearest_centroid_accuracy(
    features: Sequence[Sequence[float]],
    labels: Sequence[str],
    seed: int = 17,
    shuffle_train_labels: bool = False,
) -> float:
    if len(features) != len(labels):
        raise ValueError("features and labels must have the same length")
    train_idx, test_idx = stratified_split(labels, seed=seed)
    if not test_idx:
        return 0.0

    scaled = _zscore_columns(features)
    train_labels = [labels[idx] for idx in train_idx]
    if shuffle_train_labels:
        rng = random.Random(seed + 1009)
        rng.shuffle(train_labels)

    sums: dict[str, list[float]] = {}
    counts: dict[str, int] = {}
    for idx, label in zip(train_idx, train_labels):
        row = scaled[idx]
        if label not in sums:
            sums[label] = [0.0] * len(row)
            counts[label] = 0
        for col, value in enumerate(row):
            sums[label][col] += value
        counts[label] += 1

    centroids = {
        label: [value / counts[label] for value in values]
        for label, values in sums.items()
        if counts[label] > 0
    }
    if not centroids:
        return 0.0

    correct = 0
    for idx in test_idx:
        row = scaled[idx]
        pred = min(
            centroids,
            key=lambda label: sum(
                (row[col] - centroids[label][col]) ** 2 for col in range(len(row))
            ),
        )
        correct += int(pred == labels[idx])
    return correct / len(test_idx)


def null_p95(
    features: Sequence[Sequence[float]],
    labels: Sequence[str],
    trials: int = 200,
    seed: int = 17,
) -> float:
    scores = [
        nearest_centroid_accuracy(
            features, labels, seed=seed + trial, shuffle_train_labels=True
        )
        for trial in range(trials)
    ]
    return sorted(scores)[int(math.ceil(0.95 * len(scores))) - 1]


def _normalize_shell_records(
    raw_records: list[dict[str, object]], class_order: Sequence[str]
) -> list[GovernanceShellRecord]:
    max_cost = max(float(record["harmonic_cost"]) for record in raw_records) or 1.0
    max_coherence = max(float(record["coherence_raw"]) for record in raw_records) or 1.0
    angle_by_class = {
        attack_class: 2.0 * math.pi * idx / max(len(class_order), 1)
        for idx, attack_class in enumerate(class_order)
    }

    normalized: list[GovernanceShellRecord] = []
    for record in raw_records:
        attack_class = str(record["attack_class"])
        severity_raw = float(record["harmonic_cost"])
        severity_norm = clamp01(math.log1p(severity_raw) / math.log1p(max_cost))
        coherence_raw = float(record["coherence_raw"])
        coherence_norm = clamp01(coherence_raw / max_coherence)
        angle = angle_by_class[attack_class]
        compass_x = math.cos(angle)
        compass_y = math.sin(angle)
        tongue_coords = tuple(float(value) for value in record["tongue_coords"])  # type: ignore[arg-type]
        if len(tongue_coords) >= 2:
            local_norm = math.hypot(tongue_coords[0], tongue_coords[1]) or 1.0
            local_x = tongue_coords[0] / local_norm
            local_y = tongue_coords[1] / local_norm
        else:
            local_x = 0.0
            local_y = 0.0
        magnetic_alignment = local_x * compass_x + local_y * compass_y
        radius = 1.0 + 0.4 * severity_norm + 0.25 * coherence_norm

        normalized.append(
            GovernanceShellRecord(
                attack_id=str(record["attack_id"]),
                attack_class=attack_class,
                prompt=str(record["prompt"]),
                is_attack=bool(record["is_attack"]),
                severity_raw=severity_raw,
                severity_norm=severity_norm,
                coherence_raw=coherence_raw,
                coherence_norm=coherence_norm,
                compass_angle_rad=angle,
                compass_x=compass_x,
                compass_y=compass_y,
                shell_x=radius * compass_x,
                shell_y=radius * compass_y,
                shell_z=severity_norm,
                magnetic_alignment=magnetic_alignment,
                spin_magnitude=int(record["spin_magnitude"]),
                dispersal_cost=float(record["dispersal_cost"]),
                harmonic_cost=float(record["harmonic_cost"]),
                dominant_tongue=str(record["dominant_tongue"]),
                tongue_coords=tongue_coords,
                atomic_embedding=tuple(float(value) for value in record["atomic_embedding"]),  # type: ignore[arg-type]
                flags=tuple(float(value) for value in record["flags"]),  # type: ignore[arg-type]
                detection_signals=tuple(str(value) for value in record["detection_signals"]),  # type: ignore[arg-type]
            )
        )
    return normalized


def build_shell_records(
    include_baseline: bool = True, max_attacks: int | None = None
) -> list[GovernanceShellRecord]:
    corpus = get_full_corpus()
    gate = SCBEDetectionGate()
    gate.calibrate([item["prompt"] for item in corpus["baseline"]])

    attacks = corpus["attacks"][:max_attacks] if max_attacks else corpus["attacks"]
    rows: list[tuple[dict[str, str], bool]] = [(attack, True) for attack in attacks]
    if include_baseline:
        rows.extend((item, False) for item in corpus["baseline"])

    raw_records: list[dict[str, object]] = []
    for item, is_attack in rows:
        gate.reset_session()
        result = gate.process(
            prompt=item["prompt"],
            attack_id=item.get("id", ""),
            attack_class=item.get("class", "unknown"),
        )
        flags = tuple(float(getattr(result, name)) for name in FLAG_NAMES)
        atom = atomic_embedding(item["prompt"])
        coherence_raw = (
            len(result.detection_signals)
            + 0.35 * result.spin_magnitude
            + 0.08 * result.dispersal_cost
            + 0.4 * float(result.detected)
        )
        raw_records.append(
            {
                "attack_id": result.attack_id,
                "attack_class": result.attack_class,
                "prompt": item["prompt"],
                "is_attack": is_attack,
                "coherence_raw": coherence_raw,
                "spin_magnitude": result.spin_magnitude,
                "dispersal_cost": result.dispersal_cost,
                "harmonic_cost": result.harmonic_cost,
                "dominant_tongue": result.dominant_tongue,
                "tongue_coords": tuple(result.tongue_coords),
                "atomic_embedding": atom,
                "flags": flags,
                "detection_signals": tuple(result.detection_signals),
            }
        )

    class_order = sorted({str(record["attack_class"]) for record in raw_records})
    return _normalize_shell_records(raw_records, class_order)


def severity_features(record: GovernanceShellRecord) -> tuple[float, ...]:
    return (record.severity_norm,)


def radial_features(record: GovernanceShellRecord) -> tuple[float, ...]:
    return (record.severity_norm, record.coherence_norm)


def regional_magnetic_features(record: GovernanceShellRecord) -> tuple[float, ...]:
    return (
        record.severity_norm,
        record.coherence_norm,
        record.spin_magnitude / 6.0,
        clamp01(record.dispersal_cost / 20.0),
        *record.tongue_coords,
        *record.atomic_embedding,
        *record.flags,
    )


def attack_records_only(
    records: Sequence[GovernanceShellRecord],
) -> list[GovernanceShellRecord]:
    return [
        record
        for record in records
        if record.is_attack and record.attack_class != "baseline_clean"
    ]


def run_probe(
    max_attacks: int | None = None,
    seed: int = 17,
    null_trials: int = 200,
    render: bool = False,
    out_dir: Path | None = None,
) -> dict[str, object]:
    records = build_shell_records(include_baseline=True, max_attacks=max_attacks)
    attacks = attack_records_only(records)
    labels = [record.attack_class for record in attacks]

    severity_rows = [severity_features(record) for record in attacks]
    radial_rows = [radial_features(record) for record in attacks]
    magnetic_rows = [regional_magnetic_features(record) for record in attacks]

    severity_acc = nearest_centroid_accuracy(severity_rows, labels, seed=seed)
    radial_acc = nearest_centroid_accuracy(radial_rows, labels, seed=seed)
    magnetic_acc = nearest_centroid_accuracy(magnetic_rows, labels, seed=seed)
    magnetic_null95 = null_p95(magnetic_rows, labels, trials=null_trials, seed=seed)
    radial_null95 = null_p95(radial_rows, labels, trials=null_trials, seed=seed)

    load_bearing = magnetic_acc > max(severity_acc, radial_acc, magnetic_null95) + 0.05
    decorative_radial = radial_acc <= max(severity_acc, radial_null95) + 0.05
    verdict = "TYPE_WINDING_LOAD_BEARING" if load_bearing else "TYPE_WINDING_UNPROVEN"

    per_class: dict[str, dict[str, float | int]] = {}
    for attack_class in sorted(set(labels)):
        members = [record for record in attacks if record.attack_class == attack_class]
        per_class[attack_class] = {
            "count": len(members),
            "mean_severity": statistics.fmean(
                record.severity_norm for record in members
            ),
            "mean_coherence": statistics.fmean(
                record.coherence_norm for record in members
            ),
            "mean_magnetic_alignment": statistics.fmean(
                record.magnetic_alignment for record in members
            ),
        }

    summary: dict[str, object] = {
        "n_records": len(records),
        "n_attack_records": len(attacks),
        "n_classes": len(set(labels)),
        "feature_names": {
            "atomic": ATOMIC_FEATURE_NAMES,
            "flags": FLAG_NAMES,
        },
        "metrics": {
            "severity_only_accuracy": severity_acc,
            "radial_shell_accuracy": radial_acc,
            "regional_magnetic_accuracy": magnetic_acc,
            "radial_null95": radial_null95,
            "regional_magnetic_null95": magnetic_null95,
            "regional_minus_severity": magnetic_acc - severity_acc,
            "regional_minus_radial": magnetic_acc - radial_acc,
            "decorative_radial": decorative_radial,
        },
        "per_class": per_class,
        "decision_record": {
            "promotion": "QUARANTINE_RESEARCH_ONLY",
            "verdict": verdict,
            "load_bearing": load_bearing,
            "claim_boundary": (
                "Shows whether typed regional prompt features carry class signal beyond severity. "
                "It is not a production governance proof and does not alter runtime policy."
            ),
        },
    }

    if out_dir is not None:
        write_artifacts(records, summary, out_dir, render=render)

    return summary


def write_artifacts(
    records: Sequence[GovernanceShellRecord],
    summary: dict[str, object],
    out_dir: Path,
    render: bool = False,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )

    with (out_dir / "shell_records.csv").open(
        "w", newline="", encoding="utf-8"
    ) as handle:
        fieldnames = [
            "attack_id",
            "attack_class",
            "is_attack",
            "severity_norm",
            "coherence_norm",
            "compass_angle_rad",
            "shell_x",
            "shell_y",
            "shell_z",
            "magnetic_alignment",
            "spin_magnitude",
            "dispersal_cost",
            "harmonic_cost",
            "dominant_tongue",
            "detection_signals",
            "prompt",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            row = asdict(record)
            row["detection_signals"] = "|".join(record.detection_signals)
            writer.writerow({name: row[name] for name in fieldnames})

    if render:
        render_shell(records, out_dir / "governance_shell.png")


def render_shell(records: Sequence[GovernanceShellRecord], out_path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return

    classes = sorted({record.attack_class for record in records})
    color_by_class = {attack_class: idx for idx, attack_class in enumerate(classes)}

    fig = plt.figure(figsize=(11, 8), facecolor="#0b0d10")
    ax = fig.add_subplot(111, projection="3d")
    ax.set_facecolor("#0b0d10")

    xs = [record.shell_x for record in records]
    ys = [record.shell_y for record in records]
    zs = [record.shell_z for record in records]
    colors = [color_by_class[record.attack_class] for record in records]
    sizes = [40 + 110 * record.coherence_norm for record in records]
    ax.scatter(
        xs,
        ys,
        zs,
        c=colors,
        s=sizes,
        cmap="tab10",
        alpha=0.86,
        edgecolors="white",
        linewidths=0.25,
    )

    for record in records:
        ax.plot(
            [0.0, record.shell_x],
            [0.0, record.shell_y],
            [record.shell_z, record.shell_z],
            color="#2f3a4a",
            alpha=0.25,
            linewidth=0.6,
        )

    ax.set_title(
        "Governance Shell: Severity x Regional Risk Bearing", color="white", pad=18
    )
    ax.set_xlabel("Compass X", color="white")
    ax.set_ylabel("Compass Y", color="white")
    ax.set_zlabel("Severity", color="white")
    ax.tick_params(colors="white")
    ax.grid(color="#222733", alpha=0.6)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-attacks", type=int, default=None)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--null-trials", type=int, default=200)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--render", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_probe(
        max_attacks=args.max_attacks,
        seed=args.seed,
        null_trials=args.null_trials,
        render=args.render,
        out_dir=args.out_dir,
    )
    print(json.dumps(summary["metrics"], indent=2, sort_keys=True))
    print(json.dumps(summary["decision_record"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
