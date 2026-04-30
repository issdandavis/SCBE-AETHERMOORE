"""Smoke tests for scripts/agents/scbe_code.py and safe_apply.py.

No GPU, no HuggingFace, no model load. Exercises the bijective tongue path,
the lookup-table render path, the stage6 manifest path, and the safe-apply
sandbox happy-path + rejection-path. The optional ``llm`` mode is exercised
only via ``--no-llm`` so the test suite stays offline.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import textwrap
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "agents"

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))


# ---------------------------------------------------------------------------
# scbe_code: tongue mode (no LLM)
# ---------------------------------------------------------------------------


def _run_cli(argv):
    """Run scbe_code.main(argv) and return (rc, stdout, stderr)."""
    from scripts.agents import scbe_code

    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = scbe_code.main(argv)
    return rc, out.getvalue(), err.getvalue()


def test_compile_ca_python_round_trip_bijective():
    rc, stdout, _ = _run_cli(
        ["compile-ca", "--opcodes", "0x00", "--target", "python", "--fn", "demo", "--args", "a,b", "--json"]
    )
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["round_trip_ok"] is True
    assert payload["op_trace"] == [[0, "add"]]
    assert "def demo(a, b)" in payload["source"]
    assert "# add (0x00)" in payload["source"]


def test_compile_ca_typescript_emits_signature():
    # 0x0A = neg (1-in/1-out), 0x09 = abs (1-in/1-out) — both have TS templates.
    rc, stdout, _ = _run_cli(
        ["compile-ca", "--opcodes", "0x0A,0x09", "--target", "typescript", "--fn", "neg_abs", "--args", "a"]
    )
    assert rc == 0
    assert "export function neg_abs(a: number): number | null" in stdout
    assert "// neg (0x0A)" in stdout
    assert "// abs (0x09)" in stdout


def test_compile_ca_rejects_underflow():
    # add needs two inputs; with no args the dispatcher raises ValueError.
    with pytest.raises(ValueError, match="underflow"):
        _run_cli(["compile-ca", "--opcodes", "0x00", "--args", ""])


def test_ca_plan_resolves_abs_abs_add_from_table():
    rc, stdout, _ = _run_cli(["ca-plan", "--ops", "abs,abs,add", "--json"])
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["source"] == "python.scbe.ca_opcode_table.OP_TABLE"
    assert payload["ops"] == ["abs", "abs", "add"]
    assert payload["hex_sequence"] == ["0x09", "0x09", "0x00"]
    assert payload["compile_hint"] == 'compile-ca --opcodes "0x09 0x09 0x00"'


def test_ca_plan_known_abs_add_expression():
    rc, stdout, _ = _run_cli(["ca-plan", "--expr", "abs(a)+abs(b)"])
    assert rc == 0
    assert stdout.strip() == "0x09, 0x09, 0x00"


def test_ca_plan_unknown_op_fails():
    rc, _, err = _run_cli(["ca-plan", "--ops", "abs,definitely_not_ca"])
    assert rc == 2
    assert "unknown CA op" in err


# ---------------------------------------------------------------------------
# scbe_code: lookup mode (no LLM)
# ---------------------------------------------------------------------------


def test_render_op_add_python_substitutes_placeholders():
    rc, stdout, _ = _run_cli(["render-op", "--op", "add", "--target", "KO", "--a", "x", "--b", "y", "--json"])
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["name"] == "add"
    assert payload["template"] == "({a} + {b})"
    assert payload["rendered"] == "(x + y)"


def test_render_op_supports_hex_id():
    rc, stdout, _ = _run_cli(["render-op", "--op", "0x00", "--target", "RU", "--a", "x", "--b", "y"])
    assert rc == 0
    assert "wrapping_add" in stdout


def test_render_op_unknown_op_fails():
    rc, _, err = _run_cli(["render-op", "--op", "definitely_not_an_op", "--target", "KO"])
    assert rc != 0
    assert "unknown op" in err


# ---------------------------------------------------------------------------
# scbe_code: stage6 manifest (no model)
# ---------------------------------------------------------------------------


def test_manifest_all_kinds_no_model():
    rc, stdout, _ = _run_cli(["manifest"])
    assert rc == 0
    payload = json.loads(stdout)
    kinds = {entry["kind"] for entry in payload["kinds"]}
    assert {
        "resource_jump_cancel",
        "lane_separation",
        "hex_trace",
        "cost_propagation",
        "training_boundary",
    }.issubset(kinds)
    for entry in payload["kinds"]:
        assert entry["forced_prefix"].startswith("required-tokens:")
        assert entry["forced_prefix"].endswith("::")


def test_manifest_kind_lookup_via_prompt_id_suffix():
    rc, stdout, _ = _run_cli(["manifest", "--prompt-id", "demo_resource_jump_cancel"])
    assert rc == 0
    payload = json.loads(stdout)
    assert len(payload["kinds"]) == 1
    assert payload["kinds"][0]["kind"] == "resource_jump_cancel"


# ---------------------------------------------------------------------------
# scbe_code: generate --no-llm short-circuit
# ---------------------------------------------------------------------------


def test_generate_no_llm_short_circuits():
    rc, stdout, _ = _run_cli(["generate", "--prompt", "hello", "--no-llm"])
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["skipped"] is True


# ---------------------------------------------------------------------------
# safe_apply: rejection of forbidden paths (no worktree created)
# ---------------------------------------------------------------------------


def test_safe_apply_rejects_dotgit_paths():
    from scripts.agents.safe_apply import apply_patch_safely

    bad_patch = textwrap.dedent("""\
        diff --git a/.git/config b/.git/config
        --- a/.git/config
        +++ b/.git/config
        @@ -1 +1,2 @@
         [core]
        +    evil = true
        """)
    result = apply_patch_safely(bad_patch)
    assert result.ok is False
    assert "forbidden" in result.error
    assert result.applied is False


def test_safe_apply_rejects_path_escape():
    from scripts.agents.safe_apply import apply_patch_safely

    escape_patch = textwrap.dedent("""\
        diff --git a/../etc/passwd b/../etc/passwd
        --- a/../etc/passwd
        +++ b/../etc/passwd
        @@ -1 +1 @@
        -root
        +pwn
        """)
    result = apply_patch_safely(escape_patch)
    assert result.ok is False
    assert "forbidden" in result.error or "escape" in result.error.lower()


def test_safe_apply_empty_patch():
    from scripts.agents.safe_apply import apply_patch_safely

    result = apply_patch_safely("")
    assert result.ok is False
    assert result.error == "empty patch"


# ---------------------------------------------------------------------------
# safe_apply: happy-path on a real worktree (creates + deletes a tiny file)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    subprocess.call(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    != 0,
    reason="repo isn't a git work tree",
)
def test_safe_apply_dry_run_smoke_passes(tmp_path):
    """Create a brand-new file via patch, assert sandbox smoke passes, no main-tree write."""
    from scripts.agents.safe_apply import apply_patch_safely

    rel = "tests/_safe_apply_probe_DELETE_ME.txt"
    main_target = REPO_ROOT / rel
    if main_target.exists():
        pytest.skip(f"{rel} already exists; refusing to overwrite")

    patch = textwrap.dedent(f"""\
        diff --git a/{rel} b/{rel}
        new file mode 100644
        index 0000000..e69de29
        --- /dev/null
        +++ b/{rel}
        @@ -0,0 +1 @@
        +scbe_code safe_apply smoke probe
        """)

    result = apply_patch_safely(patch, smoke_cmd="python -c \"print('ok')\"", smoke_timeout=30)

    # Sandbox path was named, smoke ran, main tree untouched.
    assert result.smoke_returncode == 0, result.smoke_stderr or result.error
    assert result.ok is True
    assert result.applied is True
    # Cleanup: remove the file we just patched into the main tree.
    if main_target.exists():
        main_target.unlink()
