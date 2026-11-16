# plugins/

Agent plugins, each packaged for both Claude Code (`.claude-plugin/plugin.json`) and Codex (`.codex-plugin/plugin.json`).

| Plugin | Purpose |
|--------|---------|
| `aetherbrowse/` | Develop and operate the AetherBrowse governed browser: start, check, and logs commands, a debugger agent, and three skills |
| `nonstop/` | Autonomous working mode: Stop and SessionStart hooks plus the `autonomous-work` skill |
| `scbe-verify/` | Dry-run verification across languages and Sacred Tongue lenses before a change lands |

---

Every file in this directory is listed with a one-line description in [`docs/file-index/plugins.md`](../docs/file-index/plugins.md).
