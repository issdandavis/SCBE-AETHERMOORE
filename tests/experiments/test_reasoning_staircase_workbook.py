from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts" / "experiments" / "build_reasoning_staircase_workbook.py"
SPEC = importlib.util.spec_from_file_location("build_reasoning_staircase_workbook", SOURCE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


def test_topology_has_inverse_stairs_and_residual_returns() -> None:
    nodes, edges = M.build_topology(4)
    node_ids = {node.node_id for node in nodes}
    edge_by_id = {edge.edge_id: edge for edge in edges}
    assert all(edge.source in node_ids and edge.target in node_ids for edge in edges)
    ascents = [edge for edge in edges if edge.edge_type == "ascend"]
    residuals = [edge for edge in edges if edge.edge_type == "residual_return"]
    assert len(ascents) == 3
    assert len(residuals) == 4
    for edge in ascents:
        inverse = edge_by_id[edge.inverse_edge]
        assert inverse.source == edge.target
        assert inverse.target == edge.source


def test_workbook_reopens_with_links_and_required_sheets(tmp_path: Path) -> None:
    output = M.build_workbook(tmp_path / "stairs.xlsx", None, None, None, depths=4)
    workbook = load_workbook(output, data_only=False)
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
    assert required.issubset(workbook.sheetnames)
    assert str(workbook["Link_Ledger"]["B2"].value).startswith("=HYPERLINK")
    assert str(workbook["Staircase_Grid"]["B2"].value).startswith("=HYPERLINK")
    angles = [workbook["Phi_Schedule"].cell(row=row, column=3).value for row in range(2, 6)]
    assert len(set(angles)) == 4
    assert all(
        workbook["Elastic_Paths"].cell(row=row, column=10).value
        for row in range(2, workbook["Elastic_Paths"].max_row + 1)
    )
    workbook.close()


def test_workbook_accepts_staircase_result_receipts(tmp_path: Path) -> None:
    receipt = {
        "arms": [{"name": "receipt"}],
        "runs": [{"arm": "receipt", "seed": 11, "metrics": {"deep_route_floor": 0.75}}],
        "analysis": {"claim_rules": {"receipt_support": True}},
    }
    output = M.build_workbook(
        tmp_path / "stairs-results.xlsx",
        None,
        None,
        None,
        depths=3,
        staircase=receipt,
        staircase_sidecar=receipt,
        staircase_snap=receipt,
    )
    workbook = load_workbook(output, data_only=False)
    experiments = {
        workbook["Results"].cell(row=row, column=1).value
        for row in range(2, workbook["Results"].max_row + 1)
    }
    assert {
        "staircase_coupled",
        "staircase_decoupled",
        "staircase_lattice_snap",
    }.issubset(experiments)
    workbook.close()
