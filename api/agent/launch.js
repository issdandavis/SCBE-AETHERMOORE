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
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SCBE Customer Launch</title>
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
    .split {
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      margin-top: 22px;
    }
    .split section {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 16px;
      background: #0b1218;
    }
    .split ul {
      margin: 10px 0 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.55;
    }
    .split h2 {
      margin: 0 0 8px;
      font-size: 18px;
      letter-spacing: 0;
    }
    .warn { color: var(--warn); }
  </style>
</head>
<body>
  <main>
    <h1>SCBE Customer Launch</h1>
    <p>Start with the public offers, pay through the live checkout paths, or open the agent bridge when you need the governed router. This page keeps customer entry points and operator status in one place.</p>
    <nav class="actions" aria-label="Customer links">
      <a class="primary" href="/payments">Payment Center</a>
      <a href="/products">Products</a>
      <a href="/workflow-snapshot">Workflow Snapshot</a>
      <a href="/hosted-run">Hosted Run Intake</a>
      <a href="/service-credits">Service Credits</a>
      <a href="/supporter">Supporter</a>
    </nav>
    <div class="split" aria-label="Launch paths">
      <section>
        <h2>For Customers</h2>
        <p>Use the payment center for Ko-fi, Cash App, Stripe, or manual invoice paths. Paid work routes into intake so delivery can start without another setup conversation.</p>
        <ul>
          <li>Buy or tip first, then submit intake when the task needs context.</li>
          <li>Do not send secrets through public forms or payment notes.</li>
          <li>For higher-touch work, use Workflow Snapshot or Hosted Run.</li>
        </ul>
      </section>
      <section>
        <h2>For Operators</h2>
        <p>The bridge below exposes health, recent runs, and the allowed dispatch task list for the GitHub Actions agent router.</p>
        <ul>
          <li>Health and run status stay available without touching customer pages.</li>
          <li>Dispatch stays gated by configured credentials and task allowlists.</li>
          <li>Public buyer pages are served through first-party Vercel routes.</li>
        </ul>
      </section>
    </div>
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
    <nav class="actions" aria-label="Operator links">
      <a class="primary" href="/api/agent/health">Health JSON</a>
      <a href="/api/agent/status?limit=5">Recent Runs</a>
      <a href="/agents">Agent Console</a>
      <a href="/chat">Polly Chat</a>
      <a href="/legal/privacy">Privacy</a>
      <a href="/legal/terms">Terms</a>
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
