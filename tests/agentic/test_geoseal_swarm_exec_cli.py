"""Smoke tests for `geoseal swarm-exec` — the meet-in-the-middle CLI surface.

These exercise the full subcommand dispatch (argparse → cmd_swarm_exec →
merge_halves → execution gate) by invoking the geoseal_cli module as a
subprocess. We assert on stdout text rather than on internal state so we
catch regressions that any UI consumer would notice.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

GEOSEAL_CLI = "src/geoseal_cli.py"

FORWARD_GOOD = textwrap.dedent("""\
    def gate_prompt(raw):
        payload = {"text": raw, "len": len(raw)}
        drift = 1.5 if "ignore previous" in (raw or "").lower() else 0.0
        score = 1.0 / (1.0 + drift)
        verdict = "ALLOW" if score >= 0.66 else "DENY"
        # === SCBE_MEET_SEAM ===
    """)

REVERSE_GOOD = textwrap.dedent("""\
        # === SCBE_MEET_SEAM ===
        return {"payload": payload, "verdict": verdict, "score": round(score, 3)}


    if __name__ == "__main__":
        import json
        print(json.dumps(gate_prompt("Help me draft an email.")))
    """)


def _write_halves(tmp_path: Path, fwd_text: str, rev_text: str) -> tuple[Path, Path]:
    fwd = tmp_path / "forward.py"
    rev = tmp_path / "reverse.py"
    fwd.write_text(fwd_text, encoding="utf-8")
    rev.write_text(rev_text, encoding="utf-8")
    return fwd, rev


def _run_cli(*extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, GEOSEAL_CLI, "swarm-exec", *extra],
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_convergence_only_prints_matching_hashes(tmp_path: Path) -> None:
    fwd, rev = _write_halves(tmp_path, FORWARD_GOOD, REVERSE_GOOD)
    proc = _run_cli(
        "--forward",
        str(fwd),
        "--reverse",
        str(rev),
        "--seam-names",
        "payload,verdict,score",
        "--seam-types",
        "dict,str,float",
        "--json",
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["converged"] is True
    assert payload["forward_seam_hash"] == payload["reverse_seam_hash"]
    assert payload["seam_contract"]["names"] == ["payload", "verdict", "score"]
    assert payload["merged_source"] is not None


def test_divergent_seam_names_block_merge(tmp_path: Path) -> None:
    fwd, rev = _write_halves(tmp_path, FORWARD_GOOD, REVERSE_GOOD)
    proc = _run_cli(
        "--forward",
        str(fwd),
        "--reverse",
        str(rev),
        # `decision` is not bound by the forward half → fail
        "--seam-names",
        "payload,decision,score",
        "--json",
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["converged"] is False
    assert any("does not bind seam names" in d for d in payload["diagnostics"])


def test_execute_path_runs_merged_module_through_gate(tmp_path: Path) -> None:
    fwd, rev = _write_halves(tmp_path, FORWARD_GOOD, REVERSE_GOOD)
    proc = _run_cli(
        "--forward",
        str(fwd),
        "--reverse",
        str(rev),
        "--seam-names",
        "payload,verdict,score",
        "--execute",
        "--no-audit",
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stdout
    assert "converged=True" in out
    assert "tier=ALLOW" in out
    assert "ran=True" in out
    # The merged module prints a JSON envelope for the benign prompt.
    assert "ALLOW" in out and "Help me draft" in out


def test_missing_forward_file_returns_error(tmp_path: Path) -> None:
    rev = tmp_path / "reverse.py"
    rev.write_text(REVERSE_GOOD, encoding="utf-8")
    proc = _run_cli(
        "--forward",
        str(tmp_path / "nope.py"),
        "--reverse",
        str(rev),
        "--seam-names",
        "payload,verdict,score",
    )
    assert proc.returncode == 2
    assert "forward half not found" in proc.stderr


def test_missing_seam_marker_blocks_with_diagnostic(tmp_path: Path) -> None:
    fwd_no_seam = "x = 1\n"  # no SEAM_MARKER
    fwd, rev = _write_halves(tmp_path, fwd_no_seam, REVERSE_GOOD)
    proc = _run_cli(
        "--forward",
        str(fwd),
        "--reverse",
        str(rev),
        "--seam-names",
        "payload,verdict,score",
        "--json",
    )
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["converged"] is False
    assert any("forward half missing SEAM_MARKER" in d for d in payload["diagnostics"])


def test_seam_types_must_be_parallel_or_empty(tmp_path: Path) -> None:
    fwd, rev = _write_halves(tmp_path, FORWARD_GOOD, REVERSE_GOOD)
    proc = _run_cli(
        "--forward",
        str(fwd),
        "--reverse",
        str(rev),
        "--seam-names",
        "payload,verdict,score",
        "--seam-types",
        "dict,str",  # too short
    )
    assert proc.returncode == 2
    assert "parallel" in proc.stderr
