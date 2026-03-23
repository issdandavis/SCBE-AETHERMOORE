#!/usr/bin/env python3
"""PQCM formula audit helpers for SCBE.

Focus: detect scaling/behaviour issues in
``kappa_eff = (E/N) * log(1 + det(L))``.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Iterable, List


@dataclass
class KappaRecord:
    n: int
    edges: int
    reduced_det: int
    baseline: float
    kappa_eff: float
    ratio_to_baseline: float


def complete_graph_edges(n: int) -> int:
    """Return edge count of complete graph with n nodes."""
    if n <= 1:
        return 0
    return n * (n - 1) // 2


def spanning_tree_count_complete_graph(n: int) -> int:
    """Kirchhoff result for complete graph K_n.

    For K_n, reduced Laplacian determinant equals n^(n-2).
    """
    if n < 2:
        return 0
    return n ** (n - 2)


def kappa_base(e: int, n: int) -> float:
    return 0.0 if n == 0 else e / n


def kappa_eff(e: int, n: int, reduced_det: int) -> float:
    """Compute proposal kappa_eff with scalar spanning-tree proxy det(L)."""
    if n == 0:
        return 0.0
    return (e / n) * log(1.0 + reduced_det)


def audit_records(max_nodes: int) -> List[KappaRecord]:
    """Audit complete graphs K_n where det growth is exactly known."""
    if max_nodes < 2:
        raise ValueError("max_nodes must be >= 2")
    rows: List[KappaRecord] = []
    for n in range(2, max_nodes + 1):
        e = complete_graph_edges(n)
        det = spanning_tree_count_complete_graph(n)
        base = kappa_base(e, n)
        eff = kappa_eff(e, n, det)
        ratio = eff / base if base else float("inf")
        rows.append(
            KappaRecord(
                n=n,
                edges=e,
                reduced_det=det,
                baseline=base,
                kappa_eff=eff,
                ratio_to_baseline=ratio,
            )
        )
    return rows


def detect_growth_issue(records: Iterable[KappaRecord]) -> bool:
    """Return True when ratio to baseline grows with graph size (unbounded path)."""
    sorted_records = sorted(records, key=lambda r: r.n)
    for i in range(1, len(sorted_records)):
        if sorted_records[i].ratio_to_baseline <= sorted_records[i - 1].ratio_to_baseline:
            return False
    return True


def build_audit_summary(records: Iterable[KappaRecord]) -> str:
    rows = list(records)
    if not rows:
        return "No rows to audit."

    growth_issue = detect_growth_issue(rows)
    final = rows[-1]
    outcome = (
        "FAIL: growth risk" if growth_issue else "PASS: bounded behavior"
    )
    lines = [
        "# PQCM Audit",
        f"Verdict: {outcome}",
        f"det(L) growth sample n={rows[0].n}-{final.n}",
        f"det(K_n) = n^(n-2) -> {rows[0].reduced_det}..{final.reduced_det}",
        f"final ratio kappa_eff / kappa = {final.ratio_to_baseline:.6g}",
    ]
    lines.append("")
    lines.append("n, E, baseline, kappa_eff, reduced_det, ratio")
    for row in rows:
        lines.append(
            f"{row.n}, {row.edges}, {row.baseline:.6g}, "
            f"{row.kappa_eff:.6g}, {row.reduced_det}, {row.ratio_to_baseline:.6g}"
        )
    return "\n".join(lines)


def hf_dataset_card_metadata() -> dict[str, object]:
    """Schema payload useful for a SCBE dataset card markdown frontmatter."""
    return {
        "dataset_id": "scbe-pqcm-audit-log",
        "title": "SCBE PQCM Formula Audit Log",
        "layers": [1, 5, 8, 12],
        "sacred_tongue_affinity": ["KO", "CA", "DR"],
        "dual_output_schema": {
            "StateVector": ["n", "E", "det(L)", "kappa", "kappa_eff"],
            "DecisionRecord": ["decision", "signature", "timestamp", "rationale"],
        },
        "notes": [
            "det(L) uses reduced Laplacian determinant for spanning-tree count",
            "warn on O(N^N) growth path without graph-size normalization",
        ],
    }


try:
    from hypothesis import given, strategies as st
except Exception:  # pragma: no cover
    given = None
    st = None


if given is not None and st is not None:
    @given(st.integers(min_value=2, max_value=28))
    def _test_monotone_by_graph_size(n: int) -> None:
        rows = audit_records(n)
        assert rows[-1].kappa_eff > rows[0].kappa_eff

    @given(st.integers(min_value=2, max_value=28))
    def _test_ratio_increases_with_n(n: int) -> None:
        rows = audit_records(n)
        assert rows[-1].ratio_to_baseline > 1.0
        assert detect_growth_issue(rows)


def run_property_checks() -> None:
    if given is None or st is None:
        raise RuntimeError("hypothesis not installed; cannot run property tests.")
    _test_monotone_by_graph_size()
    _test_ratio_increases_with_n()


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description="Run PQCM formula audit probes.")
    p.add_argument("--max-n", type=int, default=12)
    p.add_argument("--run-properties", action="store_true")
    args = p.parse_args()

    rows = audit_records(max_nodes=args.max_n)
    print(build_audit_summary(rows))
    print("\nCard metadata:")
    print(hf_dataset_card_metadata())

    if args.run_properties:
        run_property_checks()
