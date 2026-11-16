# ai-ide/

Vite + React + Tailwind front-end titled "SCBE-AETHERMOORE Training Lab": a browser IDE shell with a code editor, terminal, file sidebar, and AI assistant pane.

- `src/components/` — `CodeEditor`, `Terminal`, `LeftSidebar`, `AIAssistant`, `Layout`.
- `src/data/` — seed files shown in the editor and the Hugging Face agent-pair command definitions.
- `src/utils/languageDetector.ts` — file-extension to language mapping.

```bash
cd ai-ide && npm install && npm run dev
```

Most source files here have no header comment; the file index describes them by their exports.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/ai-ide.md`](../docs/file-index/ai-ide.md).
