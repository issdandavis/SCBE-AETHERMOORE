# OpenClaw Browser — Post-Start Troubleshoot

Fallback playbook for keeping forward momentum after `bridge start`. Symptom-first.
Each rung degrades capability gracefully so a stalled browser never blocks the agent loop.

## Known-good baseline

| Thing | Value |
|---|---|
| Config | `~/.openclaw/openclaw.json` |
| Gateway port | `18789` (loopback, token auth) |
| Browser control port | `18791` (loopback) |
| CDP port | `18800` (`http://127.0.0.1:18800`) |
| Daemon PID | check `netstat -ano \| grep :18789` |
| Chrome exe | `C:\Program Files\Google\Chrome\Application\chrome.exe` |
| Bridge CLI | `python scripts/system/openclaw_browser_bridge.py <cmd>` |
| Driver field | `driver: openclaw`, `transport: cdp` |

## Fast triage (30 seconds)

```bash
# 1. ports up?
netstat -ano | grep -E ":18789|:18791|:18800|:11434"

# 2. bridge sees gateway?
python scripts/system/openclaw_browser_bridge.py status

# 3. CDP actually serving?
curl -s http://127.0.0.1:18800/json/version
```

Three green = everything's fine, problem is elsewhere (Playwright client, page logic).
Any red = jump to the matching symptom below.

## Symptom -> Fix Ladder

### S1. `bridge status` returns `running: false` after `bridge start`

1. Wait 2s and re-poll. Chrome cold-start can lag the CDP ready bit.
2. Check `cdpHttp: false` — gateway thinks it launched but CDP didn't bind.
   - `taskkill //F //IM chrome.exe` (kills orphans), then `bridge start` again.
3. Still false → `bridge stop` then `bridge start --profile openclaw`.
4. `detectError` non-null → Chrome path moved. Override:
   `bridge start --profile openclaw` after editing `openclaw.json`:
   ```json
   "browser": { "executablePath": "C:\\Path\\To\\chrome.exe" }
   ```

### S2. `curl :18800/json/version` hangs or 404s

CDP isn't actually up even though the daemon says it launched.
1. Confirm Chrome is running: `tasklist | grep chrome`
2. If yes but no port → Chrome started without `--remote-debugging-port`. Bridge launch flags got dropped. `bridge stop`, `taskkill //F //IM chrome.exe`, restart.
3. If no Chrome → DEP/AV blocking. Check Windows Defender event log; whitelist OpenClaw workspace dir.
4. Last resort: launch Chrome manually with the flag and **attach** instead of letting OpenClaw launch:
   ```bash
   "C:\Program Files\Google\Chrome\Application\chrome.exe" \
     --remote-debugging-port=18800 \
     --user-data-dir="C:\Users\issda\.openclaw\workspace\chrome-profile"
   ```
   Then in `openclaw.json` set `"browser": { "attachOnly": true, "cdpPort": 18800 }` and `bridge start`.

### S3. Bridge 401/403 against gateway

Token mismatch. Bridge reads `gateway.auth.token` from the same `openclaw.json` the daemon was started with.
1. Daemon was started against an old config → restart daemon.
2. `--config-path` flag pointing somewhere stale → drop the flag, default works.

### S4. Playwright `connectOverCDP` errors

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:18800")
    ctx = browser.contexts[0] if browser.contexts else browser.new_context()
    page = ctx.pages[0] if ctx.pages else ctx.new_page()
```

| Error | Fix |
|---|---|
| `ECONNREFUSED` | CDP not up — go to S2 |
| `WebSocket error` mid-session | Chrome crashed or OpenClaw recycled it. Re-run `bridge status`; reconnect on next status PASS |
| `Target page closed` | Page navigated under you. Use `ctx.pages[-1]` instead of cached `page` |
| `browser.contexts` empty | Fresh launch, no default context. Use `browser.new_context()` |
| Hangs forever on `connect_over_cdp` | Wrong URL scheme. Must be `http://`, NOT `ws://` — Playwright resolves to ws itself |

### S5. OpenClaw and Playwright fight over the same page

Both controllers see the page but actions interleave badly.
- **Convention**: OpenClaw drives navigation + auth; Playwright drives DOM scraping + assertions.
- Pin Playwright to a dedicated tab: `ctx.new_page()` and never touch `ctx.pages[0]` (that's OpenClaw's).
- Use `page.evaluate("() => document.readyState")` before reads — don't trust OpenClaw's idle signal across the CDP boundary.

### S6. Recovery lane (commit `902988ea`)

If the bridge gets wedged in a state where `status` reports `running: true` but no requests land:
```bash
python scripts/system/openclaw_browser_bridge.py stop
taskkill //F //IM chrome.exe
# wait 1s
python scripts/system/openclaw_browser_bridge.py start
```
This is the exact sequence the recovery lane fix was built around. If this doesn't restore CDP, the daemon itself is wedged — restart OpenClaw service.

### S7. Daemon (PID on 18789) gone

```bash
netstat -ano | grep :18789   # empty?
```
1. Restart OpenClaw daemon (whatever launches `openclaw` on this box — usually a tray app or a service).
2. Re-run Fast Triage.
3. If daemon won't come up, check `~/.openclaw/logs/` for the last error line.

## Forward-momentum fallbacks (when nothing recovers)

Pick the highest rung that works. Don't burn an hour debugging rung 1 when rung 3 unblocks the actual goal.

1. **Headless Playwright, no OpenClaw.** Drop governance, keep automation:
   ```python
   browser = p.chromium.launch(headless=True)
   ```
   Lose: OpenClaw recording, telegram channel, governance gate.
   Keep: scraping, screenshots, the task at hand.

2. **`mcp__claude-in-chrome` direct.** If Claude-in-Chrome extension is installed in a regular Chrome window, load `mcp__claude-in-chrome__tabs_context_mcp` via ToolSearch and drive that browser instead. Bypasses OpenClaw entirely.

3. **HTTP-only `WebFetch` / `curl`.** If the task is read-only (fetch a page, parse JSON), skip browsers entirely. Most "I need a browser" tasks actually don't.

4. **HYDRA swarm browser** (`mcp__scbe-orchestrator__hydra_swarm_*`). Different daemon, different port, different process tree — survives an OpenClaw outage.

5. **Defer + log.** If none of the above fit, write the intent to `training/intake/web_research/blocked/<timestamp>.json` with the URL and the goal, then move on. The blocked queue gets drained by the next session that has a working browser.

## Don't-do list

- Don't `taskkill` the daemon (PID on 18789) without restarting it — bridge becomes useless.
- Don't edit `openclaw.json` while the daemon is running. Stop, edit, start.
- Don't run two `bridge start` calls in parallel. The second one races the first's CDP bind and you get S2.
- Don't trust `running: true` alone. Always confirm with `curl :18800/json/version`.
- Don't checkpoint Playwright `Page` objects across `bridge stop`/`start`. Reconnect from scratch.

## Verification one-liner

Drop this at the top of any browser-using script — fails fast, prints the blocking rung:

```bash
python scripts/system/openclaw_browser_bridge.py status \
  | python -c "import sys,json; s=json.load(sys.stdin); \
    assert s.get('running') and s.get('cdpReady'), f'BRIDGE NOT READY: {s}'; \
    print('bridge OK on', s.get('cdpUrl'))"
```
