# Harness dependency and envelope validation repair — 2026-09-09

The evidence browser now runs from the repository's own copy of the existing
Hydra script. Signed policy evaluation rejects nonfinite resource readings,
invalid constraints and unspecified or unknown risk tiers before allowing an
action. This follows the full-system refusal repair described in
`FULL_SYSTEM_DECISION_REPAIR_20260909.md`.

## Reproduced policy failure

A correctly authenticated fixture envelope requires power >= 40, bandwidth >=
10 and temperature <= 85. Supplying `NaN` for any one of those readings returned
`AUTO_ALLOW`: comparisons with `NaN` are false, so the input bypassed the relevant
floor or ceiling. Positive infinity for power/bandwidth, negative infinity for
temperature, and unspecified/negative risk enum values also returned ALLOW in
the fixture. Protobuf accepts these numeric values; successful decoding does
not establish semantic validity.

The regression suite recorded 30 failures and 18 passes before the repair.
Not every failed assertion was an unauthorized ALLOW: some inputs were already
denied but lacked a distinct invalid-input reason, and others tested whether
malformed authenticated policies were rejected by the verifier itself.

`src/governance/decision_envelope_v1.py` now checks:

- Resource constraints are finite and nonnegative. The existing zero value for
  a disabled thermal ceiling remains supported.
- The policy's risk ceiling and rule boundaries are known enum values.
- Action risk is a specified, known tier; action resources are finite, with
  nonnegative power and bandwidth. Negative temperature remains valid because
  caller-defined units may be Celsius.

The actual HMAC verifier runs before action validation. Valid actions at exact
thresholds still pass; unsigned, tampered, expired and wrong-key policies still
fail. QUARANTINE retains the existing `in_envelope=True, boundary=QUARANTINE`
contract: being inside this policy does not authorize execution.

Both HMAC and ML-DSA verifiers use the shared schema validator. The current
action evaluator invokes HMAC verification; this change does not connect
ML-DSA authorization to the execution gate. No cryptographic algorithm, key
size, signature format or canonical signing representation was changed.

## Recovered dependency

The TypeScript browser test previously imported an absent, ignored
`external/codex-skills-live` file. The dispatcher independently expected an
absent profile-installed skill. There is no tracked dependency or submodule
that provided either file in a fresh checkout.

Two existing C:\dev worktrees had identical scripts after line-ending
normalization. The owner's GitHub repository provided the matching source:
`issdandavis/codex-skills-live`,
`hydra-node-terminal-browsing/scripts/hydra_terminal_browse.mjs`, Git blob
`f0fbc25d7a534fecb646d1f0abab4488df94f1f8`.

`scripts/hydra/hydra_terminal_browse.mjs` preserves all 6,179 upstream bytes,
SHA-256 `d2a03d8520017a9421dcce79565009933a6517c186fe8d2e55ccd41a3d6c05a1`.
`scripts/hydra/SOURCE.md` records provenance. The dispatcher now prefers this
repo copy, retains profile fallback for other roots, and reports a missing
dependency without invoking Node if neither exists.

The added integration test starts a loopback HTTP fixture, invokes the real
CLI, and compares stdout with the written evidence JSON. Existing extraction
tests cover blocked element contents and executable link schemes. Four Python
cases exercise bundled selection, precedence, profile fallback and missing
dependency; three existing dispatcher CLI tests remain passing.

This recovered script is a text/link extractor. Its HTML stripping is not a
general HTML sanitizer, and it does not implement a network sandbox, URL
allowlist, response-byte limit or signed execution authorization.

## Verification and remaining boundary

Focused checks: 52 envelope tests passed (including four existing real ML-DSA
tests with the installed liboqs backend), four browser tests passed, and seven
dispatcher/dependency tests passed. No model, dependency or paid service was
installed.

The full TypeScript suite passed 6,741 tests in 215 files, with 20 tests in three
files skipped. The first broad Python attempt exposed an isolation-runner
mistake: plugin autoload was disabled without loading pytest-asyncio explicitly.
The corrected Python-only attempt loaded the installed required plugins and
reached two genuine missing imports during collection:

- `external/codex-skills-live/scbe-n8n-colab-bridge/scripts/colab_n8n_bridge.py`
- `external/codex-skills-live/scbe-api-key-local-mirror/scripts/key_mirror.py`

That run stopped with two collection errors and nine skips before executing
the full Python suite. Both owned processes exited and were reaped. These two
dependencies require their own source inspection and recovery; the complete
repository check is not green. Exact output and runner settings are retained
in the artifact receipt and logs.

Finite telemetry can still be fabricated unless its provenance is verified.
Resource attestation, request replay prevention, execution-bound capabilities
and connecting the existing signed envelope to the command executor remain
separate integration work. The prior wrapper's placeholder evidence is not
an authenticated sensor feed. This repair does not establish complete agent
containment or validate the patent's cryptographic hardness claims.

Before-state files, source proof, test logs, task-only diff, training observation
and final hashes live under
`artifacts/harness_authority_repair_20260909/`. Existing dirty work was preserved;
the task diff is against saved pre-edit bytes, not against Git HEAD.

At 16:29:41 UTC, Clay had 11 completed comparison arms; the final arm's
hash-verified checkpoint was at run step 512/2048. All 40 training source pins
matched, the original deadline remained in place, and this turn launched no
new training allocation or model promotion.
