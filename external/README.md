# external/

Third-party and mirrored content. Do not edit files here; changes belong upstream.

| Path | Kind | Source |
|------|------|--------|
| `Entropicdefenseengineproposal` | git submodule | github.com/issdandavis/Entropicdefenseengineproposal |
| `claude-code-plugins-plus-skills` | git submodule | github.com/jeremylongshore/claude-code-plugins-plus-skills |
| `designer-skills` | git submodule | github.com/Owl-Listener/designer-skills |
| `codex-skills-live/` | vendored copy (462 files) | Snapshot of installed Codex skills, each a folder with a `SKILL.md` |

Submodule folders are empty until you run:

```bash
git submodule update --init --recursive
```

## Related: `external_repos/`

`external_repos/` (gitignored apart from its gitlinks, so it carries no README) holds seven more submodules: `Spiralverse-AetherMoore`, `ai-workflow-architect`, `aws-lambda-simple-web-app`, `scbe-quantum-prototype`, `scbe-security-gate`, `spiralverse-protocol`, and `visual-computer-kindle-ai`.

`.gitmodules` registers `spiralverse-protocol` at the repo root, not at `external_repos/spiralverse-protocol`. The gitlink inside `external_repos/` therefore has no URL mapping and `git submodule update` cannot fetch it.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/external.md`](../docs/file-index/external.md).
