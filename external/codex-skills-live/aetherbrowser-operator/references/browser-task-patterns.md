# Browser Task Patterns

Use this reference when turning a general online task into a repeatable browser loop.

## Standard loop

1. Discover
- Use search to find the exact page or target object.

2. Route
- Send the task through `browser_chain_dispatcher.py`.

3. Inspect
- Capture `title` and `snapshot` with `playwriter_lane_runner.py`.

4. Act
- Use `aetherbrowse_cli.py` for the smallest useful browser action.

5. Verify
- Re-capture state after action.

6. Hand off
- Emit artifact paths and the next action.

## Pattern: research read

Best for:

- papers
- docs
- release notes

Loop:

- search -> abstract/doc page -> title -> snapshot -> extract summary -> artifact path

## Pattern: signed-in ops

Best for:

- admin panels
- GitHub settings
- Codespaces
- Shopify

Loop:

- route -> inspect session surface -> do one action -> verify visual state -> capture artifact

## Pattern: multi-surface GitHub work

Best for:

- PR review with repo context
- codespace browser + terminal coordination

Loop:

- inspect repo state with `$scbe-gh-powershell-workflow`
- open repo page or codespace target in browser lane
- capture proof
- do smallest useful action
- return terminal/browser split in the final handoff

## Failure handling

- If search finds the target but page state is not needed, stay in fetch/search mode.
- If page state matters, always return to the browser lane.
- If the browser engine fails, switch engine or fall back to deterministic fetch, then report that the task is only partially complete.
