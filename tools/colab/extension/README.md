# AetherDesktop extension — governed Colab in your own browser

Run Colab actions from an AI/assistant **in your real, logged-in Chrome** (first-party — no automation
flags, no Google bot-block), with every action **screened and sealed** by the local governance bridge
before it touches the page. This is the "hands" layer; the guardrails + memory live in
`tools/colab/aether_bridge.py` + `python/scbe/colab_actions.py`.

## How it works

```
popup (you / an AI click an action)
   │  PROPOSE  →  http://127.0.0.1:8777/govern   (X-Aether-Token)
   ▼
aether_bridge  →  colab_actions gate  (never-delete / scope / chain / L13 / confirm)  →  sealed transcript
   │  verdict
   ▼
ALLOWED?  → content.js runs it in the Colab tab (Ctrl+F9 / read output / run cell)
REFUSED / NEEDS_CONFIRM / DENIED → shown; nothing runs
```

The gate is **always in front of the hands**: the page action only fires on an `ALLOWED` verdict, and
every proposal (allowed or not) is appended to `~/.aether_desktop/transcript.jsonl` — your tamper-evident
record of what was done in your name. A cell that injects a destructive payload is **refused**, even with
confirm.

## Setup (one time)

1. Start the governance bridge in a terminal and copy its token:
   ```bash
   python tools/colab/aether_bridge.py
   # -> AetherDesktop bridge on http://127.0.0.1:8777 ...
   # -> X-Aether-Token: <copy this>
   ```
2. Load the extension: `chrome://extensions` → enable **Developer mode** → **Load unpacked** →
   select `tools/colab/extension/`.
3. Open a Colab notebook (logged in). Click the AetherDesktop toolbar icon, paste the token, **Save**.

## Use

With a Colab tab focused, click **Read output / Run cell / Run all**. Guarded actions prompt for a
reason (recorded in the seal). The result (and the seal prefix) shows in the popup.

## Why an extension (vs the CDP terminal driver)

`tools/colab/colab_run.py` drives Colab over CDP from the terminal — great for unattended runs, but it
attaches to a separately-launched Chrome. The **extension runs inside your normal browser** as a
first-party citizen: no `--enable-automation` flag, no "this browser may not be secure", and it's the
natural place for a per-action approval UI. Both share the same governance gate and sealed memory.

## Security notes

- The bridge binds **127.0.0.1 only** and requires the per-session **token** — no other local process can
  drive your browser through it. Treat the token like a password; it rotates every bridge restart.
- The extension is privileged (it can act on Colab pages). Load it **unpacked from this repo only**; don't
  sideload an untrusted copy.
- Colab's ToS is a gray area on automation. This keeps it **local, transparent, and per-action approved**
  in your own session — you're delegating your own paid service to your own assistant, not running a bot.
