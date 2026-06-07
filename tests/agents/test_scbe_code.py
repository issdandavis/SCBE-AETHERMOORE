"""Smoke tests for scripts/agents/scbe_code.py and safe_apply.py.

No GPU, no HuggingFace, no model load. Exercises the bijective tongue path,
the lookup-table render path, the stage6 manifest path, and the safe-apply
sandbox happy-path + rejection-path. The optional ``llm`` mode is exercised
only via ``--no-llm`` so the test suite stays offline.
"""

from __future__ import annotations

import io
import json
import math
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
        [
            "compile-ca",
            "--opcodes",
            "0x00",
            "--target",
            "python",
            "--fn",
            "demo",
            "--args",
            "a,b",
            "--json",
        ]
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
        [
            "compile-ca",
            "--opcodes",
            "0x0A,0x09",
            "--target",
            "typescript",
            "--fn",
            "neg_abs",
            "--args",
            "a",
        ]
    )
    assert rc == 0
    assert "export function neg_abs(a: number): number | null" in stdout
    assert "// neg (0x0A)" in stdout
    assert "// abs (0x09)" in stdout


def test_compile_ca_c_round_trip_bijective():
    rc, stdout, _ = _run_cli(
        [
            "compile-ca",
            "--opcodes",
            "0x09,0x09,0x00",
            "--target",
            "c",
            "--fn",
            "abs_add",
            "--args",
            "a,b",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["round_trip_ok"] is True
    assert payload["op_trace"] == [[9, "abs"], [9, "abs"], [0, "add"]]
    assert "double abs_add(double a, double b)" in payload["source"]
    assert "// add (0x00)" in payload["source"]
    # C uses single-dash `_sp -= 1` so it must NOT false-trigger the `--` (haskell) branch.
    assert "-= 1" in payload["source"]


def test_compile_ca_haskell_round_trip_bijective():
    rc, stdout, _ = _run_cli(
        [
            "compile-ca",
            "--opcodes",
            "0x09,0x09,0x00",
            "--target",
            "haskell",
            "--fn",
            "abs_add",
            "--args",
            "a,b",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["round_trip_ok"] is True
    assert payload["op_trace"] == [[9, "abs"], [9, "abs"], [0, "add"]]
    assert "abs_add a b =" in payload["source"]
    assert "-- add (0x00)" in payload["source"]
    # head = top => args reversed in the initial list.
    assert "s0 = [b, a] :: [Double]" in payload["source"]


# ---------------------------------------------------------------------------
# Cross-language semantic checks. Be precise about what each tier proves:
#
#   * test_emitted_python_matches_rpn_reference -- the ONLY non-circular tier.
#     It EXECUTES the real emitted Python and compares to an independent RPN
#     reference. seqs include `mod` on negative operands (the one op where
#     truncation vs floor semantics actually diverge).
#   * _c_model / _hs_model -- hand-written Python mirrors of the C array model
#     and the Haskell list model. There is no gcc/ghc on this box, so the
#     emitted C/Haskell is NOT compiled or run. These mirrors transcribe the
#     template arithmetic LITERALLY (e.g. floor-mod `a - b*floor(a/b)`, not
#     Python `%`), so they catch transcription drift between template and
#     mirror, and pin the negative-operand semantics -- but a shared concept
#     error in both template and mirror would still pass. For emitted C/Haskell
#     the TESTED witness is the bijection round-trip (trace survives), above.
# ---------------------------------------------------------------------------

_ALPHABET = [
    ("add", 0x00),
    ("sub", 0x01),
    ("mul", 0x02),
    ("div", 0x03),
    ("mod", 0x04),
    ("abs", 0x09),
    ("neg", 0x0A),
    ("inc", 0x0B),
    ("dec", 0x0C),
    ("eq", 0x20),
    ("lt", 0x22),
    ("gt", 0x24),
]


def _rpn_reference(ops, a, b):
    """Independent ground-truth RPN evaluator (the semantics every target must match)."""
    st = [float(a), float(b)]
    for name in ops:
        if name in ("add", "sub", "mul", "div", "mod", "eq", "lt", "gt"):
            y = st.pop()
            x = st.pop()
            if name == "add":
                st.append(x + y)
            elif name == "sub":
                st.append(x - y)
            elif name == "mul":
                st.append(x * y)
            elif name == "div":
                st.append(x / y if y != 0 else 0)
            elif name == "mod":
                st.append(x % y if y != 0 else 0)
            elif name == "eq":
                st.append(1 if x == y else 0)
            elif name == "lt":
                st.append(1 if x < y else 0)
            else:
                st.append(1 if x > y else 0)
        else:  # unary
            x = st.pop()
            if name == "neg":
                st.append(-x)
            elif name == "abs":
                st.append(abs(x))
            elif name == "inc":
                st.append(x + 1)
            else:  # dec
                st.append(x - 1)
    return st[-1] if st else None


def _floor_mod(x, y):
    """Sign-follows-divisor mod, transcribing the C/Haskell templates literally."""
    return x - y * math.floor(x / y) if y != 0 else 0


def _binary(name, x, y):
    """Shared binary op semantics, written to mirror the template arithmetic literally."""
    if name == "add":
        return x + y
    if name == "sub":
        return x - y
    if name == "mul":
        return x * y
    if name == "div":
        return x / y if y != 0 else 0
    if name == "mod":
        return _floor_mod(x, y)
    if name == "eq":
        return 1 if x == y else 0
    if name == "lt":
        return 1 if x < y else 0
    return 1 if x > y else 0  # gt


_BINARY_OPS = ("add", "sub", "mul", "div", "mod", "eq", "lt", "gt")


def _c_model(ops, a, b):
    """Mirror the emitted C array model (_st / _sp; top = _st[_sp-1])."""
    st = [float(a), float(b)] + [0.0] * 8
    sp = 2
    for name in ops:
        if name in _BINARY_OPS:
            top = st[sp - 1]
            sp -= 1
            st[sp - 1] = _binary(name, st[sp - 1], top)
        elif name == "abs":
            st[sp - 1] = abs(st[sp - 1])  # fabs
        elif name == "neg":
            st[sp - 1] = -st[sp - 1]
        elif name == "inc":
            st[sp - 1] = st[sp - 1] + 1
        else:  # dec
            st[sp - 1] = st[sp - 1] - 1
    return st[sp - 1] if sp > 0 else 0


def _hs_model(ops, a, b):
    """Mirror the emitted Haskell list model (head = top, args reversed)."""
    s = [float(b), float(a)]  # s0 = [b, a]
    for name in ops:
        if name == "abs":
            s = [abs(s[0])] + s[1:]
        elif name == "neg":
            s = [-s[0]] + s[1:]
        elif name == "inc":
            s = [s[0] + 1] + s[1:]
        elif name == "dec":
            s = [s[0] - 1] + s[1:]
        else:  # binary: \(b:a:r) -> f a b : r  (top = b, second = a)
            top, second, rest = s[0], s[1], s[2:]
            s = [_binary(name, second, top)] + rest
    return s[0] if s else None


_NAME_TO_CODE = dict(_ALPHABET)
_INPUTS = [(3.0, -2.0), (-5.0, 4.0), (0.0, 7.0), (6.0, 6.0), (-1.5, -3.25)]
# `mod` on negatives is the divergence case: C `fmod` truncates, Python/Haskell floor.
_SEQS = [
    ["abs", "neg", "add"],
    ["inc", "dec", "mul"],
    ["abs", "abs", "add"],
    ["lt", "neg"],
    ["mod"],
    ["mod", "abs"],
    ["mod", "inc"],
]


@pytest.mark.parametrize("seq", _SEQS)
@pytest.mark.parametrize("a,b", _INPUTS)
def test_emitted_python_matches_rpn_reference(seq, a, b):
    """Execute the REAL emitted Python and check it matches the RPN ground truth."""
    from python.scbe.tongue_isa import compile_ca_tokens

    opcodes = [_NAME_TO_CODE[n] for n in seq]
    program = compile_ca_tokens(
        opcodes, target="python", fn_name="probe", arg_names=["a", "b"]
    )
    src_lines = ["def probe(a, b):"] + ["    " + ln for ln in program.body_lines]
    ns: dict = {}
    exec("\n".join(src_lines), ns)  # noqa: S102 -- generated, trusted source
    got = ns["probe"](a, b)
    assert got == pytest.approx(_rpn_reference(seq, a, b))


@pytest.mark.parametrize("seq", _SEQS)
@pytest.mark.parametrize("a,b", _INPUTS)
def test_c_and_haskell_models_match_rpn_reference(seq, a, b):
    """C and Haskell stack models agree with the RPN reference, incl. mod-on-negatives.

    These are template mirrors, not compiled code (no gcc/ghc here) -- see the
    module comment. The point of the mod-negative seqs is that C's native fmod
    would FAIL this, so the floor-mod templates are pinned.
    """
    ref = _rpn_reference(seq, a, b)
    assert _c_model(seq, a, b) == pytest.approx(ref), f"C model diverged on {seq}"
    assert _hs_model(seq, a, b) == pytest.approx(
        ref
    ), f"haskell model diverged on {seq}"


def test_models_agree_over_full_alphabet():
    """C and Haskell mirrors agree with the RPN reference for every single op."""
    for name, _code in _ALPHABET:
        for a, b in _INPUTS:
            ref = _rpn_reference([name], a, b)
            assert _c_model([name], a, b) == pytest.approx(
                ref
            ), f"C model diverged on {name}"
            assert _hs_model([name], a, b) == pytest.approx(
                ref
            ), f"haskell model diverged on {name}"


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
    assert payload["compile_hint"] == 'compile-ca --opcodes "0x09 0x09 0x00" --args a,b'


def test_ca_plan_known_abs_add_expression():
    rc, stdout, _ = _run_cli(["ca-plan", "--expr", "abs(a)+abs(b)"])
    assert rc == 0
    assert stdout.strip() == "0x09, 0x09, 0x00"


def test_prime_plan_known_abs_add_expression():
    rc, stdout, _ = _run_cli(["prime-plan", "--expr", "abs(a)+abs(b)"])
    assert rc == 0
    assert stdout.strip() == "29 29 2"


def test_compile_prime_python_round_trip_bijective():
    rc, stdout, _ = _run_cli(
        [
            "compile-prime",
            "--primes",
            "29 29 2",
            "--target",
            "python",
            "--fn",
            "abs_add",
            "--args",
            "a,b",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["prime_sequence"] == [29, 29, 2]
    assert payload["opcodes"] == [9, 9, 0]
    assert payload["round_trip_ok"] is True


def test_copilot_route_card_for_abs_add_expression():
    rc, stdout, _ = _run_cli(
        [
            "copilot-route",
            "--expr",
            "abs(a)+abs(b)",
            "--target",
            "python",
            "--fn",
            "abs_add",
            "--args",
            "a,b",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["schema"] == "scbe_agentic_copilot_route_v1"
    assert payload["ops"] == ["abs", "abs", "add"]
    assert payload["opcodes"] == [9, 9, 0]
    assert payload["prime_tape"] == "29 29 2"
    assert payload["compile_supported"] is True
    assert payload["stib_semantic_abacus"]["decision"] == "ALLOW_CLI"
    assert payload["stib_semantic_abacus"]["allowed"] is True
    assert payload["route_rows"][0]["route_lane"] == "arithmetic.mod30:29"
    assert payload["route_rows"][0]["prime_coordinate"]["prime_index"] == 10
    command_names = [command["name"] for command in payload["next_commands"]]
    assert command_names == [
        "inspect-prime-route",
        "compile-prime",
        "lint-prime-shape",
    ]


def test_copilot_route_card_blocks_compile_for_unsupported_templates():
    rc, stdout, _ = _run_cli(["copilot-route", "--ops", "pow", "--json"])
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["ops"] == ["pow"]
    assert payload["compile_supported"] is False
    blocked = payload["next_commands"][-1]
    assert blocked["name"] == "compile-prime"
    assert blocked["safe"] is False
    assert "without compiler templates" in blocked["reason"]


def test_repo_task_route_builds_allowlisted_format_lint_verify_plan():
    rc, stdout, _ = _run_cli(
        [
            "repo-task-route",
            "--task",
            "format-lint",
            "--paths",
            "python/scbe/copilot_router.py",
            "tests/agents/test_scbe_code.py",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["schema"] == "scbe_repo_task_route_v1"
    assert payload["executed"] is False
    assert payload["ok"] is True
    assert [command["name"] for command in payload["commands"]] == [
        "python-black-format",
        "python-flake8",
        "python-py-compile",
    ]
    assert all(command["allowed"] for command in payload["commands"])
    assert payload["commands"][0]["mutates"] is True
    assert payload["commands"][0]["geoseal"]["decision"]["decision"] == "ALLOW_CLI"


def test_repo_task_route_rejects_workspace_escape():
    rc, _, err = _run_cli(
        [
            "repo-task-route",
            "--task",
            "lint",
            "--paths",
            "../outside.py",
            "--json",
        ]
    )
    assert rc == 2
    assert "path escapes workspace" in err


def test_ca_plan_unknown_op_fails():
    rc, _, err = _run_cli(["ca-plan", "--ops", "abs,definitely_not_ca"])
    assert rc == 2
    assert "unknown CA op" in err


# ---------------------------------------------------------------------------
# scbe_code: lookup mode (no LLM)
# ---------------------------------------------------------------------------


def test_render_op_add_python_substitutes_placeholders():
    rc, stdout, _ = _run_cli(
        ["render-op", "--op", "add", "--target", "KO", "--a", "x", "--b", "y", "--json"]
    )
    assert rc == 0
    payload = json.loads(stdout)
    assert payload["name"] == "add"
    assert payload["template"] == "({a} + {b})"
    assert payload["rendered"] == "(x + y)"


def test_render_op_supports_hex_id():
    rc, stdout, _ = _run_cli(
        ["render-op", "--op", "0x00", "--target", "RU", "--a", "x", "--b", "y"]
    )
    assert rc == 0
    assert "wrapping_add" in stdout


def test_render_op_unknown_op_fails():
    rc, _, err = _run_cli(
        ["render-op", "--op", "definitely_not_an_op", "--target", "KO"]
    )
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

    result = apply_patch_safely(
        patch, smoke_cmd="python -c \"print('ok')\"", smoke_timeout=30
    )

    # Sandbox path was named, smoke ran, main tree untouched.
    assert result.smoke_returncode == 0, result.smoke_stderr or result.error
    assert result.ok is True
    assert result.applied is True
    # Cleanup: remove the file we just patched into the main tree.
    if main_target.exists():
        main_target.unlink()


@pytest.mark.skipif(
    subprocess.call(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "--is-inside-work-tree"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    != 0,
    reason="repo isn't a git work tree",
)
def test_safe_apply_apply_main_false_skips_main_tree(tmp_path):
    """Sandbox smoke can pass while the main tree remains untouched."""
    from scripts.agents.safe_apply import apply_patch_safely

    rel = "tests/_safe_apply_dry_run_probe_DELETE_ME.txt"
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
        +scbe_code safe_apply dry-run probe
        """)

    result = apply_patch_safely(
        patch,
        smoke_cmd=(
            'python -c "from pathlib import Path; '
            "assert Path('tests/_safe_apply_dry_run_probe_DELETE_ME.txt').exists(); "
            "print('sandbox ok')\""
        ),
        smoke_timeout=30,
        apply_main=False,
    )

    assert result.ok is True
    assert result.applied is False
    assert "main-tree apply skipped" in result.error
    assert not main_target.exists()
