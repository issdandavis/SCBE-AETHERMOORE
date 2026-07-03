# Aetherbrowser MCP Tool Bridge

## Product Claim

Aetherbrowser can be used as a local Codex/MCP browser tool. It reuses a
persistent Chrome profile, exposes typed browser actions, and writes JSON
receipts plus screenshot/text artifacts for verification.

This is the first productable slice: a governed browser worker that can be sold
as a local-first AI operator lane, not just a manually launched browser app.

## Tool Surface

The MCP server lives at:

```powershell
scripts/system/aetherbrowser_mcp_server.mjs
```

It exposes:

- `aetherbrowser_doctor`
- `aetherbrowser_targets`
- `aetherbrowser_start`
- `aetherbrowser_status`
- `aetherbrowser_open`
- `aetherbrowser_inspect`
- `aetherbrowser_screen`
- `aetherbrowser_click_text`
- `aetherbrowser_type_text`
- `aetherbrowser_press_key`
- `aetherbrowser_monitor`
- `aetherbrowser_voiceover`
- `aetherbrowser_voice_code`

The bridge only calls the allowlisted repo entrypoint:

```powershell
scripts/system/aether_browser_agent.mjs
```

It does not execute arbitrary host shell text.

## Local Commands

Check the bridge and write a front-door receipt without launching Chrome:

```powershell
npm run aetherbrowser:frontdoor
```

Start or reuse persistent Chrome through the same bounded lane:

```powershell
npm run aetherbrowser:frontdoor -- --start --target github
```

Open a destination and refresh the receipt:

```powershell
npm run aetherbrowser:frontdoor -- --open --target github
```

Probe the MCP server and call `aetherbrowser_doctor`:

```powershell
npm run aetherbrowser:mcp:probe
```

Run the MCP server directly:

```powershell
npm run aetherbrowser:mcp
```

Start persistent Chrome:

```powershell
npm run aetherbrowser:start -- --target github
```

Check status:

```powershell
npm run aetherbrowser:status -- --json
```

Create a local voiceover WAV:

```powershell
npm run aetherbrowser:voiceover -- --text "Aetherbrowser is ready." --basename demo
```

Speak through the default audio device as well:

```powershell
npm run aetherbrowser:voiceover -- --text "Aetherbrowser is ready." --speak-now
```

List the local voice-coding lanes:

```powershell
npm run aetherbrowser:voice-code -- --action inventory
```

Compile notes into a governed guitar/mode code receipt:

```powershell
npm run aetherbrowser:voice-code -- --action guitar --dialect "E minor" --notes "E E G" --basename guitar-demo
```

Compile a holophonor phrase into code faces, colors, melody, and an execution
receipt:

```powershell
npm run aetherbrowser:voice-code -- --action holophonor --song "C E" --args 2,3,4 --basename holophonor-demo
```

Compile expressive prosody text and write a local WAV:

```powershell
npm run aetherbrowser:voice-code -- --action expressive --text "compile *the button* | ^then verify^" --speak --basename expressive-demo
```

## Plugin Wiring

The installed local plugin advertises the MCP bridge through:

```text
C:\Users\issda\.codex\plugins\cache\scbe-local-plugins\aetherbrowse\0.1.0\.mcp.json
```

The plugin manifest points to that file with:

```json
{
  "mcpServers": "./.mcp.json"
}
```

After reinstalling/reloading the plugin in a new Codex thread, the bridge should
surface as first-class `aetherbrowser_*` MCP tools.

## Safety Boundary

- Uses a persistent Chrome profile that the user signs into directly.
- Does not scrape credentials or bypass login.
- Does not run arbitrary shell commands.
- Keeps screenshots and inspect artifacts under `artifacts/aetherbrowser_mcp/`
  when called through MCP.
- Keeps front-door readiness receipts under
  `artifacts/aetherbrowser_frontdoor/`.
- Keeps local voiceover WAV receipts under `artifacts/aetherbrowser_voiceover/`.
- Keeps voice-code receipts and optional WAV artifacts under
  `artifacts/aetherbrowser_voice_code/`.
- Voiceover stores text length/hash plus a short preview in receipts instead of
  echoing the full transcript.
- Voice-code wraps repo-owned coding runtimes only: instrument computer,
  Machine Crystal key phrases, proof receipts, and expressive TTS. It does not
  expose arbitrary host shell execution.
- Sensitive text entry still requires normal user authorization discipline.

## Sellable Next Layer

The next product layer is a small hosted/local dashboard that shows:

- active tabs and current task receipts,
- screenshot/text artifact history,
- voiceover artifacts and narration status,
- voice-code receipts that map speech/music/prosody into executable code paths,
- governance decisions,
- training/Colab monitor state,
- install status for Codex, Claude, and MCP clients,
- packaging status for the Windows AetherBrowser desktop app.
