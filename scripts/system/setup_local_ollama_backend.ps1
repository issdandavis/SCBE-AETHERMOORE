param(
  [string[]] $Models = @("qwen2.5-coder:1.5b", "gemma3:1b"),
  [string] $ServeModel = "qwen2.5-coder:1.5b",
  [int] $Port = 8787,
  [switch] $SkipPull,
  [switch] $StartOllama
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  throw "Ollama is not on PATH. Install Ollama first, then rerun this script."
}

Write-Host "Ollama detected:"
ollama --version

if ($StartOllama) {
  Write-Host "Ensuring local Ollama service is running..."
  python scripts/system/ollama_tool.py start --json | Out-Host
}

if (-not $SkipPull) {
  foreach ($model in $Models) {
    Write-Host "Ensuring Ollama model is present: $model"
    python scripts/system/ollama_tool.py pull $model
  }
}

$env:AGENT_CHAT_PROVIDER_ORDER = "ollama,offline"
$env:AGENT_OLLAMA_URL = "http://127.0.0.1:11434"
$env:AGENT_OLLAMA_MODEL = $ServeModel
$env:AGENT_CHAT_TIMEOUT_MS = "45000"
$env:LOCAL_AGENT_BRIDGE_PORT = [string] $Port

Write-Host ""
Write-Host "Installed models:"
python scripts/system/ollama_tool.py list

Write-Host ""
Write-Host "Starting Aethermoor local bridge. Leave this window open."
Write-Host "If Ollama is not already running, rerun with -StartOllama or start it in another window with: ollama serve"
node scripts/system/local_ollama_agent_bridge.cjs
