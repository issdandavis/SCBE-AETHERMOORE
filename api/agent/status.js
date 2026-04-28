"use strict";

const { envConfig, githubFetch, sendJson, setCors } = require("../_agent_common");

function summarizeRun(run) {
  return {
    id: run.id,
    name: run.name,
    display_title: run.display_title,
    event: run.event,
    status: run.status,
    conclusion: run.conclusion,
    branch: run.head_branch,
    created_at: run.created_at,
    updated_at: run.updated_at,
    html_url: run.html_url,
  };
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return sendJson(res, 405, { ok: false, error: "GET required" });

  const cfg = envConfig();
  const workflow = String(req.query.workflow || cfg.workflow);
  const limit = Math.max(1, Math.min(Number(req.query.limit || 10), 30));

  const response = await githubFetch(
    cfg,
    `/actions/workflows/${encodeURIComponent(workflow)}/runs?branch=${encodeURIComponent(cfg.ref)}&per_page=${limit}`,
  );

  if (!response.ok) {
    const text = await response.text();
    return sendJson(res, response.status, {
      ok: false,
      error: "GitHub workflow run lookup failed",
      github_status: response.status,
      details: text.slice(0, 800),
    });
  }

  const payload = await response.json();
  const runs = (payload.workflow_runs || []).map(summarizeRun);
  const active = runs.filter((run) => ["queued", "in_progress", "waiting"].includes(run.status));
  const latest = runs[0] || null;

  return sendJson(res, 200, {
    ok: true,
    repo: cfg.repo,
    workflow,
    active_count: active.length,
    latest,
    runs,
  });
};
