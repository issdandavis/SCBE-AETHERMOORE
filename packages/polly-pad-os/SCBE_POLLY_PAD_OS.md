# Polly Pad OS — AI-Operable Desktop (base)

**What this is:** the base for an AI OS — a browser-rendered desktop with 81 apps that an
agent can drive from a backend and _see the result_. This is the Polly Pad upgrade: Polly Pad
goes from a CLI pad ([`packages/polly-pad-cli`](../polly-pad-cli)) to a full visual workspace
the SCBE fleet can operate.

## Provenance

- Source: `Kimi_Agent_Web Linux OS Build.zip` (Downloads), staged 2026-06-07.
- Stack: React 19, Vite 7, Tailwind 3.4, shadcn/ui (40+ primitives), TypeScript 5.9.
- 81 registered apps in `src/os/appRegistry.ts`. Window manager + Start menu + Taskbar in `src/os/`.
- An earlier build (`Kimi_Agent_Web_Linux_OS_Build_1/`) existed but was an empty husk by the time
  this was staged; this 81-app build is the canonical base.
- Staged, **not** committed/pushed. No `node_modules` installed yet (deferred for disk pressure).

## The thesis (why this matters)

If an AI agent can _use_ the apps, it gains a visual tool palette, not just text I/O:

| App class                                       | Agent use                                                               |
| ----------------------------------------------- | ----------------------------------------------------------------------- |
| Terminal, **Multi-Agent Terminal**, Code Editor | act — run commands, edit, drive the SCBE fleet/HYDRA                    |
| System Monitor, Disk Usage, Task Manager        | observe — render machine state (e.g. the real C: disk-pressure problem) |
| Paint, Spreadsheet, Charts, Photo/Video         | produce — generate visual artifacts the agent can show                  |
| Games (Chess, Sudoku, 2048…)                    | sandboxed verify-by-play / reasoning surfaces                           |

The backend contract is roughly: `invoke(appId, action, args) -> { state, snapshot }` — the agent
issues structured actions, each app returns structured state **plus** a rendered visual. No pixel
screen-scraping (the noVNC-desktop alternative); each app is a React component with real state.

`Multi-Agent Terminal` (already in the registry) is the natural socket into the SCBE fleet.

## Next steps (not yet done)

1. `npm install` + `npm run dev` to confirm it boots (deferred until Codex finishes freeing disk).
2. Wire one app end-to-end (Multi-Agent Terminal -> backend stub) as the proof of the `invoke()` contract.
3. Decide commit/push (push policy: code-only to main, await explicit ask).
