"use strict";

const DEFAULT_REPO = "issdandavis/SCBE-AETHERMOORE";
const DEFAULT_WORKFLOW = "agent-router.yml";
const DEFAULT_REF = "main";
const MAX_QUERY_LENGTH = 600;
const ALLOWED_TASKS = new Set(["research", "monitor", "ask", "scrape"]);
const PAGES_DATA_BASE = "https://aethermoore.com/SCBE-AETHERMOORE/static/agent-data";

function setCors(res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Agent-Dispatch-Secret");
  res.setHeader("Access-Control-Max-Age", "86400");
}

function sendJson(res, status, payload) {
  setCors(res);
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.status(status).json(payload);
}

function readJsonBody(req) {
  if (req.body && typeof req.body === "object") return Promise.resolve(req.body);
  return new Promise((resolve, reject) => {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
      if (raw.length > 4096) {
        reject(new Error("request body too large"));
        req.destroy();
      }
    });
    req.on("end", () => {
      if (!raw.trim()) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch (error) {
        reject(error);
      }
    });
    req.on("error", reject);
  });
}

function envConfig() {
  return {
    githubToken: process.env.GITHUB_TOKEN || process.env.GH_TOKEN || "",
    repo: process.env.GITHUB_REPO || DEFAULT_REPO,
    workflow: process.env.AGENT_ROUTER_WORKFLOW || DEFAULT_WORKFLOW,
    ref: process.env.AGENT_ROUTER_REF || DEFAULT_REF,
    dispatchSecret: process.env.AGENT_DISPATCH_SECRET || "",
    pagesDataBase: process.env.AGENT_PAGES_DATA_BASE || PAGES_DATA_BASE,
  };
}

function authOk(req, cfg) {
  if (!cfg.dispatchSecret) return true;
  const bearer = String(req.headers.authorization || "").replace(/^Bearer\s+/i, "");
  const headerSecret = String(req.headers["x-agent-dispatch-secret"] || "");
  return bearer === cfg.dispatchSecret || headerSecret === cfg.dispatchSecret;
}

function validateTaskInput(input) {
  const task = String(input.task || "").trim().toLowerCase();
  const query = String(input.query || "").trim();
  const publish = input.publish === undefined ? "true" : String(input.publish);

  if (!ALLOWED_TASKS.has(task)) {
    return { ok: false, status: 400, error: `task must be one of: ${Array.from(ALLOWED_TASKS).join(", ")}` };
  }
  if (!query) {
    return { ok: false, status: 400, error: "query is required" };
  }
  if (query.length > MAX_QUERY_LENGTH) {
    return { ok: false, status: 400, error: `query exceeds ${MAX_QUERY_LENGTH} characters` };
  }
  if (!["true", "false"].includes(publish)) {
    return { ok: false, status: 400, error: "publish must be true or false" };
  }

  return { ok: true, task, query, publish };
}

async function githubFetch(cfg, path, init = {}) {
  const headers = {
    Accept: "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "scbe-agent-vercel-bridge",
    ...(init.headers || {}),
  };
  if (cfg.githubToken) headers.Authorization = `Bearer ${cfg.githubToken}`;

  return fetch(`https://api.github.com/repos/${cfg.repo}${path}`, {
    ...init,
    headers,
  });
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`fetch ${url} failed with ${response.status}`);
  }
  return response.json();
}

module.exports = {
  ALLOWED_TASKS,
  MAX_QUERY_LENGTH,
  authOk,
  envConfig,
  fetchJson,
  githubFetch,
  readJsonBody,
  sendJson,
  setCors,
  validateTaskInput,
};
