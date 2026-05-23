# Ollama Local Service Tool

Status: local/free operator surface.

This tool configures Ollama from the command line as both a service and a callable AI tool. It does not use hosted APIs by default and blocks `*:cloud` models in `generate` and `smoke`.

## Commands

```powershell
# Check the local Ollama API
npm run ollama:health

# Start `ollama serve` in the background if the API is not reachable
npm run ollama:start

# List downloaded local models, excluding cloud entries
npm run ollama:list

# Smoke-test the default local model
npm run ollama:smoke

# Print environment values for the local agent bridge
npm run ollama:bridge-env
```

Direct Python form:

```powershell
python scripts/system/ollama_tool.py generate "Write one sentence about SCBE receipts." --model openclaw:latest
python scripts/system/ollama_tool.py bridge-env --model openclaw:latest --port 8787
python scripts/system/ollama_tool.py pull qwen2.5-coder:1.5b
```

`pull` is explicit because it can consume disk. No script pulls new model blobs silently.

## Bridge Mode

To expose Ollama through the local agent bridge:

```powershell
.\scripts\system\setup_local_ollama_backend.ps1 -SkipPull -StartOllama -ServeModel openclaw:latest
```

The bridge sets:

- `AGENT_CHAT_PROVIDER_ORDER=ollama,offline`
- `AGENT_OLLAMA_URL=http://127.0.0.1:11434`
- `AGENT_OLLAMA_MODEL=<selected model>`
- `LOCAL_AGENT_BRIDGE_PORT=8787`

Then it serves:

- `GET http://127.0.0.1:8787/api/agent/health`
- `POST http://127.0.0.1:8787/api/agent/chat`

## Policy

- Local Ollama first.
- Offline fallback second.
- No hosted API by default.
- No cloud Ollama model route unless a future command explicitly adds an opt-in flag.
