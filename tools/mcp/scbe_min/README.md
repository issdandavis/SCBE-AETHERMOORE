# SCBE MIN MCP Stub

This folder provides a minimal MCP server scaffold for safe, parallel web automation.

## What it exposes

- `6` tools
- `4` resources
- `3` resource templates
- Dual output on tool calls: `StateVector` and `DecisionRecord`
- Canonical decision set: `ALLOW`, `QUARANTINE`, `DENY`

## Files

- `tools/mcp/scbe_min/server.py`: stdio MCP server stub + telemetry emitter
- `tools/mcp/scbe_min/contract.min.yaml`: MIN contract definition
- `tools/mcp/scbe_min/analyze_telemetry.py`: telemetry -> dataset + next-step analysis

## Run self-test

```powershell
python tools/mcp/scbe_min/server.py --self-test
```

## Run server

```powershell
python tools/mcp/scbe_min/server.py
```

Optional telemetry controls:

```powershell
python tools/mcp/scbe_min/server.py --telemetry-path C:/temp/scbe_events.jsonl
python tools/mcp/scbe_min/server.py --disable-telemetry
```

Default telemetry output:

- `artifacts/scbe_min/telemetry/events.jsonl`

## Example MCP config entry

```json
{
  "mcpServers": {
    "scbe-min": {
      "command": "python",
      "args": ["C:/Users/issda/SCBE-AETHERMOORE/tools/mcp/scbe_min/server.py"]
    }
  }
}
```

## Learning loop (Astromech mode)

1. Run tasks through `browser.run_headless` with optional `action_diagnostics` that include click `intended` and `actual` points.
2. Analyze emitted telemetry into HF-ready rows and recommendations.
3. Upload dataset artifacts to Hugging Face.

```powershell
python tools/mcp/scbe_min/analyze_telemetry.py
```

```powershell
python tools/mcp/scbe_min/analyze_telemetry.py --upload-hf --hf-repo YOUR_USER/YOUR_DATASET
```

Outputs:

- `training-data/scbe-min/scbe_min_browser_telemetry.jsonl`
- `training-data/scbe-min/scbe_min_browser_telemetry.analysis.json`

The analyzer flags click drift and rounded-decimal telemetry gaps to produce concrete next-step actions.

## Example request (JSON-RPC line)

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list"}
```

## Next integration points

1. Replace `browser.run_headless` stub internals with Playwright or remote browser worker execution.
2. Replace antivirus baseline checks with your real scanner/telemetry pipeline.
3. Add persistent storage for tasks, runs, and artifacts.
4. Connect analyzer outputs into HYDRA policy update PRs.