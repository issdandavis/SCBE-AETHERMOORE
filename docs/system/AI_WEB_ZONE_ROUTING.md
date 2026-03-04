# AI Web Zone Routing

This document defines practical zone routing for AetherBrowse automation.

## Zone Model

- `open`: Public pages and APIs with low friction.
- `soft`: Rate-limited or session-sensitive pages.
- `hard`: High-friction pages (auth, anti-bot, strict flows).
- `dark`: Onion/Tor-routed lane (lawful research use only).

## Runtime Controls

Set these environment variables before launching runtime/worker:

```env
AETHERBROWSE_NETWORK_PROFILE=open
AETHERBROWSE_PROXY_SERVER=
AETHERBROWSE_TOR_PROXY=socks5://127.0.0.1:9050
AETHERBROWSE_PROXY_USERNAME=
AETHERBROWSE_PROXY_PASSWORD=
AETHERBROWSE_PROXY_BYPASS=
AETHERBROWSE_FORCE_PROXY=0
```

## Worker Actions

- `set_network_profile` with `network_profile=open|soft|hard|dark`
- `navigate` can include `network_profile` to switch profile before navigation.

## Playwriter Lane (Existing Browser Session)

For signed-in flows that should reuse an already-open Chrome tab, use the
Playwriter lane instead of launching a separate browser context.

Dispatcher now supports:

- `--engine playwriter` (or payload `{"engine":"playwriter"}`)
- lane log: `artifacts/agent_comm/github_lanes/playwriter_lane.jsonl`

Executor:

```bash
python scripts/system/playwriter_lane_runner.py --session 1 --domain github.com --task navigate
python scripts/system/playwriter_lane_runner.py --session 1 --url https://example.com --task snapshot
```

Execution log:

- `artifacts/agent_comm/github_lanes/playwriter_exec.jsonl`

## Notes

- `dark` profile uses `AETHERBROWSE_TOR_PROXY` (or `AETHERBROWSE_PROXY_SERVER`) and defaults to `socks5://127.0.0.1:9050`.
- If no proxy is reachable, the worker returns normal Playwright errors; it does not silently bypass governance intent.
- Use this only for compliant, authorized automation work.
