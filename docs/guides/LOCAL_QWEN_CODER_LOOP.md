# Local Qwen Coder Loop

This machine already has the right base runtime for a free local coding model:

- `ollama.exe` is installed.
- `hf` is installed.
- The GPU is `GTX 1660 Ti 6GB`, so the safe default is `qwen2.5-coder:7b` through Ollama.

## Recommended local model

Use `qwen2.5-coder:7b` for coding on this laptop. It is free, local, and small enough to run on the current GPU class.

## One-time setup

```powershell
.\scripts\setup_local_qwen_coder.ps1 -EnsureTemplates
.\scripts\setup_local_qwen_coder.ps1 -PullModel
.\scripts\setup_local_qwen_coder.ps1 -RegisterAgent
```

If `ollama pull` fails because the desktop app is in a bad state, fully quit the Ollama desktop app and rerun the pull.

## Manual coding cycle

Interactive loop:

```powershell
python .\scripts\scbe-system-cli.py agent cycle --agent-id qwen-local --interactive --append-memory --show-context
```

One-shot call:

```powershell
python .\scripts\scbe-system-cli.py agent cycle --agent-id qwen-local --prompt "inspect the CLI parser and suggest the smallest fix" --append-memory --show-context
```

## Obsidian files used by the loop

- Context note: `notes/agent-memory/local-qwen-coder-context.md`
- Memory log: `notes/agent-memory/local-qwen-coder-memory.md`

The cycle command loads the context note into the model prompt and appends successful turns to the memory log when `--append-memory` is enabled.

## Local endpoint details

- Provider: `openai-compatible`
- Endpoint: `http://127.0.0.1:11434/v1`
- Model: `qwen2.5-coder:7b`

This works because the upgraded `scripts/scbe-system-cli.py` now supports OpenAI-compatible local endpoints without requiring an API key.

## Notes

- The Obsidian memory log is append-only by design.
- Keep the context note short and curated; do not dump full repo files into it.
- If you want stronger coding performance later, move to a larger Qwen coder on a machine with more VRAM.
