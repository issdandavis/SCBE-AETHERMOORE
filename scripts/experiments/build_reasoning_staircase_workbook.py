from __future__ import annotations

"""Build an auditable Excel ledger for the triadic reasoning staircase."""

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook, load_workbook
from openpyxl.chart import ScatterChart, Series, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo


PHI = (1.0 + math.sqrt(5.0)) / 2.0
GOLDEN_ANGLE = 2.0 * math.pi * (1.0 - 1.0 / PHI)
TARGET_WEIGHTS = (3, 2, 2, -2, -1, 1)
DEFAULT_OUTPUT = Path("artifacts") / "reasoning_staircase_20261021.xlsx"


@dataclass(frozen=True)
class Node:
    node_id: str
    depth_z: int
    realm: str
    role: str
    local_index: int
    radius: float
    theta: float
    x: float
    y: float
    phi_scale: float
    source_value: float | None
    source_kind: str
    residual_slot: str


@dataclass(frozen=True)
class Edge:
    edge_id: str
    source: str
    target: str
    edge_type: str
    weight: float
    polarity: int
    inverse_edge: str
    residual_of: str
    shared_group: str
    authorized: str


def build_topology(depths: int = 14) -> tuple[list[Node], list[Edge]]:
    nodes: list[Node] = []
    edges: list[Edge] = []
    for depth in range(depths):
        phase = depth * GOLDEN_ANGLE
        scale = PHI ** (depth / max(depths - 1, 1))
        nodes.append(
            Node(
                f"z{depth:02d}.anchor",
                depth,
                "staircase",
                "anchor",
                0,
                0.0,
                phase,
                0.0,
                0.0,
                scale,
                None,
                "route",
                f"route.z{depth:02d}",
            )
        )
        for axis, value in enumerate(TARGET_WEIGHTS):
            theta = phase + 2.0 * math.pi * axis / len(TARGET_WEIGHTS)
            radius = 1.0 + 0.08 * depth
            nodes.append(
                Node(
                    f"z{depth:02d}.e{axis}",
                    depth,
                    "evidence",
                    "coordinate",
                    axis,
                    radius,
                    theta,
                    radius * math.cos(theta),
                    radius * math.sin(theta),
                    scale,
                    float(value),
                    "exact_sidecar",
                    f"evidence.axis{axis}",
                )
            )
            edge_base = f"z{depth:02d}.axis{axis}"
            edges.extend(
                [
                    Edge(
                        f"{edge_base}.fanout",
                        f"z{depth:02d}.anchor",
                        f"z{depth:02d}.e{axis}",
                        "fanout",
                        1.0,
                        0,
                        f"{edge_base}.return",
                        "",
                        f"axis{axis}",
                        "typed",
                    ),
                    Edge(
                        f"{edge_base}.return",
                        f"z{depth:02d}.e{axis}",
                        f"z{depth:02d}.anchor",
                        "return",
                        1.0,
                        0,
                        f"{edge_base}.fanout",
                        "",
                        f"axis{axis}",
                        "typed",
                    ),
                    Edge(
                        f"{edge_base}.affirm",
                        f"z{depth:02d}.e{axis}",
                        f"z{depth:02d}.affirm",
                        "evidence",
                        abs(float(value)),
                        1,
                        "",
                        "",
                        f"decision.z{depth:02d}",
                        "measured",
                    ),
                    Edge(
                        f"{edge_base}.counter",
                        f"z{depth:02d}.e{axis}",
                        f"z{depth:02d}.counter",
                        "evidence",
                        abs(float(value)),
                        -1,
                        "",
                        "",
                        f"decision.z{depth:02d}",
                        "measured",
                    ),
                ]
            )
        role_layout = {
            "affirm": (2.2, phase + math.pi / 3.0, 1),
            "counter": (2.2, phase - math.pi / 3.0, -1),
            "judge": (3.0, phase, 0),
        }
        for index, (role, (radius, theta, polarity)) in enumerate(role_layout.items(), 1):
            nodes.append(
                Node(
                    f"z{depth:02d}.{role}",
                    depth,
                    "decision",
                    role,
                    index,
                    radius,
                    theta,
                    radius * math.cos(theta),
                    radius * math.sin(theta),
                    scale,
                    float(polarity),
                    "learned_head",
                    f"decision.{role}",
                )
            )
        for role in ("affirm", "counter"):
            edges.append(
                Edge(
                    f"z{depth:02d}.{role}.judge",
                    f"z{depth:02d}.{role}",
                    f"z{depth:02d}.judge",
                    "adjudicate",
                    1.0,
                    1 if role == "affirm" else -1,
                    "",
                    "",
                    f"decision.z{depth:02d}",
                    "measured",
                )
            )
        edges.append(
            Edge(
                f"z{depth:02d}.residual",
                f"z{depth:02d}.judge",
                f"z{depth:02d}.anchor",
                "residual_return",
                1.0,
                0,
                "",
                f"route.z{depth:02d}",
                f"decision.z{depth:02d}",
                "receipt_required",
            )
        )
        if depth + 1 < depths:
            edges.extend(
                [
                    Edge(
                        f"z{depth:02d}.ascend",
                        f"z{depth:02d}.judge",
                        f"z{depth + 1:02d}.anchor",
                        "ascend",
                        PHI,
                        1,
                        f"z{depth + 1:02d}.descend",
                        "",
                        "shared_staircase",
                        "judge_pass",
                    ),
                    Edge(
                        f"z{depth + 1:02d}.descend",
                        f"z{depth + 1:02d}.anchor",
                        f"z{depth:02d}.judge",
                        "descend",
                        1.0 / PHI,
                        -1,
                        f"z{depth:02d}.ascend",
                        "",
                        "shared_staircase",
                        "inverse_receipt",
                    ),
                ]
            )
    return nodes, edges


def add_table(ws, name: str) -> None:
    table = Table(displayName=name, ref=ws.dimensions)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False, showRowStripes=True
    )
    ws.add_table(table)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions


def style_header(ws) -> None:
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center")


def auto_width(ws, maximum: int = 38) -> None:
    for column in ws.columns:
        width = max(len(str(cell.value or "")) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = min(width + 2, maximum)


def load_receipt(path: Path | None) -> dict[str, object] | None:
    return json.loads(path.read_text(encoding="utf-8")) if path and path.exists() else None


def build_workbook(
    output: Path,
    multiview: dict[str, object] | None,
    triadic: dict[str, object] | None,
    sidecar: dict[str, object] | None,
    depths: int = 14,
    staircase: dict[str, object] | None = None,
    staircase_sidecar: dict[str, object] | None = None,
    staircase_snap: dict[str, object] | None = None,
) -> Path:
    nodes, edges = build_topology(depths)
    node_row = {node.node_id: index + 2 for index, node in enumerate(nodes)}
    workbook = Workbook()
    readme = workbook.active
    readme.title = "README"
    readme_rows = [
        ("Reasoning staircase ledger", "Inspectable topology; not an execution engine"),
        ("Node sheet", "Local, radial, and z coordinates for every landing"),
        ("Edge sheet", "Typed direction, inverse, shared group, and residual lineage"),
        ("Link_Ledger", "Clickable source/target links into Nodes"),
        ("Elastic_Paths", "Deformable residual geometry with fixed endpoint identity"),
        ("Staircase_Grid", "One whole decision grid per depth"),
        ("Phi_Schedule", "Golden-angle coordinates and reversible depth links"),
        ("Results", "Measured arm means and registered claim gates"),
        ("Rule", "A realm may update its receipt; it may not overwrite the route anchor"),
    ]
    for row in readme_rows:
        readme.append(row)
    readme["A1"].font = Font(bold=True, size=16)
    readme.column_dimensions["A"].width = 28
    readme.column_dimensions["B"].width = 88

    node_ws = workbook.create_sheet("Nodes")
    node_ws.append(list(Node.__dataclass_fields__))
    for node in nodes:
        node_ws.append(list(node.__dict__.values()))
    style_header(node_ws)
    add_table(node_ws, "NodeLedger")
    auto_width(node_ws)

    edge_ws = workbook.create_sheet("Edges")
    edge_ws.append(list(Edge.__dataclass_fields__))
    for edge in edges:
        edge_ws.append(list(edge.__dict__.values()))
    style_header(edge_ws)
    add_table(edge_ws, "EdgeLedger")
    auto_width(edge_ws)

    link_ws = workbook.create_sheet("Link_Ledger")
    link_ws.append(
        [
            "edge_id",
            "source_link",
            "target_link",
            "type",
            "inverse_edge",
            "residual_of",
            "shared_group",
            "authorized",
        ]
    )
    for edge in edges:
        source_row = node_row[edge.source]
        target_row = node_row[edge.target]
        link_ws.append(
            [
                edge.edge_id,
                f'=HYPERLINK("#Nodes!A{source_row}","{edge.source}")',
                f'=HYPERLINK("#Nodes!A{target_row}","{edge.target}")',
                edge.edge_type,
                edge.inverse_edge,
                edge.residual_of,
                edge.shared_group,
                edge.authorized,
            ]
        )
    style_header(link_ws)
    add_table(link_ws, "LinkLedger")
    auto_width(link_ws)

    elastic_ws = workbook.create_sheet("Elastic_Paths")
    elastic_ws.append(
        [
            "edge_id",
            "source",
            "target",
            "rest_length",
            "spring_k",
            "damping_c",
            "bend_kappa",
            "max_stretch_ratio",
            "payload",
            "topology_locked",
            "render_path",
        ]
    )
    node_by_id = {node.node_id: node for node in nodes}
    for edge in edges:
        source = node_by_id[edge.source]
        target = node_by_id[edge.target]
        dz = float(target.depth_z - source.depth_z)
        rest_length = math.sqrt(
            (target.x - source.x) ** 2 + (target.y - source.y) ** 2 + dz**2
        )
        spring_k = max(0.25, abs(edge.weight))
        elastic_ws.append(
            [
                edge.edge_id,
                edge.source,
                edge.target,
                rest_length,
                spring_k,
                0.70 * math.sqrt(spring_k),
                1.0 / PHI,
                PHI,
                edge.residual_of or edge.shared_group,
                True,
                "bounded cubic spline",
            ]
        )
    style_header(elastic_ws)
    add_table(elastic_ws, "ElasticPathLedger")
    auto_width(elastic_ws)

    grid_ws = workbook.create_sheet("Staircase_Grid")
    grid_headers = ["depth_z", "anchor"] + [f"evidence_{i}" for i in range(6)] + [
        "affirm",
        "counter",
        "judge",
        "residual_return",
        "ascend",
    ]
    grid_ws.append(grid_headers)
    for depth in range(depths):
        ids = [f"z{depth:02d}.anchor"] + [f"z{depth:02d}.e{i}" for i in range(6)] + [
            f"z{depth:02d}.affirm",
            f"z{depth:02d}.counter",
            f"z{depth:02d}.judge",
        ]
        row = [depth]
        for node_id in ids:
            row.append(f'=HYPERLINK("#Nodes!A{node_row[node_id]}","{node_id}")')
        row.extend(
            [
                f'=HYPERLINK("#Edges!A{2 + next(i for i, e in enumerate(edges) if e.edge_id == f"z{depth:02d}.residual")}","residual")',
                (
                    f'=HYPERLINK("#Nodes!A{node_row[f"z{depth + 1:02d}.anchor"]}","z{depth + 1:02d}")'
                    if depth + 1 < depths
                    else "END"
                ),
            ]
        )
        grid_ws.append(row)
    style_header(grid_ws)
    add_table(grid_ws, "StaircaseGrid")
    auto_width(grid_ws)

    phi_ws = workbook.create_sheet("Phi_Schedule")
    phi_ws.append(
        ["depth_z", "theta_rad", "theta_deg", "radius", "x", "y", "phi_scale", "previous", "next"]
    )
    for depth in range(depths):
        theta = depth * GOLDEN_ANGLE
        radius = math.sqrt(depth + 1)
        phi_ws.append(
            [
                depth,
                theta,
                math.degrees(theta) % 360.0,
                radius,
                radius * math.cos(theta),
                radius * math.sin(theta),
                PHI ** (depth / max(depths - 1, 1)),
                depth - 1 if depth else "",
                depth + 1 if depth + 1 < depths else "",
            ]
        )
    style_header(phi_ws)
    add_table(phi_ws, "PhiSchedule")
    auto_width(phi_ws)
    chart = ScatterChart()
    chart.title = "Golden-angle staircase projection"
    chart.x_axis.title = "x"
    chart.y_axis.title = "y"
    chart.series.append(
        Series(
            Reference(phi_ws, min_col=6, min_row=2, max_row=depths + 1),
            Reference(phi_ws, min_col=5, min_row=2, max_row=depths + 1),
            title="depth",
        )
    )
    phi_ws.add_chart(chart, "K2")

    result_ws = workbook.create_sheet("Results")
    result_ws.append(
        [
            "experiment",
            "arm",
            "metric",
            "mean",
            "minimum",
            "maximum",
            "seeds",
            "claim",
        ]
    )
    for experiment, receipt in (
        ("multiview", multiview),
        ("triadic_latent", triadic),
        ("triadic_sidecar", sidecar),
        ("staircase_coupled", staircase),
        ("staircase_decoupled", staircase_sidecar),
        ("staircase_lattice_snap", staircase_snap),
    ):
        if not receipt:
            continue
        for arm in receipt["arms"]:
            rows = [row for row in receipt["runs"] if row["arm"] == arm["name"]]
            metric_names = sorted(rows[0]["metrics"])
            for metric in metric_names:
                values = [float(row["metrics"][metric]) for row in rows]
                result_ws.append(
                    [
                        experiment,
                        arm["name"],
                        metric,
                        sum(values) / len(values),
                        min(values),
                        max(values),
                        ",".join(str(row["seed"]) for row in rows),
                        "",
                    ]
                )
        for claim, passed in receipt["analysis"]["claim_rules"].items():
            result_ws.append([experiment, "", "", "", "", "", "", f"{claim}={passed}"])
    style_header(result_ws)
    add_table(result_ws, "ResultLedger")
    auto_width(result_ws)
    if result_ws.max_row > 2:
        result_ws.conditional_formatting.add(
            f"D2:D{result_ws.max_row}",
            ColorScaleRule(
                start_type="min",
                start_color="F8696B",
                mid_type="percentile",
                mid_value=50,
                mid_color="FFEB84",
                end_type="max",
                end_color="63BE7B",
            ),
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output)
    # Reopen now so a corrupt or unsupported workbook fails before it is reported.
    checked = load_workbook(output, read_only=False, data_only=False)
    required = {
        "README",
        "Nodes",
        "Edges",
        "Link_Ledger",
        "Elastic_Paths",
        "Staircase_Grid",
        "Phi_Schedule",
        "Results",
    }
    if not required.issubset(checked.sheetnames):
        raise RuntimeError("saved workbook is missing required sheets")
    checked.close()
    return output


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--depths", type=int, default=14)
    parser.add_argument("--multiview-results", type=Path)
    parser.add_argument("--triadic-results", type=Path)
    parser.add_argument("--sidecar-results", type=Path)
    parser.add_argument("--staircase-results", type=Path)
    parser.add_argument("--staircase-sidecar-results", type=Path)
    parser.add_argument("--staircase-snap-results", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.depths < 2:
        parser.error("--depths must be at least 2")
    output = build_workbook(
        args.output,
        load_receipt(args.multiview_results),
        load_receipt(args.triadic_results),
        load_receipt(args.sidecar_results),
        depths=args.depths,
        staircase=load_receipt(args.staircase_results),
        staircase_sidecar=load_receipt(args.staircase_sidecar_results),
        staircase_snap=load_receipt(args.staircase_snap_results),
    )
    print(output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
