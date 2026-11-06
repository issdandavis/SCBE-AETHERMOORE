"""Generate the bounded CBD mechanics chart and machine-readable receipts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import random

import matplotlib.pyplot as plt
import numpy as np

import condensed_boundary_density as cbd

SEEDS = (11, 23, 47)


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".pending")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(seed: int, condition: str):
    rng = random.Random(seed)
    cells = []
    for prefix, concept, base in (("a", "rose", 0.0), ("b", "thorn", 1.4)):
        for dimension, layer in enumerate(("token", "context", "policy")):
            phase = base + rng.uniform(-0.07, 0.07)
            if condition == "phase_shuffled" and prefix == "a":
                phase = 2 * math.pi * dimension / 3 + rng.uniform(-0.07, 0.07)
            cells.append(
                cbd.BoundaryCell(
                    cell_id=f"{prefix}{dimension}",
                    dimension=dimension,
                    layer=layer,
                    seed_id=concept,
                    mass=(1.0, 0.9, 1.1)[dimension],
                    amplitude=1.0,
                    phase=phase,
                    frequency=(0.7, 0.9, 1.1)[dimension],
                    trits=(1, 0, -1) if prefix == "a" else (-1, 0, 1),
                )
            )
    links = [
        cbd.TransportLink("a0", "a1", 1.0, kind="sibling"),
        cbd.TransportLink("a1", "a2", 1.0, kind="sibling"),
        cbd.TransportLink("a0", "a2", 0.8, kind="sibling"),
        cbd.TransportLink("b0", "b1", 1.0, kind="sibling"),
        cbd.TransportLink("b1", "b2", 1.0, kind="sibling"),
        cbd.TransportLink("b0", "b2", 0.8, kind="sibling"),
        cbd.TransportLink("a2", "b2", 0.08, kind="context"),
    ]
    if condition == "binding_shuffled":
        links[0] = cbd.TransportLink("a0", "b1", 1.0, kind="sibling")
        links[3] = cbd.TransportLink("b0", "a1", 1.0, kind="sibling")
    return cells, links


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("cannot write an empty table")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build(output: Path) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=False)
    metric_rows: list[dict[str, object]] = []
    for condition in ("aligned", "phase_shuffled", "binding_shuffled"):
        for seed in SEEDS:
            cells, links = fixture(seed, condition)
            metrics = cbd.cluster_metrics(cells, links, ("a0", "a1", "a2"))
            metric_rows.append({"condition": condition, "seed": seed, **metrics})
    cells, links = fixture(SEEDS[0], "aligned")
    single = cbd.cluster_metrics(cells, links, ("a0",))
    for seed in SEEDS:
        metric_rows.append({"condition": "single_node", "seed": seed, **single})

    aligned_cells, aligned_links = fixture(SEEDS[0], "aligned")
    cluster_cells = aligned_cells[:3]
    cluster_links = aligned_links[:3]
    modes = cbd.normal_modes(cluster_cells, cluster_links)
    heavy_cells = [
        cbd.BoundaryCell(
            cell.cell_id,
            cell.dimension,
            cell.layer,
            cell.seed_id,
            mass=4 * cell.mass,
            amplitude=cell.amplitude,
            phase=cell.phase,
            frequency=cell.frequency,
            trits=cell.trits,
        )
        for cell in cluster_cells
    ]
    heavy_modes = cbd.normal_modes(heavy_cells, cluster_links)
    mode_rows = [
        {
            "mode": index,
            "base_frequency": float(base),
            "four_x_mass_frequency": float(heavy),
        }
        for index, (base, heavy) in enumerate(
            zip(modes["frequencies"], heavy_modes["frequencies"], strict=True)
        )
    ]

    coarse = cbd.coarsen_partition(
        aligned_cells,
        aligned_links,
        (("a0", "a1", "a2"), ("b0", "b1", "b2")),
    )
    first_lift = np.asarray(
        [
            [1, 0, 0, 0],
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]
    )
    second_lift = np.asarray([[1, 0], [1, 0], [0, 1], [0, 1]])
    hierarchy = cbd.coarsen_operator_hierarchy(
        coarse["fine_laplacian"],
        coarse["fine_mass"],
        (first_lift, second_lift),
    )
    meta_state = np.asarray([0.4 + 0.2j, -0.3 + 0.1j])
    fine_state = hierarchy["total_lift"] @ meta_state
    fine_energy = np.vdot(fine_state, coarse["fine_laplacian"] @ fine_state).real
    meta_energy = np.vdot(meta_state, hierarchy["coarse_laplacian"] @ meta_state).real
    recursive_energy_residual = float(fine_energy - meta_energy)

    base_rule = hashlib.sha256(b"cbd-shared-cell-rule-v1").hexdigest()
    contracts = [
        cbd.RepeatedCellContract(
            f"{concept}{slot}",
            (concept_index, slot),
            concept,
            base_rule,
            16,
            8,
        )
        for concept_index, concept in enumerate(("rose", "thorn"))
        for slot in range(3)
    ]
    contracts.extend(
        cbd.RepeatedCellContract(
            concept,
            (concept_index,),
            concept,
            base_rule,
            16,
            8,
            generation=1,
            child_ids=tuple(f"{concept}{slot}" for slot in range(3)),
        )
        for concept_index, concept in enumerate(("rose", "thorn"))
    )
    contracts.append(
        cbd.RepeatedCellContract(
            "wafer",
            (0,),
            "root",
            base_rule,
            16,
            8,
            generation=2,
            child_ids=("rose", "thorn"),
        )
    )
    fabric = cbd.validate_repeated_fabric(contracts)
    atomic_text(
        output / "fabric_manifest.json",
        json.dumps(fabric, indent=2, sort_keys=True) + "\n",
    )
    readout = np.asarray([0.25, 0.35, 0.55, -0.15, 0.1, -0.2], dtype=complex)
    trace = cbd.step_with_trace(
        aligned_cells, aligned_links, readout, dt=0.03, diffusion=0.08
    )
    trace_rows = [row for row in trace["output_terms"] if row["kind"] == "cell"]

    write_csv(output / "cluster_metrics.csv", metric_rows)
    write_csv(output / "mode_frequencies.csv", mode_rows)
    write_csv(output / "trace_contributions.csv", trace_rows)

    figure, axes = plt.subplots(2, 2, figsize=(14, 10), constrained_layout=True)
    figure.suptitle(
        "Condensed Boundary Density — mechanics and audit lenses",
        fontsize=16,
        weight="bold",
    )
    conditions = ("aligned", "phase_shuffled", "binding_shuffled", "single_node")
    labels = (
        "aligned\npoly-node",
        "phase\nshuffled",
        "binding\nshuffled",
        "single\nnode",
    )
    colors = ("#1B7F5C", "#D98C10", "#B33A3A", "#6B7280")
    for position, (condition, label, color) in enumerate(
        zip(conditions, labels, colors, strict=True)
    ):
        values = [
            float(row["condensation_index"])
            for row in metric_rows
            if row["condition"] == condition
        ]
        axes[0, 0].scatter(
            [position] * len(values), values, color=color, s=55, zorder=3
        )
        axes[0, 0].bar(position, float(np.mean(values)), color=color, alpha=0.45)
    axes[0, 0].set_xticks(range(len(labels)), labels)
    axes[0, 0].set_ylim(-0.02, 0.75)
    axes[0, 0].set_ylabel("Condensation index [0, 1]")
    axes[0, 0].set_title(
        "A clump requires plurality, coherence, retention, and valid siblings"
    )
    axes[0, 0].grid(axis="y", alpha=0.25)

    x = np.arange(len(mode_rows))
    axes[0, 1].plot(
        x, [row["base_frequency"] for row in mode_rows], "o-", label="base mass"
    )
    axes[0, 1].plot(
        x, [row["four_x_mass_frequency"] for row in mode_rows], "s--", label="4× mass"
    )
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xlabel("Internal cluster mode")
    axes[0, 1].set_ylabel("Natural frequency")
    axes[0, 1].set_title("Trampoline law: 4× mass gives 1/2 frequency")
    axes[0, 1].legend(frameon=False)
    axes[0, 1].grid(alpha=0.25)

    heat = np.abs(coarse["coarse_laplacian"])
    image = axes[1, 0].imshow(heat, cmap="magma")
    axes[1, 0].set_xticks((0, 1), ("rose clump", "thorn clump"))
    axes[1, 0].set_yticks((0, 1), ("rose clump", "thorn clump"))
    axes[1, 0].set_title(
        "Galerkin coarse operator: clusters act as weighted meta-nodes"
    )
    for row in range(2):
        for column in range(2):
            axes[1, 0].text(
                column,
                row,
                f"{heat[row, column]:.2f}",
                ha="center",
                va="center",
                color="white",
            )
    figure.colorbar(
        image, ax=axes[1, 0], fraction=0.046, pad=0.04, label="|coarse Laplacian entry|"
    )

    contributions = [float(row["contribution"]) for row in trace_rows]
    axes[1, 1].bar(
        [row["cell_id"] for row in trace_rows],
        contributions,
        color=["#1B7F5C"] * 3 + ["#B33A3A"] * 3,
    )
    axes[1, 1].axhline(0, color="black", linewidth=0.8)
    axes[1, 1].set_ylabel("Exact readout contribution")
    axes[1, 1].set_title(
        f"Output ledger reconstructs y={trace['output']:.4f}; residual={trace['trace_residual']:.1e}"
    )
    axes[1, 1].grid(axis="y", alpha=0.25)

    chart = output / "condensed_boundary_density.png"
    figure.savefig(chart, dpi=180)
    plt.close(figure)

    report = f"""# Condensed Boundary Density mechanics result

Status: **MECHANICS_VALIDATED / MODEL_GAIN_UNTESTED**.

The prototype converts cells of every dimension into nodes, preserves boundary
orientation as connection phase, forms poly-nodal clumps by exact Galerkin
coarsening, solves mass-weighted natural modes, and reconstructs one linear
readout from a per-cell contribution ledger with residual
`{trace['trace_residual']:.3e}`.

Two recursive lifts reproduce the direct leaf-to-concept map with quadratic
energy residual `{recursive_energy_residual:.3e}`. A nine-cell Q1 architecture
manifest records six leaves, two concept meta-cells, one root cell, their shared
rule/interface, addresses, sectors, and child lineage. This verifies structure;
it is not functional self-reproduction.

Three deterministic matched seeds were evaluated under aligned, phase-shuffled,
binding-shuffled, and singleton conditions. These are synthetic mechanics
fixtures. They do not establish language, reasoning, security, or training gains.

The next real gate must attach the same operators to pinned neural activations
and compare against a parameter-matched graph layer, a no-intervention baseline,
a shuffled stable-concept binding, and component ablations over at least three
training seeds. Top traced cells must also beat random and magnitude-matched
cells in causal removal/injection tests.
"""
    atomic_text(output / "REPORT.md", report)
    artifacts = (
        "cluster_metrics.csv",
        "mode_frequencies.csv",
        "trace_contributions.csv",
        "fabric_manifest.json",
        "condensed_boundary_density.png",
        "REPORT.md",
    )
    result = {
        "schema": "scbe.condensed-boundary-density.mechanics.v1",
        "status": "MECHANICS_VALIDATED_MODEL_GAIN_UNTESTED",
        "seeds": list(SEEDS),
        "trace_residual": float(trace["trace_residual"]),
        "fine_cells": len(aligned_cells),
        "coarse_clusters": 2,
        "recursive_energy_residual": recursive_energy_residual,
        "fabric_manifest_sha256": fabric["manifest_sha256"],
        "fabric_cells": fabric["cell_count"],
        "fabric_generations": fabric["max_generation"] + 1,
        "source_sha256": sha256(
            Path(__file__).with_name("condensed_boundary_density.py")
        ),
        "artifacts": {name: sha256(output / name) for name in artifacts},
    }
    atomic_text(
        output / "RESULT.json", json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
