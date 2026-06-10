# Vendored engine: Hermes Agent (by reference)

The Aether harness uses **Hermes Agent** (NousResearch, MIT) as its execution
engine. We vendor it **by reference**, not by source dump: this repo is public
and code-lean, and the upstream tree is ~127 MB (website, infographic, apps,
tests, locales). Committing that would bloat git history permanently for no
gain — the only thing we actually changed is one 24-line patch.

So instead of an in-tree copy, we pin the exact commit, carry our patch, and
bootstrap a working clone on demand.

## Pin

| Field | Value |
|-------|-------|
| Upstream | `https://github.com/NousResearch/Hermes-Agent` |
| Pinned commit | `a72bb03757c0c925c686f9774eefc8dc5a77b329` |
| Commit subject | `fix(docker): optimize image size … (#38749)` |
| License | MIT (preserved in the clone) |
| Python | 3.12 (upstream is incompatible with 3.14 — pydantic-core has no cp314 wheel) |

## Our changes (the only reason this is a "fork")

1. **`patches/0001-strip-reasoning-content-on-replay.patch`** — reasoning models
   (gpt-oss, GLM) over plain OpenAI-compatible endpoints (Cerebras, "custom")
   reject an echoed assistant `reasoning_content` with HTTP 400. The patch
   strips it from the *replayed* api message when the active provider does not
   require the thinking-mode echo (`agent._needs_thinking_reasoning_pad()` is
   the pre-existing upstream helper, so this is idiomatic, not a bolt-on).
   Without it, any multi-turn tool-using run on Cerebras dies on turn 2.

2. **The governance plugin** (`../../hermes_plugin/`) is copied into the clone's
   `plugins/scbe-governance/`. It registers a `pre_tool_call` hook that routes
   every tool call through the SCBE governance seam and blocks on DENY. This is
   the engine's *native, intended* extension point — no monkeypatching.

## Bootstrap

```powershell
# from packages/aether-harness/vendor/hermes/
pwsh ./bootstrap_hermes.ps1            # clones to C:\Users\issda\harness-study\hermes-agent
pwsh ./bootstrap_hermes.ps1 -Dest D:\path\to\clone
```

The script clones the pinned commit, applies the patch, creates a 3.12 venv,
installs deps, and copies the governance plugin in. After it runs, launch a
governed task with `HERMES_HOME` pointed at a dir whose `config.yaml` enables
the plugin (see `../../hermes_plugin/config.example.yaml`).

## Where blocking actually comes from (honesty note)

In the proven runs the **DENY on `rm -rf /` came from the GeoSeal command
scanner**, not the hyperbolic gate (the gate reported `calibrating` and did not
itself flag the command). The seam takes the worst verdict across {gate,
GeoSeal scan}, so shell-command safety is carried by the GeoSeal scanner today;
the gate contributes governance signals/receipts. Do not read the demo as the
geometry catching bad commands. See the package README for the full proof.
