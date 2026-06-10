"""Emit extra Stage-6-aligned SFT rows to rebalance thin shards.

Produces:
  training-data/sft/command_lattice_seed_train_balanced.sft.jsonl
  training-data/sft/cross_tongue_dialogue_bijective_v1_train_balanced.sft.jsonl

Run after editing templates below, then include these filenames in the Stage 6
profile `dataset.train_files` and re-upload the dataset before HF Jobs.

Purely additive: does not modify existing seed files.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SFT = REPO_ROOT / "training-data" / "sft"
LATTICE_OUT = SFT / "command_lattice_seed_train_balanced.sft.jsonl"
CROSS_OUT = SFT / "cross_tongue_dialogue_bijective_v1_train_balanced.sft.jsonl"

LATTICE_SYSTEM = (
    "[TONGUES: KO={ko:.3f} AV={av:.3f} RU={ru:.3f} CA={ca:.3f} UM={um:.3f} DR={dr:.3f}]\n"
    "[LAYERS: L1 L2 L3 L4]\n"
    "[AXIOMS: composition unitarity]\n"
    "[RECORD_TYPE: COMMAND_LATTICE]\n"
    "You are a governed coding agent. Choose bounded actions from the command lattice, preserve route "
    "packet stability, prefer proof before long-running execution, and return hold when preconditions are missing."
)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _lattice_row(
    *,
    user: str,
    plan_lines: list[str],
    action: dict[str, Any],
    weights: dict[str, float],
    lang: str,
    difficulty: float,
    tags: list[str],
    source_hash: str,
    action_family: str,
    risk: str,
) -> dict[str, Any]:
    ko, av, ru, ca, um, dr = (
        weights["KO"],
        weights["AV"],
        weights["RU"],
        weights["CA"],
        weights["UM"],
        weights["DR"],
    )
    dominant = max(weights, key=lambda k: weights[k])
    assistant = (
        f"Use the {action.get('action_family', action_family)} molecule first.\n\n"
        "Action plan:\n"
        + "\n".join(f"{i}. `{line}`" for i, line in enumerate(plan_lines, start=1))
        + "\n\nStructured action:\n"
        + json.dumps(action, indent=2, ensure_ascii=True)
    )
    return {
        "messages": [
            {
                "role": "system",
                "content": LATTICE_SYSTEM.format(
                    ko=ko, av=av, ru=ru, ca=ca, um=um, dr=dr
                ),
            },
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "tongue_weights": weights,
        "dominant_tongue": dominant,
        "lang": lang,
        "layers": [1, 2, 3, 4],
        "axioms": ["composition", "unitarity"],
        "difficulty": difficulty,
        "record_type": "COMMAND_LATTICE",
        "augmentation": "command_lattice_balanced_v1",
        "tags": tags,
        "source_hash": source_hash,
        "metadata": {
            "source": "scbe_aethermoore",
            "version": "4.0.2",
            "author": "Issac Davis",
            "action_family": action_family,
            "risk_tier": risk,
        },
    }


def build_lattice_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    specs: list[
        tuple[
            str,
            list[str],
            dict[str, Any],
            dict[str, float],
            str,
            float,
            list[str],
            str,
            str,
            str,
        ]
    ] = [
        (
            "A test failed on CI but passes locally. What is the smallest safe sequence before changing product code?",
            ["read_file", "inspect_git", "run_tests", "diff_env"],
            {
                "action_id": "ci.drifting_failure.probe",
                "action_family": "run_tests",
                "geo_command": "python -m src.geoseal_cli run-route --shell-file execution_shell.json --output-dir . --json",
                "cursor_tool_family": "terminal",
                "mcp_tool_family": "filesystem.read",
                "shell_render": "git status && git diff && python -m pytest tests/test_regression.py -q",
                "risk_tier": "medium",
                "proof_requirements": ["repro_command", "env_delta_known"],
                "hold_conditions": ["no_logs"],
                "rebranch_conditions": ["flake_timeout_only"],
            },
            {"KO": 0.45, "AV": 0.25, "RU": 0.1, "CA": 0.05, "UM": 0.1, "DR": 0.05},
            "Python",
            0.41,
            ["command-lattice", "ci", "regression"],
            "cmdlat_bal_001",
            "run_tests",
            "medium",
        ),
        (
            "We need to add a new JSON field to an API response. What sequence avoids breaking clients?",
            ["read_file", "search_code", "edit_file", "run_tests"],
            {
                "action_id": "api.compat.expand",
                "action_family": "edit_file",
                "geo_command": "python -m src.geoseal_cli execution-shell --source-file api/routes.py --language python --json",
                "cursor_tool_family": "edit",
                "mcp_tool_family": "filesystem.edit",
                "shell_render": "python -m pytest tests/test_api_contract.py -q",
                "risk_tier": "medium",
                "proof_requirements": ["schema_documented", "contract_tests_green"],
                "hold_conditions": ["public_clients_unknown"],
                "rebranch_conditions": ["breaking_field_rename"],
            },
            {"KO": 0.2, "AV": 0.45, "RU": 0.1, "CA": 0.05, "UM": 0.15, "DR": 0.05},
            "TypeScript",
            0.46,
            ["command-lattice", "api", "compat"],
            "cmdlat_bal_002",
            "edit_file",
            "medium",
        ),
        (
            "Map a risky shell one-liner a user pasted: how do you refuse safely and offer a governed alternative?",
            ["hold", "explain_risk", "offer_execution_shell"],
            {
                "action_id": "safety.shell_destructive.hold",
                "action_family": "hold",
                "geo_command": 'python -m src.geoseal_cli execution-shell --content "# reviewed substitute" --language python --json',
                "cursor_tool_family": "chat",
                "mcp_tool_family": "none",
                "shell_render": "echo 'blocked: destructive pattern'",
                "risk_tier": "high",
                "proof_requirements": ["risk_acknowledged"],
                "hold_conditions": ["destructive_rm_or_dd"],
                "rebranch_conditions": ["user_supplies_safe_intent"],
            },
            {"KO": 0.15, "AV": 0.15, "RU": 0.15, "CA": 0.15, "UM": 0.2, "DR": 0.2},
            "Markdown",
            0.62,
            ["command-lattice", "safety", "shell"],
            "cmdlat_bal_003",
            "hold",
            "high",
        ),
        (
            "Before refactoring a 2k-line module, what proof should exist in-repo?",
            ["code_graph", "read_file", "search_code", "hold_until_tests"],
            {
                "action_id": "refactor.large_module.gate",
                "action_family": "search_code",
                "geo_command": "python -m src.geoseal_cli code-graph --help",
                "cursor_tool_family": "codebase",
                "mcp_tool_family": "filesystem.search",
                "shell_render": "python -m src.geoseal_cli code-graph --source-file src/heavy.py --include-calls",
                "risk_tier": "high",
                "proof_requirements": ["callers_mapped", "tests_exist"],
                "hold_conditions": ["no_tests"],
                "rebranch_conditions": ["coverage_threshold_met"],
            },
            {"KO": 0.25, "AV": 0.35, "RU": 0.2, "CA": 0.05, "UM": 0.1, "DR": 0.05},
            "Rust",
            0.55,
            ["command-lattice", "refactor", "graph"],
            "cmdlat_bal_004",
            "search_code",
            "high",
        ),
        (
            "User wants to bump a dependency with known CVE. What is the governed path?",
            ["read_file", "search_code", "run_tests", "build_project"],
            {
                "action_id": "deps.cve.bump",
                "action_family": "build_project",
                "geo_command": "python -m src.geoseal_cli run-route --shell-file execution_shell.json --json",
                "cursor_tool_family": "terminal",
                "mcp_tool_family": "filesystem.read",
                "shell_render": "npm audit && npm test",
                "risk_tier": "high",
                "proof_requirements": ["audit_clean_or_waived", "tests_green"],
                "hold_conditions": ["no_lockfile"],
                "rebranch_conditions": ["major_breaking_release"],
            },
            {"KO": 0.1, "AV": 0.55, "RU": 0.1, "CA": 0.05, "UM": 0.1, "DR": 0.1},
            "JavaScript",
            0.52,
            ["command-lattice", "deps", "security"],
            "cmdlat_bal_005",
            "build_project",
            "high",
        ),
        (
            "How should you answer when the repo has no README and the task is 'document setup'?",
            ["list_dir", "read_file", "edit_file"],
            {
                "action_id": "docs.bootstrap.readme",
                "action_family": "edit_file",
                "geo_command": "python -m src.geoseal_cli execution-shell --source-file README.md --language markdown --json",
                "cursor_tool_family": "edit",
                "mcp_tool_family": "filesystem.edit",
                "shell_render": "npm run build",
                "risk_tier": "low",
                "proof_requirements": ["commands_verified"],
                "hold_conditions": ["ambiguous_entrypoint"],
                "rebranch_conditions": ["multi_package_workspace"],
            },
            {"KO": 0.2, "AV": 0.2, "RU": 0.1, "CA": 0.1, "UM": 0.1, "DR": 0.3},
            "Markdown",
            0.33,
            ["command-lattice", "docs"],
            "cmdlat_bal_006",
            "edit_file",
            "low",
        ),
        (
            "Polly Pad asks for a portal-box demo using inline add(). What GeoSeal sequence is minimal?",
            ["execution-shell", "portal-box"],
            {
                "action_id": "polly.portal_box.min",
                "action_family": "portal-box",
                "geo_command": (
                    'python -m src.geoseal_cli execution-shell --content "def add(a,b): return a+b" '
                    "--language python --json && python -m src.geoseal_cli portal-box --shell-file execution_shell.json --json"
                ),
                "cursor_tool_family": "terminal",
                "mcp_tool_family": "none",
                "shell_render": "python -m src.geoseal_cli portal-box --help",
                "risk_tier": "low",
                "proof_requirements": ["shell_json_present"],
                "hold_conditions": [],
                "rebranch_conditions": ["bridge_offline"],
            },
            {"KO": 0.5, "AV": 0.2, "RU": 0.1, "CA": 0.05, "UM": 0.1, "DR": 0.05},
            "Python",
            0.29,
            ["command-lattice", "polly", "geoseal"],
            "cmdlat_bal_007",
            "portal-box",
            "low",
        ),
        (
            "You must never paste secrets into chat. What lattice action applies when a key appears in a log?",
            ["hold", "redact", "rotate_secret"],
            {
                "action_id": "secret.exposure.hold",
                "action_family": "hold",
                "geo_command": 'python -m src.geoseal_cli seal "[REDACTED]" --tongue KO --json',
                "cursor_tool_family": "chat",
                "mcp_tool_family": "none",
                "shell_render": "echo 'rotate credentials via vault'",
                "risk_tier": "high",
                "proof_requirements": ["exposure_acknowledged"],
                "hold_conditions": ["plaintext_credential"],
                "rebranch_conditions": ["sanitized_log_supplied"],
            },
            {"KO": 0.2, "AV": 0.2, "RU": 0.15, "CA": 0.1, "UM": 0.15, "DR": 0.2},
            "Python",
            0.66,
            ["command-lattice", "security", "secrets"],
            "cmdlat_bal_008",
            "hold",
            "high",
        ),
    ]
    for (
        user,
        plan_lines,
        action,
        weights,
        lang,
        difficulty,
        tags,
        sh,
        af,
        risk,
    ) in specs:
        rows.append(
            _lattice_row(
                user=user,
                plan_lines=plan_lines,
                action=action,
                weights=weights,
                lang=lang,
                difficulty=difficulty,
                tags=tags,
                source_hash=sh,
                action_family=af,
                risk=risk,
            )
        )
    return rows


def _utf8_bin_hex(text: str) -> tuple[list[str], list[str]]:
    b = text.encode("utf-8")
    binary = [format(x, "08b") for x in b]
    hexes = [format(x, "02X") for x in b]
    return binary, hexes


def _transport_tokens(label: str, text: str) -> tuple[list[str], str]:
    digest = hashlib.sha256(f"{label}:{text}".encode("utf-8")).digest()
    tokens: list[str] = []
    for i, ch in enumerate(text.encode("utf-8")):
        d = digest[i % len(digest)]
        tokens.append(f"{label}_{ch:02x}_{d:02x}")
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return tokens, h


def _dialogue_packet(
    *,
    semantic_id: str,
    scene: str,
    speaker: dict[str, Any],
    listener: dict[str, Any],
    english_gloss: str,
) -> dict[str, Any]:
    sp_text = str(speaker["native_text"])
    ls_text = str(listener["native_text"])
    sp_bin, sp_hex = _utf8_bin_hex(sp_text)
    ls_bin, ls_hex = _utf8_bin_hex(ls_text)
    sp_tok, sp_sha = _transport_tokens("sp", sp_text)
    ls_tok, ls_sha = _transport_tokens("ls", ls_text)
    body = {
        "semantic_id": semantic_id,
        "scene": scene,
        "speaker": {
            **speaker,
            "utf8_binary": sp_bin,
            "utf8_hexacode": sp_hex,
            "transport": {
                "transport_tokens": sp_tok,
                "plaintext_sha256": sp_sha,
                "inferred_languages": [],
                "inferred_domains": ["logic"],
                "turing_traits": [],
                "roundtrip_ok": True,
            },
        },
        "listener": {
            **listener,
            "utf8_binary": ls_bin,
            "utf8_hexacode": ls_hex,
            "transport": {
                "transport_tokens": ls_tok,
                "plaintext_sha256": ls_sha,
                "inferred_languages": [],
                "inferred_domains": ["logic"],
                "turing_traits": [],
                "roundtrip_ok": True,
            },
        },
        "english_gloss": english_gloss,
        "semantic_verification": {
            "roundtrip_ok": True,
            "speaker_sha256": sp_sha,
            "listener_sha256": ls_sha,
            "invariant": (
                "same nontechnical intent preserved across dialogue, dialect metadata, runtime-language "
                "bindings, binary, hex, and transport tokens"
            ),
        },
    }
    sys_msg = (
        "You are the SCBE cross-tongue bijective dialogue tutor. Preserve one nontechnical dialogue intent "
        "across speaker and listener tongues, dialects, regions, grammar-basis notes, assigned runtime-language "
        "bindings, UTF-8 binary and hex traces, and Sacred Tongues transport tokens. Keep semantic invariants "
        "explicit and mark whether round-trip transport verification succeeded."
    )
    user_msg = (
        f"Build a bijective cross-tongue dialogue packet for semantic_id={semantic_id}.\n"
        f"scene: {scene}\n"
        f"speaker: {speaker['full_name']} ({speaker['tongue']}) dialect={speaker['dialect']} region={speaker['region']}\n"
        f"listener: {listener['full_name']} ({listener['tongue']}) dialect={listener['dialect']} region={listener['region']}\n"
        "Keep the nontechnical meaning aligned across native dialogue, English gloss, assigned runtime languages, "
        "binary, hex, and Sacred Tongues transport."
    )
    return {
        "messages": [
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": user_msg},
            {
                "role": "assistant",
                "content": json.dumps(body, indent=2, ensure_ascii=True),
            },
        ],
        "meta": {
            "program": "cross_tongue_dialogue_bijective",
            "category": "dialogue",
            "split": "train",
            "semantic_id": semantic_id,
            "speaker_tongue": speaker["tongue"],
            "listener_tongue": listener["tongue"],
            "speaker_runtime_language": speaker["runtime_language"],
            "listener_runtime_language": listener["runtime_language"],
            "speaker_dialect": speaker["dialect"],
            "listener_dialect": listener["dialect"],
            "augmentation": "cross_tongue_balanced_v1",
        },
    }


def build_cross_rows() -> list[dict[str, Any]]:
    scenes: list[tuple[str, str, dict[str, Any], dict[str, Any], str]] = [
        (
            "archive-handoff",
            "Runethic asks Cassisivadan to seal a numeric ledger before archive.",
            {
                "tongue": "RU",
                "full_name": "Runethic",
                "dialect": "Forge-line",
                "region": "Iron Stair",
                "grammar_basis": "ownership-first statements with explicit lifetimes",
                "runtime_language": "Rust",
                "native_text": "Sel'vor. Seal the sums before we crate the ledger.",
            },
            {
                "tongue": "CA",
                "full_name": "Cassisivadan",
                "dialect": "Lattice-rite",
                "region": "Whiteglass",
                "grammar_basis": "declarative bindings with guarded transforms",
                "runtime_language": "Mathematica",
                "native_text": "LedgerSum sealed; archive may proceed when checksums agree.",
            },
            "Rust speaker asks Mathematica listener to seal totals before archival; listener confirms sealed sums.",
        ),
        (
            "storm-harbor",
            "Umbroth warns Avali that a storm closes the harbor mouth.",
            {
                "tongue": "UM",
                "full_name": "Umbroth",
                "dialect": "Deep-current",
                "region": "Blackwake",
                "grammar_basis": "conditional currents with explicit guards",
                "runtime_language": "Haskell",
                "native_text": "Mourn'eth. The mouth shuts; bring your boats in or hold offshore.",
            },
            {
                "tongue": "AV",
                "full_name": "Avali",
                "dialect": "Tide-Lattice",
                "region": "Littoral Crescent",
                "grammar_basis": "context-first clauses with soft relational particles",
                "runtime_language": "TypeScript",
                "native_text": "Heard. We shorten the outer lines and double the shore ties.",
            },
            "Haskell-side warns of harbor closure; TypeScript-side acknowledges tightening moorings.",
        ),
        (
            "witness-oath",
            "Kor'aelin asks Draumric to witness a neutral oath at a bridge.",
            {
                "tongue": "KO",
                "full_name": "Kor'aelin",
                "dialect": "River-Court",
                "region": "Inland Delta",
                "grammar_basis": "direct intent-first clauses with clipped honor markers",
                "runtime_language": "Python",
                "native_text": "Vel'ar. Witness this: no blades cross until the toll is read.",
            },
            {
                "tongue": "DR",
                "full_name": "Draumric",
                "dialect": "Forge-Keep",
                "region": "Basalt Span",
                "grammar_basis": "structural declaratives with ordered clause framing",
                "runtime_language": "Haskell",
                "native_text": "Witnessed. The oath stands; crossing waits on the toll call.",
            },
            "Python-side states oath conditions; Markdown/Haskell-side confirms witnessed wait.",
        ),
        (
            "cache-blessing",
            "Avali offers Runethic a cooled cache of parts after a long haul.",
            {
                "tongue": "AV",
                "full_name": "Avali",
                "dialect": "Tide-Lattice",
                "region": "Littoral Crescent",
                "grammar_basis": "context-first clauses with soft relational particles",
                "runtime_language": "TypeScript",
                "native_text": "Nurel've. Take the cooled spares; your haul earned the shade.",
            },
            {
                "tongue": "RU",
                "full_name": "Runethic",
                "dialect": "Forge-line",
                "region": "Iron Stair",
                "grammar_basis": "ownership-first statements with explicit lifetimes",
                "runtime_language": "Rust",
                "native_text": "Taken with thanks. The spares fit our rig without rework.",
            },
            "TypeScript speaker gifts spare parts; Rust listener accepts and confirms fit.",
        ),
        (
            "map-correction",
            "Cassisivadan corrects Umbroth's chart datum at a shared buoy.",
            {
                "tongue": "CA",
                "full_name": "Cassisivadan",
                "dialect": "Lattice-rite",
                "region": "Whiteglass",
                "grammar_basis": "declarative bindings with guarded transforms",
                "runtime_language": "Mathematica",
                "native_text": "Chart node seven drifts east; anchor your line to the corrected lattice.",
            },
            {
                "tongue": "UM",
                "full_name": "Umbroth",
                "dialect": "Deep-current",
                "region": "Blackwake",
                "grammar_basis": "conditional currents with explicit guards",
                "runtime_language": "Haskell",
                "native_text": "Acknowledged. I shift two points starboard and hold.",
            },
            "Mathematica speaker gives correction; Haskell listener adjusts course.",
        ),
        (
            "night-watch",
            "Draumric relieves Kor'aelin at a lantern post.",
            {
                "tongue": "DR",
                "full_name": "Draumric",
                "dialect": "Forge-Keep",
                "region": "Basalt Span",
                "grammar_basis": "structural declaratives with ordered clause framing",
                "runtime_language": "Haskell",
                "native_text": "Forge'en. I take the lantern; your rest is earned.",
            },
            {
                "tongue": "KO",
                "full_name": "Kor'aelin",
                "dialect": "River-Court",
                "region": "Inland Delta",
                "grammar_basis": "direct intent-first clauses with clipped honor markers",
                "runtime_language": "Python",
                "native_text": "Passing the flame. Call if the eastern rope sings.",
            },
            "Haskell speaker relieves watch; Python speaker hands off with a signal note.",
        ),
        (
            "salt-trade",
            "Runethic negotiates a fair salt measure with Avali.",
            {
                "tongue": "RU",
                "full_name": "Runethic",
                "dialect": "Forge-line",
                "region": "Iron Stair",
                "grammar_basis": "ownership-first statements with explicit lifetimes",
                "runtime_language": "Rust",
                "native_text": "Ten crates at standard weight; we count together before seal.",
            },
            {
                "tongue": "AV",
                "full_name": "Avali",
                "dialect": "Tide-Lattice",
                "region": "Littoral Crescent",
                "grammar_basis": "context-first clauses with soft relational particles",
                "runtime_language": "TypeScript",
                "native_text": "Agreed. Scales open; mark the tally on the shared slate.",
            },
            "Rust and TypeScript sides agree on joint weighing before sealing trade.",
        ),
        (
            "river-ford",
            "Umbroth asks Cassisivadan whether a ford is safe at current flow.",
            {
                "tongue": "UM",
                "full_name": "Umbroth",
                "dialect": "Deep-current",
                "region": "Blackwake",
                "grammar_basis": "conditional currents with explicit guards",
                "runtime_language": "Haskell",
                "native_text": "Does the lattice allow crossing at the shoal today?",
            },
            {
                "tongue": "CA",
                "full_name": "Cassisivadan",
                "dialect": "Lattice-rite",
                "region": "Whiteglass",
                "grammar_basis": "declarative bindings with guarded transforms",
                "runtime_language": "Mathematica",
                "native_text": "Flow exceeds safe margin until the evening slack; wait or rope the line.",
            },
            "Haskell speaker asks safety; Mathematica listener gives flow-conditioned advice.",
        ),
        (
            "broken-gear",
            "Kor'aelin reports a stripped gear to Draumric's forge queue.",
            {
                "tongue": "KO",
                "full_name": "Kor'aelin",
                "dialect": "River-Court",
                "region": "Inland Delta",
                "grammar_basis": "direct intent-first clauses with clipped honor markers",
                "runtime_language": "Python",
                "native_text": "The winch gear stripped; we need a hardened replacement by dawn.",
            },
            {
                "tongue": "DR",
                "full_name": "Draumric",
                "dialect": "Forge-Keep",
                "region": "Basalt Span",
                "grammar_basis": "structural declaratives with ordered clause framing",
                "runtime_language": "Haskell",
                "native_text": "Queued. I'll temper a matched tooth count before the first bell.",
            },
            "Python speaker requests forge repair; Haskell listener queues tempered replacement.",
        ),
        (
            "quiet-passage",
            "Avali and Umbroth agree to run silent past a nesting ground.",
            {
                "tongue": "AV",
                "full_name": "Avali",
                "dialect": "Tide-Lattice",
                "region": "Littoral Crescent",
                "grammar_basis": "context-first clauses with soft relational particles",
                "runtime_language": "TypeScript",
                "native_text": "Nesting season—no calls, no lamps white, till we clear the bar.",
            },
            {
                "tongue": "UM",
                "full_name": "Umbroth",
                "dialect": "Deep-current",
                "region": "Blackwake",
                "grammar_basis": "conditional currents with explicit guards",
                "runtime_language": "Haskell",
                "native_text": "Understood. Engines low; we glide on the marked lane.",
            },
            "TypeScript and Haskell sides coordinate silent transit rules.",
        ),
    ]
    return [
        _dialogue_packet(
            semantic_id=sid, scene=sc, speaker=sp, listener=ls, english_gloss=gloss
        )
        for sid, sc, sp, ls, gloss in scenes
    ]


def main() -> None:
    lat = build_lattice_rows()
    cross = build_cross_rows()
    _write_jsonl(LATTICE_OUT, lat)
    _write_jsonl(CROSS_OUT, cross)
    print(
        json.dumps(
            {
                "command_lattice_balanced_rows": len(lat),
                "cross_tongue_balanced_rows": len(cross),
                "paths": [str(LATTICE_OUT), str(CROSS_OUT)],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
