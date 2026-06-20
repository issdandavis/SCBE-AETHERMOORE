# colab_run — drive a hosted Colab notebook from the terminal

Google offers **no headless CLI** for hosted Colab, and it **blocks sign-in in a Playwright-launched
browser** (the automation flag trips Chrome's "unsupported command-line flag" bar and Google's "this
browser may not be secure" wall). The path that actually works — validated live — is to launch a
**plain `chrome.exe`** ourselves with only a debug port (no automation flags, so Google lets you sign
in), then **attach over CDP** and drive the notebook. Attaching adds no automation flag, so the login
goes through and the session persists.

## Run

```bash
# first time: opens a window, you do the ONE-TIME Google sign-in, then it verifies and closes
python tools/colab/colab_run.py --dry-run --keep-open 240

# run the notebook: run-all, feed the corpus, wait, print the result
python tools/colab/colab_run.py --run --upload "C:/path/to/vtc_mbpp_refined.jsonl"
```

The first run pops a Chrome window for the **one-time Google login** (a human must do it — Google blocks
automated credential entry). The login persists in the profile, so every later run is zero-touch. The
tool then opens the notebook, handles the **"Run anyway" / Connect** prompts, runs all cells, and
**feeds `--upload` into the notebook's `files.upload()` cell** so the run never blocks on a file dialog.
Completion is detected by polling the outputs for `--done-marker` (default `NET LIFT`, what the VTC
notebook's `code_lift.render()` prints) — your notebook's own result, not Colab's brittle run-state DOM.

## Flags

| Flag | Meaning |
|------|---------|
| `--run` / `--dry-run` | execute, or just launch + load (verify / sign in) |
| `--upload <file>` | local corpus fed into the notebook's `files.upload()` cell during the run |
| `--notebook <url\|name>` | a Colab URL, a catalog name, or omit for the VTC lift notebook |
| `--profile <dir>` | persistent Chrome profile (login persists here; default `~/.colab-cdp-profile`) |
| `--port <n>` | Chrome debug port (launched for you; or your own with `--attach`) |
| `--attach` | attach to a Chrome **you** started with `--remote-debugging-port` instead of launching one |
| `--done-marker <text>` | output text that signals completion (default `NET LIFT`) |
| `--timeout <s>` / `--login-timeout <s>` | max wait for the result (default 90 min) / for the one-time sign-in |
| `--chrome-path <exe>` | path to `chrome.exe` (auto-detected if omitted) |

## Why this design (and what didn't work)

- **Playwright-launched Chrome → blocked.** `launch`/`launch_persistent_context` set `--enable-automation`
  + `navigator.webdriver`, which Google detects → "browser may not be secure", no login. Don't use it.
- **Plain `chrome.exe` + `connect_over_cdp` → works.** No automation flag is set, so Google treats it as
  a normal browser and the sign-in succeeds; CDP-attach then drives it.
- **Runtime-socket (drive the Jupyter kernel directly, no UI)** is the most robust *ceiling*, but for
  **hosted** Colab the kernel endpoint is proxied/rotated by Google and not cleanly reachable — it only
  pays off for a local/self-hosted runtime (see `scbe-n8n-colab-bridge`). So attach-to-real-Chrome is the
  best practical option for hosted paid Colab.

## Honest caveat

Colab's UI is not a stable automation target. Run-all uses the `Ctrl+F9` shortcut (more durable than
clicking the menu); the trust-dialog / Connect / sign-in selectors are best-effort and may need a
one-line tweak on a first live run. `--dry-run` confirms attach + load before a long training run. The
corpus cell on the VTC notebook tries Drive → URL → upload; for a fully unattended run, prefer the
`--upload` feed (corpus stays local) or set `CORPUS_URL`/`DRIVE_CORPUS` in the notebook.
