# Manhwa Roundtable Long-Run Context

Use this when Codex, Claude, and any helper lanes need to stay aligned across multiple sessions without re-explaining the whole project every time.

## Stable Task ID

- `MANHWA-ROUNDTABLE`

Keep this `TaskId` stable for the ongoing manhwa production thread.

## Working Seats

| Seat | Agent | Name | Owns |
|---|---|---|---|
| Strategist | `agent.claude` | `Opus` | ledger, working notes, text overlays, scene phrasing, reference organization |
| Engineer | `agent.codex` | `Codex` | packets, render router, edit packet tooling, APK-side integration |
| Librarian | `agent.keeper` | `Keeper` | world bible, style rules, character continuity, reference constraints |
| Artisan | `agent.grok` | `Grok` | hero concept art and quality bar setting |
| Soldier | `agent.imagen` | `Imagen` | batch and hero generation routed by the renderer |
| Bard | `agent.kokoro` | `Kokoro` | narration schema, TTS, pacing timings, recap audio prep |
| DM | `agent.issac` | `Issac` | approvals, creative direction, final decisions |

## Extended Operational Lane

| Lane | Agent | Name | Owns |
|---|---|---|---|
| Fine edit | `agent.editor` | `Editor` | Photoshop, Canva, Adobe Express, touch-up packets, promo variants |

## Current Working Context

Any long-run packet should assume these are true unless a later packet explicitly changes them:

1. `artifacts/webtoon/panel_prompts/ch01_prompts_v4.json` is the current Chapter 1 beat-expanded generation packet.
2. `artifacts/webtoon/ch01/v4_preview/v4_reading_preview.jpg` validated that the strip rhythm reads like a book.
3. The old 30-panel text overlay file is a rendering-style reference, not the new 56-panel content source.
4. `scripts/merge_text_layer_v4.py` is the content merge lane for the 56-panel v4 packet.
5. `scripts/render_grok_storyboard_packet.py` is the Imagen-first router:
   - `imagen-ultra` for hero panels
   - `imagen` for batch panels
   - `hf` as fallback
6. `scripts/build_manhwa_edit_packet.py` is the handoff lane for Photoshop, Canva, and Adobe Express.
7. `notes/manhwa-project/ledger/art-style-bible.md` is the active style doctrine source.
8. `notes/manhwa-project/references/character-catalog.md` and `notes/manhwa-project/references/location-catalog.md` are the active anchor set.

## Shared Project Goal

Build a production-grade Chapter 1 webtoon lane for `The Six Tongues Protocol` that can:

- read correctly in vertical scroll form
- preserve the book's emotional order and the current working constraints
- generate selectively through the Imagen router
- route weak-but-promising frames into human fine-edit apps
- feed text and voice systems without losing beat alignment

## Packet Minimum

Every meaningful packet should include:

- `summary`: one factual sentence
- `next_action`: who should do what next
- `where`: exact lane or file zone
- `why`: why this matters to the roundtable
- `how`: packet path, merge path, or render path
- `proof`: file paths when a change exists

## Cadence

- Emit one packet when a session starts.
- Emit one packet at each meaningful handoff.
- Emit one packet if blocked.
- Run cross-talk reliability audit every 4 hours during active multi-agent work.

## Copy-Paste Commands

Start or rotate the Codex lane:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\system\emit_manhwa_roundtable.ps1 -Role codex -NewSession -Summary "Codex session started for packet/render/edit pipeline work." -NextAction "Opus sync story/text context and respond with any conflicts."
```

Start or rotate the Opus lane:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\system\emit_manhwa_roundtable.ps1 -Role opus -NewSession -Summary "Opus session started for ledger/story/text overlay work." -NextAction "Codex confirm packet/schema alignment and open any implementation blockers."
```

Post a render update:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\system\emit_manhwa_roundtable.ps1 -Role imagen -Summary "Rendered first v4 shortlist through Imagen router." -NextAction "Editor build fine-edit packet for the strongest panels." -Proof "artifacts/webtoon/generated_router/ch01/ch01_prompts_v4_router_manifest.json"
```

Post an edit handoff:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\system\emit_manhwa_roundtable.ps1 -Role editor -Summary "Built fine-edit packet for selected Chapter 1 panels." -NextAction "Photoshop pass on anatomy/light fixes, then Claude reviews story continuity." -Proof "artifacts/webtoon/edit_packets/ch01"
```

Post a blocked packet:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\system\emit_manhwa_roundtable.ps1 -Role codex -Status blocked -Summary "Blocked on deciding whether to render or emulator-test next." -NextAction "Roundtable choose one path and avoid splitting effort."
```

Audit packet mirrors:

```powershell
python scripts/system/crosstalk_reliability_manager.py
```

## Current Working Decision

Do not push emulator testing back into the critical path yet.

Current priority order:

1. render a small `v4` shortlist
2. fine-edit only the best `2-3` panels
3. validate text merge and reading rhythm
4. then run device scroll verification
