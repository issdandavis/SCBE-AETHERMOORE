"use strict";

const { envConfig, fetchJson, sendJson, setCors } = require("../_agent_common");

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET") return sendJson(res, 405, { ok: false, error: "GET required" });

  const cfg = envConfig();
  const task = String(req.query.task || "").trim().toLowerCase();
  const base = cfg.pagesDataBase.replace(/\/$/, "");

  try {
    const index = await fetchJson(`${base}/index.json`);
    const tasks = index.tasks || {};

    if (task) {
      const entry = tasks[task];
      if (!entry) return sendJson(res, 404, { ok: false, error: `no latest result for task '${task}'`, index });
      const result = await fetchJson(`${base}/${entry.file}`);
      return sendJson(res, 200, {
        ok: true,
        mode: "latest",
        task,
        index_entry: entry,
        result,
      });
    }

    return sendJson(res, 200, {
      ok: true,
      mode: "latest-index",
      index,
      archive: {
        enabled: false,
        reason: "timestamped run archive is not implemented yet",
      },
    });
  } catch (error) {
    return sendJson(res, 502, {
      ok: false,
      error: error.message,
      pages_data_base: base,
    });
  }
};
