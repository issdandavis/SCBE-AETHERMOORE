# Governed Harness — Study & Keep-List (Hermes vs Claude Code)

_2026-06-10. Evidence-based input for the Slice-1 design. "Study/compare first, build after" (user's call)._

## Goal

We're building a **custom, governed agent harness that replaces the terminal** — the Claude-Code-style experience (streaming loop, option-buttons, notes, slash commands, nested if-then workflows) but under our control, on our moat (SCBE gate + anchor wall + GeoSeal receipts, Polly Pad OS, coding_spine, 100+ skills). Before committing an architecture, we stood up Hermes locally and ran a task through it, and characterized the Claude Code harness, to produce an evidence-based **keep-list**.

## What was actually run (provenance — honest)

Hermes Agent v0.16.0, MIT, cloned to `C:/Users/issda/harness-study/hermes-agent` (home scratch zone per STORAGE_RULES). Installed with `uv venv --python 3.12` + `uv pip install -e .` (core only). **Python 3.14 is unusable** for it — Hermes caps `requires-python <3.14` because pydantic-core has no cp314 wheel; uv built a 3.12 venv.

Task run through the **real one-shot harness** (`cli.py --query … --quiet`): _"Create palindrome.py + test_palindrome.py with 3 pytest cases, run pytest, report."_ Model attempts (honest about what failed and why — none were harness-logic bugs):

| Provider/model | Result | What it proves |
|---|---|---|
| `anthropic/claude-sonnet-4-6` | 400 **billing** (no API credit on the key) | Loop + provider wiring work; the Claude Code key has no standalone API balance |
| `custom → groq/llama-3.3-70b` | 401 invalid key | env `GROQ_API_KEY` is stale |
| `custom → ollama/qwen2.5-coder:1.5b` | refused: **needs ≥64K context** | Hermes enforces a 64K context floor (design opinion) |
| `custom → cerebras/llama-3.3-70b` | 404 model id | key valid, wrong id |
| `custom → cerebras/gpt-oss-120b` | wrote `palindrome.py` ✓ then **reasoning_content** 400 | harness plans + writes correct code; adapter bug on re-send |
| `custom → cerebras/zai-glm-4.7` | wrote **both** files ✓ then reasoning_content 400 | same — got further (both files) |

**Key result:** the code Hermes generated **passes all 3 tests** (`3 passed in 0.48s`, verified by running pytest ourselves). The harness did the real work; only the 3rd turn (self-running pytest) died — consistently — on a provider-adapter bug, not harness logic.

## Hermes findings (live + source-verified)

- **Installs/boots clean.** MIT (forkable commercially), Python, `uv`, light core deps (provider SDKs are lazy-installed extras → small supply-chain blast radius; they exact-pin every dep after a 2026 PyPI worm).
- **30 tools enabled by default** incl. `clarify` (its AskUserQuestion analog), `delegate_task` (subagents, isolated context), `execute_code`, accessibility-tree browser (9 tools), `file` (patch/read/write/search), cron, image_gen. 0 skills until you add them.
- **UX is good:** boxed banner, session ids, and a **per-edit "review diff" affordance** (`a/file → b/file` unified diff) — exactly the edit-review surface we want.
- **Provider layer genuinely pluggable** — every provider reached the real API; failures were creds/model-id/context/format. Switching is `--provider/--model`, no code change (declarative `ProviderProfile` dataclass).
- **Self-improving skills** in `SKILL.md` format (same standard our repo already uses) with progressive disclosure (list→view→file) and an autonomous `curator` that prunes/consolidates. **Memory** = `MEMORY.md`/`USER.md` + SQLite-FTS5 session search.
- **Cleanest graft seam:** every tool routes through `registry.handle_function_call`. Wrapping that one function with our SCBE gate + GeoSeal receipt governs the whole harness without touching the loop.
- **Real bug to avoid inheriting:** the generic `custom` adapter doesn't strip assistant `reasoning_content` before re-sending, so multi-turn breaks with reasoning models (gpt-oss, GLM) over OpenAI-compat endpoints. Our provider layer must normalize reasoning content.

## Claude Code harness (first-hand + research)

- **Streaming event loop** (gather→act→verify), tokens + tool-start/tool-end + a one-word status verb — the biggest "feels alive" lever. Hermes' one-shot returns the whole turn at once (less live).
- **`AskUserQuestion` = the "buttons."** Schema: 1–4 questions, each 2–4 `{label,description}` options, `header≤12`, `multiSelect`, recommended-first, **always an "Other"→free-text escape**, plus a top-level free-text `response`. Used **only when blocked on a genuinely-user decision**. (This is the surface the user pointed at: "buttons interaction, notes like this.")
- **"Notes like this"** = the free-text on a choice + persistent re-injected memory notes (this very session shows `MEMORY.md` re-injected as gray context). Capture `{decision, choice, note}`, promote durable ones to a memory file, re-inject as marked passive context.
- **5-step permission pipeline:** hooks → deny → ask → mode → allow → runtime callback. **Deny beats bypass.** Maps onto SCBE L13: gate = the "hooks" stage (runs first, hard-deny regardless of mode); ask→QUARANTINE, escalate→ESCALATE, deny→DENY. Five callback shapes worth copying: approve / approve-with-changes (sanitize input) / approve-and-remember / deny-with-reason (fed back to model) / suggest-alternative.
- **Subagents:** isolated context, return distilled results; **never inherit broader permissions than parent**; share a tree-wide work/budget cap (Hermes' `IterationBudget` is a good model). User-facing questions route to the parent.
- **Extensibility:** user-invoked `/commands` + model-invoked skills, file-on-disk, no rebuild; bundle as plugins. Our `scbe-*` skills already follow this.

## Keep-list (what to take from each)

**Fork/borrow from Hermes:** the harness loop + tool registry (wrap `handle_function_call` as the governance seam); the SKILL.md skill system + curator (format-compatible with ours); the `ProviderProfile` provider abstraction; local accessibility-tree browser; `delegate_task` subagent model; MEMORY.md/USER.md + FTS5 session memory. Strip: messaging gateway (Discord/Feishu/etc.), media-gen tools, cloud browser backends — to shrink deps + attack surface.

**Replicate from Claude Code (build ourselves, on top):** the **streaming** event loop with live status; the **AskUserQuestion buttons** (exact schema + Other/free-text); **notes-on-decisions** persisted + re-injected; the **5-step permission pipeline** with SCBE as the hooks stage and the five callback response shapes; **plan mode + live todo checklist**.

**Our moat, wired in:** SCBE gate + anchor wall → **GeoSeal receipt per governed action** (the seam); Polly Pad OS as the eventual GUI surface (it already has Terminal/Approval/AuditLog apps); coding_spine router/indexer where better than Hermes' equivalents; our skill library.

**Fix that neither gives us free:** provider-layer `reasoning_content` normalization (Hermes' custom adapter bug); a non-reasoning or reasoning-aware default model with ≥64K context.

## Recommended Slice 1 (to spec next)

**Governed Hermes graft, minimal:** vendor/fork Hermes, run it in PowerShell on a working ≥64K model (fix the env keys: get a live API key or a local model with ≥64K ctx), and **wrap `registry.handle_function_call` with the SCBE gate + anchor wall, emitting a GeoSeal receipt per tool call** (ALLOW proceeds; QUARANTINE/ESCALATE pauses; DENY blocks + receipt). That single seam = Hermes' power + our governance + our control, and it's the spine every later slice (buttons/notes surface, if-then workflows, multi-agent, Polly GUI) builds on.

**Open decisions for the design step:** (1) vendor-into-repo vs. submodule vs. pip-dep fork; (2) which model/provider is the reliable default (the cred situation needs sorting); (3) terminal-first vs. Polly-GUI-first surface.
