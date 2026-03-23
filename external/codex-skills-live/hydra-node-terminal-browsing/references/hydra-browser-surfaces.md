# HYDRA Browser Surfaces

This reference maps the browser-related implementation surfaces used by the HYDRA Node terminal-browsing skill.

## Core Modules

- `hydra/browsers.py`
  - Browser backend adapters and interface compliance layer.
- `hydra/swarm_browser.py`
  - 6-agent sacred tongue orchestrator (KO/AV/RU/CA/UM/DR).
- `hydra/cli_swarm.py`
  - CLI entrypoint for swarm execution.

## Related Tests

- `tests/hydra/test_browsers.py`
- `tests/hydra/test_swarm_browser.py`
- `tests/hydra/test_cli_swarm.py`
- `tests/hydra/test_llm_providers_hf.py`
- `tests/hydra/test_keyword_persistence.py`

## Recommended Verification Commands

```powershell
python -m pytest tests/hydra/test_browsers.py -q
python -m pytest tests/hydra/test_swarm_browser.py -q
python -m pytest tests/hydra/test_cli_swarm.py -q
```

## Operational Notes

- Start with `--dry-run` on swarm tasks before live runs.
- For deterministic extraction artifacts, use `hydra_terminal_browse.mjs` with `--out`.
