"use strict";

const { ALLOWED_TASKS, envConfig, setCors } = require("../_agent_common");

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderTaskList() {
  return Array.from(ALLOWED_TASKS)
    .map((task) => `<code>${escapeHtml(task)}</code>`)
    .join("");
}

function renderLaunchPage(cfg) {
  const configured = Boolean(cfg.githubToken);
  const secretRequired = Boolean(cfg.dispatchSecret);
  const docsBase = "https://aethermoore.com/SCBE-AETHERMOORE";
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SCBE Agent Bridge</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #080c10;
      --panel: #101820;
      --line: #22303a;
      --text: #eef5f3;
      --muted: #9fb0ad;
      --accent: #2dd3a6;
      --warn: #f0b65f;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
      display: grid;
      place-items: center;
      padding: 32px 18px;
    }
    main {
      width: min(860px, 100%);
      border: 1px solid var(--line);
      background: var(--panel);
      padding: 28px;
      border-radius: 8px;
    }
    h1 { margin: 0 0 8px; font-size: clamp(28px, 5vw, 44px); letter-spacing: 0; }
    p { color: var(--muted); line-height: 1.55; margin: 0 0 18px; }
    .status {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      margin: 22px 0;
    }
    .status div {
      border: 1px solid var(--line);
      padding: 14px;
      border-radius: 6px;
      min-height: 82px;
    }
    strong { display: block; margin-bottom: 6px; }
    code {
      display: inline-block;
      margin: 4px 6px 4px 0;
      padding: 4px 7px;
      border: 1px solid var(--line);
      border-radius: 5px;
      color: var(--accent);
      background: #07100f;
      font-size: 13px;
    }
    a {
      color: var(--accent);
      text-decoration: none;
      font-weight: 650;
    }
    .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 22px;
    }
    .actions a {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px 12px;
      color: var(--text);
      background: #0b1218;
    }
    .actions a.primary {
      color: #04100d;
      border-color: var(--accent);
      background: var(--accent);
    }
    .warn { color: var(--warn); }
  </style>
</head>
<body>
  <main>
    <h1>SCBE Agent Bridge</h1>
    <p>This Vercel surface is the lightweight launch and status bridge for the GitHub Actions agent router. The public documentation and checkout pages remain on GitHub Pages.</p>
    <section class="status" aria-label="Bridge status">
      <div>
        <strong>Repository</strong>
        <span>${escapeHtml(cfg.repo)}</span>
      </div>
      <div>
        <strong>Workflow</strong>
        <span>${escapeHtml(cfg.workflow)}</span>
      </div>
      <div>
        <strong>Ref</strong>
        <span>${escapeHtml(cfg.ref)}</span>
      </div>
      <div>
        <strong>Dispatch</strong>
        <span class="${configured ? "" : "warn"}">${configured ? "configured" : "missing GitHub token"}</span>
      </div>
      <div>
        <strong>Secret Gate</strong>
        <span>${secretRequired ? "required" : "not required"}</span>
      </div>
    </section>
    <p><strong>Allowed Tasks</strong>${renderTaskList()}</p>
    <nav class="actions" aria-label="Launch links">
      <a class="primary" href="/api/agent/health">Health JSON</a>
      <a href="/api/agent/status?limit=5">Recent Runs</a>
      <a href="${docsBase}/agents.html">Agent Console</a>
      <a href="${docsBase}/">Public Launch Site</a>
      <a href="${docsBase}/support.html">Support</a>
    </nav>
  </main>
</body>
</html>`;
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return res.status(405).send("GET required");

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.status(200).send(renderLaunchPage(envConfig()));
};
