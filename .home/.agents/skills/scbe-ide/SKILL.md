---
name: scbe-ide
description: Launch and operate the SCBE Codex IDE with Polly Pad workspaces, Hugging Face integration, crew collaboration, and governance zones. Use when opening or recovering the local web-based code editor.
---

# scbe-ide

Launch the SCBE Codex IDE — a multi-AI collaborative code editor with Polly Pad workspaces, HuggingFace AI integration, crew collaboration, and SCBE governance zones.

## When to use

- User says `/ide`, "open ide", "launch ide", "start the editor"
- User wants to open the web-based code editor
- User wants multi-AI collaborative coding

## Steps

1. **Kill any existing IDE server** on port 3000:
   ```bash
   # Windows
   taskkill /F /IM python.exe /FI "WINDOWTITLE eq Codex IDE*" 2>/dev/null || true
   ```

2. **Start the IDE server** pointing at the SCBE workspace:
   ```bash
   cd C:/Users/issda/Codex-ide
   python server.py "C:/Users/issda/SCBE_Production_Pack_local" -p 3000 --no-open &
   ```

3. **Open in browser**:
   ```bash
   start http://127.0.0.1:3000
   ```

4. **Join as crew member** — POST to `/api/crew/join` with your identity:
   ```bash
   curl -s -X POST http://127.0.0.1:3000/api/crew/join \
     -H "Content-Type: application/json" \
     -d '{"name": "Codex", "role": "Codex"}'
   ```

5. **Report status** to the user: IDE is running at http://127.0.0.1:3000 with crew collaboration active.

## Features

- **File Explorer**: Browse, create, edit, delete files
- **Monaco Editor**: Syntax highlighting, minimap, themes
- **Terminal**: Run shell commands (git, build, npm, pytest)
- **AI Chat**: Talk to HuggingFace models for code help, review, generation
- **Crew Panel**: See connected agents (human + AI), chat together
- **Polly Pad Zones**: HOT (exploratory) / SAFE (execution) dual code zones with SCBE governance
- **Search**: Full-text search across workspace

## Architecture

- **Backend**: `C:/Users/issda/Codex-ide/server.py` (Python, zero-dependency HTTP server)
- **Frontend**: `C:/Users/issda/Codex-ide/index.html` (Monaco editor, single-file SPA)
- **Polly Pads**: SQLite-backed pad lifecycle via `hydra/polly_pad.py`
- **AI Providers**: HuggingFace Inference API (direct HTTP from browser, no server proxy needed)
