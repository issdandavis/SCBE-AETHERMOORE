"use strict";

const { authOk, envConfig, githubFetch, readJsonBody, sendJson, setCors, validateTaskInput } = require("../_agent_common");

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return sendJson(res, 405, { ok: false, error: "POST required" });

  const cfg = envConfig();
  if (!authOk(req, cfg)) {
    return sendJson(res, 401, { ok: false, error: "invalid dispatch secret" });
  }
  if (!cfg.githubToken) {
    return sendJson(res, 501, {
      ok: false,
      error: "GITHUB_TOKEN or GH_TOKEN is not configured in Vercel",
      required_env: ["GITHUB_TOKEN", "GITHUB_REPO", "AGENT_ROUTER_WORKFLOW", "AGENT_DISPATCH_SECRET"],
    });
  }

  let body;
  try {
    body = await readJsonBody(req);
  } catch (error) {
    return sendJson(res, 400, { ok: false, error: `invalid JSON body: ${error.message}` });
  }

  const checked = validateTaskInput(body);
  if (!checked.ok) return sendJson(res, checked.status, { ok: false, error: checked.error });

  const response = await githubFetch(cfg, `/actions/workflows/${encodeURIComponent(cfg.workflow)}/dispatches`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ref: cfg.ref,
      inputs: {
        task: checked.task,
        query: checked.query,
        publish: checked.publish,
      },
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    return sendJson(res, response.status, {
      ok: false,
      error: "GitHub workflow_dispatch failed",
      github_status: response.status,
      details: text.slice(0, 800),
    });
  }

  return sendJson(res, 202, {
    ok: true,
    status: "queued",
    repo: cfg.repo,
    workflow: cfg.workflow,
    ref: cfg.ref,
    task: checked.task,
    publish: checked.publish,
    next: {
      status_url: "/api/agent/status",
      runs_url: "/api/agent/runs",
    },
  });
};
