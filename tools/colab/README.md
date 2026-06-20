# colab_run — drive a Colab notebook from the terminal

Google offers **no headless CLI for hosted Colab**, so the robust way to run a paid-Colab notebook from
the terminal is to reuse *your own authenticated browser session*. You launch Chrome once with a remote
debugging port and log into Colab; `colab_run.py` attaches over CDP (Playwright `connect_over_cdp`),
opens the notebook, runs all cells, waits out the run, and prints the result back to your terminal.

## Setup (one time)

Start Chrome with a debugging port and a dedicated profile, then log into Colab in that window:

```bat
"C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="%USERPROFILE%\.colab-cdp-profile"
```

(Use a *separate* `--user-data-dir` so the debug port opens reliably and your normal profile is untouched.)

## Run

```bash
# 1. confirm the tool can attach + load the notebook (no execution)
python tools/colab/colab_run.py --dry-run

# 2. run all cells and wait for the result (default notebook = the VTC lift harness)
python tools/colab/colab_run.py --run
```

It polls the rendered output for a **completion marker** (`NET LIFT` for the VTC notebook — what
`code_lift.render()` prints last) and prints the matching block. Override per notebook with
`--done-marker "<text the last cell prints>"`.

Useful flags: `--notebook <url|catalog-name>`, `--timeout <seconds>` (default 5400 = 90 min for a
training run), `--port <cdp-port>`, `--launch` (own Chrome + `--profile` instead of attach),
`--upload <file>` (best-effort: feed a pending `files.upload()` input).

## Corpus delivery (the VTC notebook)

The notebook's cell 2 tries **Drive → URL → upload**. For an *unattended* terminal run, set one so it
never blocks on a dialog: put the corpus on Drive at `DRIVE_CORPUS`, or set `CORPUS_URL` to a secret
gist/release raw URL. Manual `files.upload()` is the fallback.

## Transport options (your call: #1 now; #2/#3 documented)

| # | Mode | How | When |
|---|------|-----|------|
| **1** | **Attach (default)** | `connect_over_cdp` to the Chrome you started with `--remote-debugging-port` | **Recommended now.** Reuses your live Google login, no re-auth, works with hosted paid Colab. |
| 2 | Launch | `--launch` opens its own Chrome with a persistent `--profile` you log into once | If you can't expose a debug port. Google may flag automation in that profile. |
| 3 | Runtime socket | Talk to the Jupyter kernel directly, no UI | Most robust *ceiling* — but for **hosted** Colab the kernel endpoint is proxied/rotated by Google and not cleanly extractable. Only pays off for a **local/self-hosted** runtime (see `scbe-n8n-colab-bridge`). |

**Most-robust verdict for hosted paid Colab: option 1.** Option 3's "no brittle DOM" advantage only
materializes when you control the runtime; against hosted Colab it isn't reliably reachable, so attach
(#1) is both the now-path and the most robust *practical* choice. #2 is the fallback if a debug port
isn't an option.

## Honest caveat

Colab's UI is not a stable automation target. Run-all uses the `Ctrl+F9` shortcut (more durable than
clicking the menu), and completion is detected by *your notebook's own printed marker* (not Colab's
run-state DOM) — both deliberately robust. The trust-dialog / Connect-button selectors are best-effort
and may need a one-line tweak on the first live run; `--dry-run` lets you confirm attach + load first.
Reuses the repo's notebook catalog (`scripts/system/colab_workflow_catalog.py`) for `--notebook <name>`.
