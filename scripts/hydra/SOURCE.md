# Hydra terminal browser source

`hydra_terminal_browse.mjs` is an exact copy of Issac's existing script from
`issdandavis/codex-skills-live`, recovered on 2026-09-09. No parser or fetch
behavior was changed while moving the dependency into this repository.

- Source path: `hydra-node-terminal-browsing/scripts/hydra_terminal_browse.mjs`
- Git blob: `f0fbc25d7a534fecb646d1f0abab4488df94f1f8`
- SHA-256: `d2a03d8520017a9421dcce79565009933a6517c186fe8d2e55ccd41a3d6c05a1`
- Size: 6179 bytes; imports only Node built-ins.
- Two older local worktree copies matched the GitHub bytes after CRLF normalization.

The tracked copy is the default used by `scripts/system/octoarms_dispatch.py`
and its parser tests. The dispatcher retains the installed profile-skill path
as a fallback when operating on a repository without the bundled script.
Upstream changes should be reviewed and this provenance updated deliberately.

Run `node scripts/hydra/hydra_terminal_browse.mjs --help` for usage. Importing
the module does not fetch a page or run the CLI. It is a text/link extractor;
it is not an HTML security sanitizer, a rendered browser, or a network sandbox.
