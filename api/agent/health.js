"use strict";

const { ALLOWED_TASKS, MAX_QUERY_LENGTH, envConfig, sendJson, setCors } = require("../_agent_common");

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return sendJson(res, 405, { ok: false, error: "GET required" });

  const cfg = envConfig();
  return sendJson(res, 200, {
    ok: true,
    service: "scbe-agent-vercel-bridge",
    repo: cfg.repo,
    workflow: cfg.workflow,
    ref: cfg.ref,
    dispatch_configured: Boolean(cfg.githubToken),
    dispatch_secret_required: Boolean(cfg.dispatchSecret),
    allowed_tasks: Array.from(ALLOWED_TASKS),
    max_query_length: MAX_QUERY_LENGTH,
  });
};
