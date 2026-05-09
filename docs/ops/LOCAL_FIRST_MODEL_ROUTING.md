# Local-First Model Routing

SCBE chat and agent support should prefer the cheapest usable model path:

1. Local Ollama when `OLLAMA_URL` or `AGENT_OLLAMA_URL` is configured.
2. Hugging Face when `HF_TOKEN`, `HUGGINGFACE_TOKEN`, or `HUGGING_FACE_HUB_TOKEN` is configured.
3. Deterministic offline response when no model provider is available.

This keeps the mobile/web endpoint usable with minimal external dependency, while still allowing better hosted models when a token or paid provider is intentionally configured.

## Vercel / Hosted Endpoint

`api/agent/chat.js` is the public chat bridge used by mobile/web clients.

Useful environment variables:

```text
AGENT_CHAT_PROVIDER_ORDER=ollama,huggingface,offline
AGENT_OLLAMA_URL=http://127.0.0.1:11434
AGENT_OLLAMA_MODEL=llama3.2
HF_TOKEN=...
AGENT_HF_MODEL=Qwen/Qwen2.5-7B-Instruct
HF_CHAT_URL=https://router.huggingface.co/v1/chat/completions
AGENT_CHAT_TIMEOUT_MS=25000
```

For Vercel production, `AGENT_OLLAMA_URL` should usually be unset unless the deployment can reach a private Ollama service. Vercel cannot reach an Ollama process running on the user's home PC at `127.0.0.1`. On a local/self-hosted backend, set `AGENT_OLLAMA_URL=http://127.0.0.1:11434` and keep Hugging Face as fallback.

## Health Check

`GET /api/agent/health` reports:

- provider order
- whether Ollama is configured
- whether Hugging Face is configured
- chosen Ollama and Hugging Face model IDs
- the cost policy

## At-Home Smoke Test

Do not put Ollama model blobs in GitHub. Keep GitHub for code, scripts, and small manifests. Keep Ollama models on the
machine that serves inference, or publish model artifacts through Hugging Face when a real model release is needed.

This machine currently has small local models suitable for a free-first backend:

- `qwen2.5-coder:1.5b`
- `gemma3:1b`
- `scbe-geoseal-coder:q8`
- `qwen2.5-coder:0.5b`

When the home machine is available, start Ollama:

```powershell
ollama list
ollama serve
```

Then, from another shell, run the local bridge:

```powershell
npm run agent:local-ollama
```

The bridge serves the same public endpoints the mobile app already uses:

- `GET /api/agent/health`
- `POST /api/agent/chat`
- `POST /api/agent/search`
- `GET|POST /api/agent/storage`

It prints a LAN URL like:

```text
phone: http://192.168.1.25:8787
```

Put that URL into the mobile app's **Bridge** field while the phone is on the same Wi-Fi. The app will then use the PC's
Ollama models without customer API keys.

One-shot setup helper:

```powershell
.\scripts\system\setup_local_ollama_backend.ps1
```

Use `-SkipPull` if the models are already present:

```powershell
.\scripts\system\setup_local_ollama_backend.ps1 -SkipPull
```

For a direct module smoke test:

```powershell
$env:AGENT_OLLAMA_URL="http://127.0.0.1:11434"
$env:AGENT_OLLAMA_MODEL="qwen2.5-coder:1.5b"
node -e "const {routeChat,chatConfig}=require('./api/agent/chat.js')._private; routeChat(chatConfig(),'Say READY in one word',[]).then(r=>console.log(JSON.stringify(r,null,2)))"
```

Expected result: `provider` is `ollama` and `model` is the configured local model.

## Google Play Upload Reminder

Upload the corrected internal-test bundle:

```text
C:\Users\issda\Downloads\aethermoor-bus-internal-0.1.1-io.aethermoor.bus-SIGNED.aab
```

Verified package name: `io.aethermoor.bus`.
