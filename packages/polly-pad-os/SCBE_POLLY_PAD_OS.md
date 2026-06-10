# Polly Pad OS — AI-Operable Desktop (base)

**What this is:** the base for an AI OS — a browser-rendered desktop with 82 apps that an
agent can drive from a backend and _see the result_. This is the Polly Pad upgrade: Polly Pad
goes from a CLI pad ([`packages/polly-pad-cli`](../polly-pad-cli)) to a full visual workspace
the SCBE fleet can operate.

## Provenance

- Source: `Kimi_Agent_Web Linux OS Build.zip` (Downloads), staged 2026-06-07.
- Stack: React 19, Vite 7, Tailwind 3.4, shadcn/ui (40+ primitives), TypeScript 5.9.
- 82 registered apps in `src/os/appRegistry.ts`. Window manager + Start menu + Taskbar in `src/os/`.
- An earlier build (`Kimi_Agent_Web_Linux_OS_Build_1/`) existed but was an empty husk by the time
  this was staged; this desktop build is the canonical base.
- Committed + pushed on `feat/cli-ui-kit` (HEAD `0f2b858f3` feat(app): add polly pad OS package); 166 files tracked.
  `node_modules` installed (gitignored).

## The thesis (why this matters)

If an AI agent can _use_ the apps, it gains a visual tool palette, not just text I/O:

| App class                                       | Agent use                                                               |
| ----------------------------------------------- | ----------------------------------------------------------------------- |
| Terminal, **Multi-Agent Terminal**, Code Editor | act — run commands, edit, drive the SCBE fleet/HYDRA                    |
| System Monitor, Disk Usage, Task Manager        | observe — render machine state (e.g. the real C: disk-pressure problem) |
| Paint, Spreadsheet, Charts, Photo/Video         | produce — generate visual artifacts the agent can show                  |
| **Layered Abacus**, Calculator, Math Graph      | calculate — chunked rows/layers, prime-basis rows, numeric snapshots    |
| Games (Chess, Sudoku, 2048…)                    | sandboxed verify-by-play / reasoning surfaces                           |

The backend contract is now concrete in `src/os/runtime.ts`:

```ts
const runtime = createPollyPadRuntime();
const result = runtime.invoke('terminal', 'open', { data: { cwd: '/repo' } });
```

Every call returns `{ ok, action, appId, windowId?, error?, snapshot }`. The snapshot includes
registered apps, desktop icons, windows, active window, theme, start-menu state, notifications, and
viewport. This lets an agent operate the OS like a structured control surface instead of scraping
pixels. The rendered React desktop can still be driven separately, but the state authority is a
typed invocation layer.

`Multi-Agent Terminal` (already in the registry) is the natural socket into the SCBE fleet.

## Programmatic controls

Supported actions:

- `snapshot`, `listApps`
- `open`, `close`, `focus`, `minimize`, `maximize`, `restore`
- `move`, `resize`, `setTitle`
- `setTheme`, `setStartMenu`, `notify`
- `abacusSetRow`, `abacusAddLayer`, `abacusReset` for `layeredabacus`

Verification: `npm test` runs `tests/runtime.test.ts`, which proves the 82-app registry, app open,
move/resize, singleton focus behavior, system-level theme/menu/notification calls, close behavior,
chunked layered-abacus math with prime-basis rows, and fail-closed invalid input handling.

## Next steps

1. ~~`npm install`~~ done (node_modules present). ~~Confirm `npm run dev` boots the desktop~~ done on `127.0.0.1:5187`.
2. ~~Programmatic `invoke()` runtime~~ done (`src/os/runtime.ts`, verified by `npm test`).
3. Wire one app end-to-end (Multi-Agent Terminal -> backend stub) so the visual app and runtime share live state.
4. If needed later, connect the React app state directly to the backend runtime so browser clicks and agent invokes use the same live store.
