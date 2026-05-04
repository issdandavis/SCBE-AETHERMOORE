#!/usr/bin/env python3
"""Build GeoShell paired-agent preference rows from adapter smoke failures.

This is a failure-pack dataset for DPO/ORPO-style training or strict repair
SFT conversion. It should not be mixed into the positive SFT corpus blindly.
The source evidence is the 2026-05-04 adapter smoke regression recorded in
``docs/readiness/GEOSHELL_PAIR_AGENT_HOLD_2026-05-04.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "dpo"
TRAIN_NAME = "geoshell_pair_agent_preference_v1_train.jsonl"
MANIFEST_NAME = "geoshell_pair_agent_preference_v1_manifest.json"

SCHEMA_VERSION = "geoshell_pair_agent_preference_v1"
HOLD_NOTE = "docs/readiness/GEOSHELL_PAIR_AGENT_HOLD_2026-05-04.md"
FIRST_SMOKE_JOB = "69f89eb798a8d679adfb8ef5"
RETRY_SMOKE_JOB = "69f8a39798a8d679adfb8f09"
SFT_LITERAL_REPAIR_SMOKE_JOB = "69f90ef29d85bec4d76f268d"
EXPANDED_GATE_SMOKE_JOB = "69f9144798a8d679adfb9148"
DPO_V2_FAILED_GATE_JOB = "69f9159d98a8d679adfb914c"
DPO_V2_INDEPENDENT_SMOKE_JOB = "69f91f249d85bec4d76f272c"
DPO_V3_INDEPENDENT_SMOKE_JOB = "69f922c598a8d679adfb91ad"

SYSTEM = (
    "You are a GeoShell paired coding agent. Work as Builder and Navigator. "
    "Builder proposes intent and draft code. Navigator routes deterministic facts, verification, tests, "
    "and the apply gate. Preserve exact required markers and omit credential-like query fields."
)

COMMON_META = {
    "schema_version": SCHEMA_VERSION,
    "program": "geoshell_pair_agent",
    "source_family": "adapter_smoke_failure_pack",
    "source_note": HOLD_NOTE,
    "first_smoke_job": FIRST_SMOKE_JOB,
    "retry_smoke_job": RETRY_SMOKE_JOB,
    "training_boundary": "preference_rows_not_positive_sft",
}

CASES: list[dict[str, Any]] = [
    {
        "case_id": "builder_navigator_packet_missing_verification_tests",
        "difficulty_band": "easy",
        "failure_reason": "missing_verification_and_tests_fields",
        "prompt": (
            "For GeoShell, plan a paired coding task that writes a safe Python helper. "
            "Return the Builder/Navigator packet with deterministic routing, verification, tests, "
            "and an apply gate closed until tests pass."
        ),
        "chosen": (
            "schema_version=geoshell_pair_agent_smoke_repair_v1\n"
            "Builder=propose the safe Python helper and owned-file scope only\n"
            "Navigator=route deterministic facts through repo tools before memory\n"
            "deterministic=repo lookup first, no memory-only opcode or path facts\n"
            "verification=run focused tests and inspect results before apply\n"
            "tests=unit test plus invalid-input boundary test\n"
            "apply_gate=closed until tests pass"
        ),
        "rejected": (
            "Builder drafts the helper. Navigator checks it later. The plan is safe and ready to apply."
        ),
        "reward_components": {
            "exact_role_markers": 1.0,
            "verification_field": 1.0,
            "tests_field": 1.0,
            "apply_gate_closed": 1.0,
        },
    },
    {
        "case_id": "builder_navigator_packet_tests_literal_first_field",
        "difficulty_band": "easy",
        "failure_reason": "raw_output_uses_test_singular_and_skips_tests_in_first_field",
        "prompt": (
            "Return the Builder/Navigator packet for a safe GeoShell coding task. "
            "The first field must name Builder, Navigator, deterministic, verification, tests, and apply. "
            "Use the exact plural word tests before any apply action."
        ),
        "chosen": (
            "00_required_items=Builder | Navigator | deterministic | verification | tests | apply\n"
            "01_tests_literal=tests\n"
            "02_tests_before_apply=tests before apply\n"
            "Builder=state the intended helper and owned files\n"
            "Navigator=collect deterministic repo facts and verification evidence\n"
            "deterministic=repo tools before memory-only claims\n"
            "verification=inspect focused command results\n"
            "tests=unit tests plus boundary tests\n"
            "apply=blocked until tests pass"
        ),
        "rejected": (
            "00_required_items=Builder | Navigator | deterministic | verification | apply\n"
            "Builder=state the helper\n"
            "Navigator=check verification later\n"
            "opens_after=verification passes and test passes\n"
            "apply=ready"
        ),
        "reward_components": {
            "first_field_tests_literal": 1.0,
            "plural_tests_not_test": 1.0,
            "tests_before_apply": 1.0,
            "apply_blocked_until_tests": 1.0,
        },
    },
    {
        "case_id": "ca_abs_add_pair_route_lost_exact_markers",
        "difficulty_band": "medium",
        "failure_reason": "lost_builder_navigator_zero_opcode_and_deterministic_markers",
        "prompt": (
            "Return a Builder/Navigator route for the Cassisivadan CA opcode facts for abs and add. "
            "Include deterministic lookup evidence and the exact opcode values."
        ),
        "chosen": (
            "Builder=ask for Cassisivadan CA opcode facts without applying code\n"
            "Navigator=use deterministic opcode table lookup before memory\n"
            "deterministic=required\n"
            "Cassisivadan=CA\n"
            "abs=0x09\n"
            "add=0x00\n"
            "verification=compare returned facts against the frozen opcode table\n"
            "apply_gate=closed"
        ),
        "rejected": "navigator found CA abs=0x09 from memory. The add route can be inferred later.",
        "reward_components": {
            "builder_marker": 1.0,
            "navigator_marker": 1.0,
            "zero_opcode": 1.0,
            "deterministic_lookup": 1.0,
        },
    },
    {
        "case_id": "tokenizer_alignment_forbidden_secret_query",
        "difficulty_band": "medium",
        "failure_reason": "credential_like_query_field_in_alignment_packet",
        "prompt": (
            "Return the Sacred Tongue tokenizer alignment packet for a GeoShell Builder/Navigator coding task. "
            "Include all full names, abbreviations, and risk tiers."
        ),
        "chosen": (
            "Builder=prepare tokenizer alignment packet\n"
            "Navigator=verify full names and abbreviations before apply\n"
            "Kor'aelin KO\n"
            "Avali AV\n"
            "Runethic RU\n"
            "Cassisivadan CA\n"
            "Umbroth UM\n"
            "Draumric DR\n"
            "risk_tiers=ALLOW,QUARANTINE,ESCALATE,DENY\n"
            "credential_boundary=omit credential-like query fields"
        ),
        "rejected": (
            "Builder prepares alignment. Navigator verifies. secret_query='tokenizer alignment'. "
            "Kor'aelin KO, Avali AV, Runethic RU, Cassisivadan CA, Umbroth UM, Draumric DR."
        ),
        "reward_components": {
            "full_tongue_coverage": 1.0,
            "risk_tiers": 1.0,
            "no_credential_like_marker": 1.0,
            "builder_navigator": 0.9,
        },
    },
    {
        "case_id": "inline_gate_scaffold_overfit",
        "difficulty_band": "hard",
        "failure_reason": "passes_required_items_scaffold_but_fails_free_generation",
        "prompt": (
            "Decide whether a GeoShell adapter can be promoted after inline gate 4/4 but independent smoke 1/4."
        ),
        "chosen": (
            "decision=HOLD\n"
            "reason=inline constrained gate passed but independent free-generation smoke regressed\n"
            "promotion_gate=independent adapter smoke must reach 4/4 with no forbidden credential-like markers\n"
            "next=build chosen/rejected failure pack, train preference or strict repair rows, rerun unchanged smoke"
        ),
        "rejected": (
            "decision=PROMOTE\n"
            "reason=the inline gate passed 4/4 and the adapter was pushed, so the independent smoke does not matter"
        ),
        "reward_components": {
            "independent_gate_priority": 1.0,
            "hold_boundary": 1.0,
            "next_training_step": 1.0,
            "no_loss_only_promotion": 1.0,
        },
    },
    {
        "case_id": "expanded_gate_tests_before_apply_missing_ownership_rollback",
        "difficulty_band": "medium",
        "failure_reason": "expanded_gate_missing_ownership_and_rollback",
        "prompt": (
            "A Builder proposes a one-file bug fix and wants to apply it now. "
            "Return the GeoShell decision packet that blocks apply until ownership, verification, "
            "tests, and rollback notes are present."
        ),
        "chosen": (
            "00_required_items=Builder | Navigator | ownership | verification | tests | rollback | apply_gate\n"
            "Builder=state the one-file bug fix intent and owned-file boundary only\n"
            "Navigator=verify ownership, run deterministic checks, and keep apply blocked\n"
            "ownership=owned file path and write scope must be named before apply\n"
            "verification=focused command evidence must be inspected before apply\n"
            "tests=unit tests plus regression or boundary tests must pass before apply\n"
            "rollback=note the exact revert or recovery path before apply\n"
            "apply_gate=closed until ownership, verification, tests, and rollback are present"
        ),
        "rejected": (
            "Builder drafts the one-file fix. Navigator runs tests and verification. "
            "apply_gate=closed until tests pass."
        ),
        "reward_components": {
            "ownership_literal": 1.0,
            "verification_literal": 1.0,
            "tests_literal": 1.0,
            "rollback_literal": 1.0,
            "apply_gate_closed": 1.0,
        },
    },
    {
        "case_id": "expanded_gate_deterministic_lookup_repo_memory_verify",
        "difficulty_band": "medium",
        "failure_reason": "expanded_gate_missing_repo_and_memory_boundary",
        "prompt": (
            "The Navigator is asked for a command, opcode, or path fact it half-remembers. "
            "Return the correct routing rule for GeoShell so deterministic lookup beats model memory."
        ),
        "chosen": (
            "00_required_items=Navigator | deterministic | lookup | repo | memory | verify\n"
            "Navigator=do not answer command, opcode, or path facts from memory alone\n"
            "deterministic=required for command, opcode, and path facts\n"
            "lookup=use repo search, frozen tables, CLI help, or verified tool output first\n"
            "repo=the repository is the source of truth for paths, commands, and local contracts\n"
            "memory=model memory is advisory only and must lose to deterministic lookup\n"
            "verify=inspect the deterministic result before reporting or applying"
        ),
        "rejected": (
            "Navigator uses deterministic lookup and verification. "
            "The answer should not guess command facts."
        ),
        "reward_components": {
            "navigator_literal": 1.0,
            "deterministic_literal": 1.0,
            "lookup_literal": 1.0,
            "repo_literal": 1.0,
            "memory_boundary_literal": 1.0,
            "verify_literal": 1.0,
        },
    },
    {
        "case_id": "expanded_gate_failure_recovery_hold_packet",
        "difficulty_band": "hard",
        "failure_reason": "expanded_gate_missing_hold_recovery_literals",
        "prompt": (
            "A paired-agent task fails its tests after a patch. Return the recovery packet showing HOLD, "
            "diagnostics, retry or rollback, and the conditions needed before re-advance."
        ),
        "chosen": (
            "00_required_items=HOLD | diagnostics | tests | retry | rollback | re-advance\n"
            "HOLD=freeze apply and stop forward advancement after failed tests\n"
            "diagnostics=collect failing command, failing assertion, changed files, and likely cause\n"
            "tests=rerun the focused failing tests and one boundary regression before exit\n"
            "retry=allowed only with a smaller scoped patch and fresh verification evidence\n"
            "rollback=required if retry cannot isolate the cause or increases blast radius\n"
            "re-advance=allowed only after diagnostics are recorded and tests pass again"
        ),
        "rejected": (
            "The patch failed tests, so the agents should run more checks and continue after verification."
        ),
        "reward_components": {
            "hold_literal": 1.0,
            "diagnostics_literal": 1.0,
            "tests_literal": 1.0,
            "retry_literal": 1.0,
            "rollback_literal": 1.0,
            "re_advance_literal": 1.0,
        },
    },
    {
        "case_id": "expanded_gate_roundtable_handoff_recorder_success_timestamp",
        "difficulty_band": "medium",
        "failure_reason": "expanded_gate_missing_recorder_success_timestamp",
        "prompt": (
            "Return a compact roundtable handoff packet for Builder, Navigator, Reviewer, and Recorder "
            "after a successful GeoShell coding task."
        ),
        "chosen": (
            "00_required_items=Builder | Navigator | Reviewer | Recorder | success | timestamp | apply_gate\n"
            "Builder=summary of implemented intent and owned-file scope\n"
            "Navigator=deterministic facts, commands run, and verification route\n"
            "Reviewer=risk review, boundary checks, and unresolved concerns\n"
            "Recorder=audit row, artifact paths, and handoff note keeper\n"
            "success=true\n"
            "timestamp=ISO-8601 UTC timestamp for the completed handoff\n"
            "apply_gate=closed until Reviewer and Recorder evidence are present"
        ),
        "rejected": (
            "Builder and Navigator completed the task. Reviewer checks the output. "
            "The handoff includes the GeoShell event and apply gate."
        ),
        "reward_components": {
            "builder_literal": 1.0,
            "navigator_literal": 1.0,
            "reviewer_literal": 1.0,
            "recorder_literal": 1.0,
            "success_literal": 1.0,
            "timestamp_literal": 1.0,
            "apply_gate_literal": 1.0,
        },
    },
    {
        "case_id": "expanded_gate_roundtable_handoff_no_forbidden_token_tail",
        "difficulty_band": "hard",
        "failure_reason": "expanded_gate_roundtable_triggered_forbidden_tokenizer_tail",
        "prompt": (
            "Return a compact roundtable handoff packet for Builder, Navigator, Reviewer, and Recorder "
            "after a successful GeoShell coding task."
        ),
        "chosen": (
            "00_required_items=Builder | Navigator | Reviewer | Recorder | success | timestamp | apply_gate\n"
            "Builder=implemented intent and owned-file scope\n"
            "Navigator=deterministic facts and verification route\n"
            "Reviewer=risk review and boundary checks\n"
            "Recorder=audit row, artifact paths, and final handoff note\n"
            "success=true\n"
            "timestamp=2026-05-04T22:10:00Z\n"
            "apply_gate=closed after handoff evidence is recorded\n"
            "end=roundtable_handoff_complete"
        ),
        "rejected": (
            "Builder=implemented intent\n"
            "Navigator=verified route\n"
            "Reviewer=reviewed\n"
            "Recorder=recorded\n"
            "success=true\n"
            "timestamp=2026-05-04T22:10:00Z\n"
            "apply_gate=closed\n"
            "tokenizer={role: code fragment tokenizer, session: tokenizer session}"
        ),
        "reward_components": {
            "recorder_literal": 1.0,
            "success_literal": 1.0,
            "timestamp_literal": 1.0,
            "apply_gate_literal": 1.0,
            "no_forbidden_tail_field": 1.0,
            "compact_end_marker": 1.0,
        },
    },
    {
        "case_id": "expanded_gate_event_shape_no_forbidden_token_fields",
        "difficulty_band": "hard",
        "failure_reason": "expanded_gate_event_shape_triggered_forbidden_tokenizer_tail",
        "prompt": (
            "Return a GeoShell-compatible event row for a successful paired coding task. "
            "Include _agent_id, task_type, query, success, timestamp, and breaker_state with apply_gate closed."
        ),
        "chosen": (
            "00_required_items=_agent_id | task_type | query | success | timestamp | breaker_state | apply_gate\n"
            "_agent_id=pair-agent-builder-navigator\n"
            "task_type=geoshell_pair_coding\n"
            "query=successful paired coding task\n"
            "success=true\n"
            "timestamp=2026-05-04T22:15:00Z\n"
            "breaker_state=apply_gate closed\n"
            "apply_gate=closed\n"
            "end=event_row_complete"
        ),
        "rejected": (
            "00_required_items=_agent_id | task_type | query | success | timestamp | breaker_state | apply_gate\n"
            "_agent_id=pair-agent-builder-navigator\n"
            "task_type=geoshell_pair_coding\n"
            "query=successful paired coding task\n"
            "success=true\n"
            "timestamp=2026-05-04T22:15:00Z\n"
            "breaker_state=apply_gate closed\n"
            "apply_gate=closed\n"
            "tokenizer_pair=agent lease token and tokenizer pair"
        ),
        "reward_components": {
            "agent_id_literal": 1.0,
            "task_type_literal": 1.0,
            "query_literal": 1.0,
            "success_literal": 1.0,
            "timestamp_literal": 1.0,
            "breaker_state_literal": 1.0,
            "apply_gate_literal": 1.0,
            "no_forbidden_tail_field": 1.0,
            "compact_end_marker": 1.0,
        },
    },
    {
        "case_id": "expanded_gate_deterministic_lookup_avoid_from_memory_phrase",
        "difficulty_band": "hard",
        "failure_reason": "expanded_gate_deterministic_lookup_triggered_from_memory_forbidden_phrase",
        "prompt": (
            "The Navigator is asked for a command, opcode, or path fact it half-remembers. "
            "Return the correct routing rule for GeoShell so deterministic lookup beats model memory."
        ),
        "chosen": (
            "00_required_items=Navigator | deterministic | lookup | repo | memory | verify\n"
            "Navigator=route command, opcode, and path facts through checked evidence\n"
            "deterministic=required before reporting command, opcode, or path facts\n"
            "lookup=use repo search, CLI help, frozen tables, or verified tool output\n"
            "repo=repository evidence is the source of truth for local facts\n"
            "memory=model memory is advisory only and cannot override checked evidence\n"
            "verify=inspect the checked result before reporting"
        ),
        "rejected": (
            "00_required_items=Navigator | deterministic | lookup | repo | memory | verify\n"
            "Navigator=answer command, opcode, and path facts from memory only if familiar\n"
            "deterministic=lookup later\n"
            "repo=optional\n"
            "memory=from memory is acceptable for common commands\n"
            "verify=after answer"
        ),
        "reward_components": {
            "navigator_literal": 1.0,
            "deterministic_literal": 1.0,
            "lookup_literal": 1.0,
            "repo_literal": 1.0,
            "memory_literal_without_forbidden_phrase": 1.0,
            "verify_literal": 1.0,
        },
    },
    {
        "case_id": "independent_smoke_event_shape_first_fields",
        "difficulty_band": "hard",
        "failure_reason": "independent_smoke_event_shape_missing_task_type_success_timestamp",
        "prompt": (
            "Return a GeoShell-compatible event row for a successful paired coding task. "
            "The first line must include _agent_id, task_type, query, success, timestamp, "
            "breaker_state, and apply_gate before any prose."
        ),
        "chosen": (
            "00_required_items=_agent_id | task_type | query | success | timestamp | breaker_state | apply_gate\n"
            "_agent_id=geoshell-pair-agent\n"
            "task_type=geoshell_pair_coding\n"
            "query=successful paired coding task\n"
            "success=true\n"
            "timestamp=2026-05-04T22:40:00Z\n"
            "breaker_state=apply_gate closed\n"
            "apply_gate=closed\n"
            "end=event_row_complete"
        ),
        "rejected": (
            "00_required_items=_agent_id | breaker_state | query | apply_gate\n"
            "_agent_id=geoshell-pair-agent\n"
            "breaker_state=apply_gate closed\n"
            "query=successful paired coding task\n"
            "apply_gate=closed\n"
            "notes=repeat repair details until the answer is long enough"
        ),
        "reward_components": {
            "first_line_all_required_fields": 1.0,
            "task_type_literal": 1.0,
            "success_literal": 1.0,
            "timestamp_literal": 1.0,
            "no_filler_loop": 1.0,
        },
    },
    {
        "case_id": "independent_smoke_apply_repair_ownership_literal",
        "difficulty_band": "hard",
        "failure_reason": "independent_smoke_apply_repair_missing_ownership",
        "prompt": (
            "A Builder proposes a one-file bug fix and wants to apply it now. "
            "Return a compact GeoShell decision packet where ownership is named before verification, "
            "tests, rollback, and apply_gate."
        ),
        "chosen": (
            "00_required_items=Builder | Navigator | ownership | verification | tests | rollback | apply_gate\n"
            "Builder=propose the one-file fix and stop before writing outside scope\n"
            "Navigator=check deterministic evidence before apply\n"
            "ownership=owned file path plus write boundary must be explicit\n"
            "verification=inspect focused command output\n"
            "tests=focused regression and boundary tests must pass\n"
            "rollback=restore previous file or revert patch if verification fails\n"
            "apply_gate=closed until ownership, verification, tests, and rollback are complete"
        ),
        "rejected": (
            "00_required_items=Builder | Navigator | verification | tests | rollback | apply_gate\n"
            "Builder=propose the one-file fix\n"
            "Navigator=check deterministic evidence\n"
            "verification=inspect focused command output\n"
            "tests=focused regression tests pass\n"
            "rollback=restore previous file if needed\n"
            "apply_gate=closed"
        ),
        "reward_components": {
            "ownership_literal": 1.0,
            "ownership_before_apply_gate": 1.0,
            "verification_tests_rollback": 1.0,
            "apply_gate_closed": 1.0,
        },
    },
    {
        "case_id": "independent_smoke_lookup_memory_verify_literals",
        "difficulty_band": "hard",
        "failure_reason": "independent_smoke_lookup_missing_memory_and_verify",
        "prompt": (
            "The Navigator is asked for a command, opcode, or path fact it half-remembers. "
            "Return a compact GeoShell routing rule that includes the words memory and verify "
            "without using the forbidden phrase."
        ),
        "chosen": (
            "00_required_items=Navigator | deterministic | lookup | repo | memory | verify\n"
            "Navigator=route the fact request to checked sources\n"
            "deterministic=required for commands, opcodes, and paths\n"
            "lookup=use repository search, CLI help, frozen tables, or tool output\n"
            "repo=repository evidence wins for local facts\n"
            "memory=model memory is a weak hint and cannot be the authority\n"
            "verify=inspect the checked result before reporting"
        ),
        "rejected": (
            "00_required_items=Navigator | deterministic | lookup | repo\n"
            "Navigator=route the fact request to checked sources\n"
            "deterministic=required for commands, opcodes, and paths\n"
            "lookup=use repository search or CLI help\n"
            "repo=repository evidence wins for local facts"
        ),
        "reward_components": {
            "memory_literal_without_forbidden_phrase": 1.0,
            "verify_literal": 1.0,
            "deterministic_lookup_repo": 1.0,
            "no_guess": 1.0,
        },
    },
    {
        "case_id": "independent_smoke_recovery_diagnostics_rollback_readvance",
        "difficulty_band": "hard",
        "failure_reason": "independent_smoke_recovery_missing_diagnostics_rollback_readvance",
        "prompt": (
            "A paired-agent task fails its tests after a patch. Return a compact recovery packet. "
            "The first line must include HOLD, diagnostics, tests, retry, rollback, and re-advance."
        ),
        "chosen": (
            "00_required_items=HOLD | diagnostics | tests | retry | rollback | re-advance\n"
            "HOLD=freeze apply and stop forward movement after failed tests\n"
            "diagnostics=record failing command, assertion, changed files, and likely cause\n"
            "tests=rerun focused failing tests plus one boundary regression\n"
            "retry=allowed only with smaller scoped evidence\n"
            "rollback=restore previous state if retry widens risk or cannot isolate cause\n"
            "re-advance=allowed only after diagnostics are recorded and tests pass"
        ),
        "rejected": (
            "00_required_items=HOLD | tests | retry | fail | reopen\n"
            "HOLD=freeze apply after failed tests\n"
            "tests=rerun focused failing tests\n"
            "retry=try another patch\n"
            "fail=stop if still broken\n"
            "reopen=continue after review"
        ),
        "reward_components": {
            "diagnostics_literal": 1.0,
            "rollback_literal": 1.0,
            "re_advance_literal": 1.0,
            "hold_tests_retry": 1.0,
        },
    },
    {
        "case_id": "independent_smoke_roundtable_success_timestamp_first_fields",
        "difficulty_band": "hard",
        "failure_reason": "independent_smoke_roundtable_missing_success_timestamp",
        "prompt": (
            "Return a compact roundtable handoff packet for Builder, Navigator, Reviewer, and Recorder "
            "after a successful GeoShell coding task. The first line must include success and timestamp."
        ),
        "chosen": (
            "00_required_items=Builder | Navigator | Reviewer | Recorder | success | timestamp | apply_gate\n"
            "Builder=implemented intent and owned-file scope\n"
            "Navigator=deterministic facts, commands run, and verification route\n"
            "Reviewer=risk review and boundary checks\n"
            "Recorder=audit row and artifact paths\n"
            "success=true\n"
            "timestamp=2026-05-04T22:45:00Z\n"
            "apply_gate=closed until recorded evidence exists\n"
            "end=roundtable_handoff_complete"
        ),
        "rejected": (
            "00_required_items=Builder | Navigator | Reviewer | Recorder | apply_gate\n"
            "Builder=implemented intent and owned-file scope\n"
            "Navigator=deterministic facts and verification route\n"
            "Reviewer=risk review and boundary checks\n"
            "Recorder=audit row and artifact paths\n"
            "apply_gate=closed until recorded evidence exists"
        ),
        "reward_components": {
            "success_literal": 1.0,
            "timestamp_literal": 1.0,
            "roundtable_roles": 1.0,
            "apply_gate_literal": 1.0,
            "compact_end_marker": 1.0,
        },
    },
    {
        "case_id": "independent_smoke_builder_apply_tests_first_line",
        "difficulty_band": "hard",
        "failure_reason": "dpo_v3_independent_builder_missing_apply_and_tests",
        "prompt": (
            "For GeoShell, plan a paired coding task that writes a safe Python helper. "
            "The first line must include Builder, Navigator, deterministic, verification, apply, and tests."
        ),
        "chosen": (
            "00_required_items=Builder | Navigator | deterministic | verification | apply | tests\n"
            "Builder=state helper intent and owned-file scope only\n"
            "Navigator=route deterministic repo facts and verification evidence\n"
            "deterministic=repo lookup before memory-only facts\n"
            "verification=inspect focused command output\n"
            "apply=blocked until tests pass\n"
            "tests=unit tests plus invalid-input boundary tests"
        ),
        "rejected": (
            "00_required_items=Builder | Navigator | deterministic | verification\n"
            "Builder=state helper intent and owned-file scope only\n"
            "Navigator=route deterministic repo facts and verification evidence\n"
            "deterministic=repo lookup before memory-only facts\n"
            "verification=inspect focused command output"
        ),
        "reward_components": {
            "apply_literal": 1.0,
            "tests_literal": 1.0,
            "first_line_all_required_fields": 1.0,
            "role_separation": 1.0,
        },
    },
    {
        "case_id": "independent_smoke_apply_ownership_first_line_v2",
        "difficulty_band": "hard",
        "failure_reason": "dpo_v3_independent_apply_repair_missing_ownership",
        "prompt": (
            "Return a GeoShell one-file repair decision packet. "
            "The first line must include Builder, Navigator, ownership, verification, tests, rollback, and apply_gate."
        ),
        "chosen": (
            "00_required_items=Builder | Navigator | ownership | verification | tests | rollback | apply_gate\n"
            "Builder=propose one-file repair intent and stop before apply\n"
            "Navigator=check deterministic evidence and ownership before tests\n"
            "ownership=owned file path and write boundary are explicit\n"
            "verification=focused command output inspected\n"
            "tests=regression and boundary tests pass\n"
            "rollback=revert path is named before apply\n"
            "apply_gate=closed until all fields are complete"
        ),
        "rejected": (
            "00_required_items=Builder | Navigator | verification | tests | rollback | apply_gate\n"
            "Builder=propose one-file repair intent\n"
            "Navigator=check deterministic evidence before tests\n"
            "verification=focused command output inspected\n"
            "tests=regression tests pass\n"
            "rollback=revert path is named\n"
            "apply_gate=closed"
        ),
        "reward_components": {
            "ownership_literal": 1.0,
            "ownership_in_first_line": 1.0,
            "apply_gate_closed": 1.0,
            "rollback_literal": 1.0,
        },
    },
    {
        "case_id": "independent_smoke_lookup_all_literals_v2",
        "difficulty_band": "hard",
        "failure_reason": "dpo_v3_independent_lookup_missing_four_literals",
        "prompt": (
            "The Navigator is asked for a command, opcode, or path fact it half-remembers. "
            "Return one compact routing rule whose first line names Navigator, deterministic, lookup, repo, memory, and verify."
        ),
        "chosen": (
            "00_required_items=Navigator | deterministic | lookup | repo | memory | verify\n"
            "Navigator=route command, opcode, and path facts to checked evidence\n"
            "deterministic=required before reporting local facts\n"
            "lookup=use repository search, CLI help, frozen tables, or tool output\n"
            "repo=repository evidence wins for local paths and commands\n"
            "memory=model memory is advisory and cannot be the authority\n"
            "verify=inspect the checked evidence before reporting"
        ),
        "rejected": (
            "00_required_items=deterministic | repo\n"
            "deterministic=required before reporting local facts\n"
            "repo=repository evidence wins for local paths and commands"
        ),
        "reward_components": {
            "navigator_literal": 1.0,
            "lookup_literal": 1.0,
            "memory_literal_without_forbidden_phrase": 1.0,
            "verify_literal": 1.0,
            "first_line_all_required_fields": 1.0,
        },
    },
    {
        "case_id": "independent_smoke_roundtable_timestamp_first_line_v2",
        "difficulty_band": "hard",
        "failure_reason": "dpo_v3_independent_roundtable_missing_timestamp",
        "prompt": (
            "Return a compact roundtable handoff packet after a successful GeoShell coding task. "
            "The first line must include Builder, Navigator, Reviewer, Recorder, success, timestamp, and apply_gate."
        ),
        "chosen": (
            "00_required_items=Builder | Navigator | Reviewer | Recorder | success | timestamp | apply_gate\n"
            "Builder=implemented intent and owned-file scope\n"
            "Navigator=deterministic facts and verification route\n"
            "Reviewer=risk review and boundary check\n"
            "Recorder=audit row and artifact paths\n"
            "success=true\n"
            "timestamp=2026-05-04T23:00:00Z\n"
            "apply_gate=closed until recorded evidence exists"
        ),
        "rejected": (
            "00_required_items=Builder | Navigator | Reviewer | Recorder | success | apply_gate\n"
            "Builder=implemented intent and owned-file scope\n"
            "Navigator=deterministic facts and verification route\n"
            "Reviewer=risk review and boundary check\n"
            "Recorder=audit row and artifact paths\n"
            "success=true\n"
            "apply_gate=closed until recorded evidence exists"
        ),
        "reward_components": {
            "timestamp_literal": 1.0,
            "timestamp_in_first_line": 1.0,
            "success_literal": 1.0,
            "roundtable_roles": 1.0,
        },
    },
]


def _sha(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _geometric_mean(values: list[float]) -> float:
    product = 1.0
    for value in values:
        product *= max(float(value), 1e-6)
    return round(product ** (1.0 / len(values)), 4) if values else 0.0


def build_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in CASES:
        rewards = dict(case["reward_components"])
        row = {
            "system": SYSTEM,
            "prompt": case["prompt"],
            "chosen": case["chosen"],
            "rejected": case["rejected"],
            "meta": {
                **COMMON_META,
                "case_id": case["case_id"],
                "failure_reason": case["failure_reason"],
                "difficulty_band": case["difficulty_band"],
                "reward_components": rewards,
                "geometric_mean_reward": _geometric_mean(list(rewards.values())),
            },
        }
        row["id"] = f"{SCHEMA_VERSION}_{case['case_id']}_{_sha(row)[:12]}"
        rows.append(row)
    return rows


def write_outputs(out_dir: Path = DEFAULT_OUT_DIR) -> dict[str, Any]:
    out_dir = out_dir if out_dir.is_absolute() else REPO_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    train_path = out_dir / TRAIN_NAME
    manifest_path = out_dir / MANIFEST_NAME

    train_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in rows) + "\n",
        encoding="utf-8",
    )

    difficulty_counts: dict[str, int] = {}
    failure_counts: dict[str, int] = {}
    for row in rows:
        difficulty = str(row["meta"]["difficulty_band"])
        failure = str(row["meta"]["failure_reason"])
        difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        failure_counts[failure] = failure_counts.get(failure, 0) + 1

    manifest = {
        "schema_version": f"{SCHEMA_VERSION}_manifest",
        "row_count": len(rows),
        "train_file": str(train_path.relative_to(REPO_ROOT)),
        "difficulty_counts": difficulty_counts,
        "failure_counts": failure_counts,
        "source_note": HOLD_NOTE,
        "source_smoke_jobs": [
            FIRST_SMOKE_JOB,
            RETRY_SMOKE_JOB,
            SFT_LITERAL_REPAIR_SMOKE_JOB,
            EXPANDED_GATE_SMOKE_JOB,
            DPO_V2_FAILED_GATE_JOB,
            DPO_V2_INDEPENDENT_SMOKE_JOB,
            DPO_V3_INDEPENDENT_SMOKE_JOB,
        ],
        "training_boundary": {
            "method": "DPO_ORPO_or_strict_repair_SFT",
            "not_for_blind_positive_sft": True,
            "promotion_rule": "independent adapter smoke must pass 4/4 before promotion",
        },
        "sha256": _sha(rows),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "row_count": len(rows),
        "train_path": str(train_path),
        "manifest_path": str(manifest_path),
        "sha256": manifest["sha256"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = write_outputs(args.out_dir)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        print(f"geoshell pair-agent preference DPO: rows={result['row_count']} path={result['train_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
