# Colab n8n bridge source

`colab_n8n_bridge.py` is the existing owner-maintained script from
`issdandavis/codex-skills-live`,
`scbe-n8n-colab-bridge/scripts/colab_n8n_bridge.py`.

- Git blob: `130f69d767cdca71594f1b8e7e7b7e3302247a70`
- SHA-256: `84d1936a887857bfb664f031864e9e50259cd9060d4650edde58d80e4b5df3f2`
- Size: 9,477 bytes; upstream bytes preserved without algorithm changes.
- Verified 2026-09-09 against GitHub and two existing C:\dev worktree copies
  after local CRLF normalization.

The tracked system CLI now delegates here. The script discovers the repo root
via `pyproject.toml` and uses `src.security.secret_store`; importing it or using
`--help` does not open a profile. Its operational subcommands explicitly manage
profiles or probe a backend. It is separate from the DOM specification in
`scripts/system/colab_bridge.py`.

Example for syntax only: `python scripts/colab/colab_n8n_bridge.py --help`.
Tests use temporary stores and dummy secrets. This recovery does not claim
comprehensive URL, redirect, credential-output or network-boundary hardening.
