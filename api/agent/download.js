"use strict";

const { sendJson, setCors } = require("../_agent_common");

const PRODUCTS = {
  toolkit: {
    envUrl: "SCBE_TOOLKIT_BLOB_URL",
    filename: "SCBE_AI_Governance_Toolkit_v1.zip",
  },
  vault: {
    envUrl: "SCBE_VAULT_BLOB_URL",
    filename: "SCBE_AI_Security_Training_Vault_v1.zip",
  },
};

function resolveProduct(req) {
  const rawUrl = new URL(req.url || "/api/agent/download", "https://scbe-agent-bridge-vercel.vercel.app");
  return String(rawUrl.searchParams.get("product") || "").trim().toLowerCase();
}

function resolveToken(req) {
  const rawUrl = new URL(req.url || "/api/agent/download", "https://scbe-agent-bridge-vercel.vercel.app");
  const queryToken = String(rawUrl.searchParams.get("token") || "").trim();
  const bearer = String(req.headers.authorization || "").replace(/^Bearer\s+/i, "").trim();
  return queryToken || bearer;
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "GET" && req.method !== "HEAD") {
    return sendJson(res, 405, { status: "error", error: "GET required" });
  }

  const expectedToken = String(process.env.SCBE_DELIVERY_TOKEN || "").trim();
  if (!expectedToken) {
    return sendJson(res, 503, { status: "error", error: "delivery token is not configured" });
  }

  const providedToken = resolveToken(req);
  if (!providedToken || providedToken !== expectedToken) {
    return sendJson(res, 401, { status: "error", error: "unauthorized" });
  }

  const productKey = resolveProduct(req);
  const product = PRODUCTS[productKey];
  if (!product) {
    return sendJson(res, 400, { status: "error", error: "product must be toolkit or vault" });
  }

  const blobUrl = String(process.env[product.envUrl] || "").trim();
  const blobToken = String(process.env.BLOB_READ_WRITE_TOKEN || "").trim();
  if (!blobUrl || !blobToken) {
    return sendJson(res, 503, { status: "error", error: "blob delivery is not configured" });
  }

  const upstream = await fetch(blobUrl, {
    method: req.method,
    headers: { Authorization: `Bearer ${blobToken}` },
  });
  if (!upstream.ok) {
    return sendJson(res, upstream.status, { status: "error", error: "blob fetch failed" });
  }

  res.setHeader("Content-Type", upstream.headers.get("content-type") || "application/zip");
  res.setHeader("Content-Disposition", `attachment; filename="${product.filename}"`);
  res.setHeader("Cache-Control", "private, no-store");
  res.setHeader("X-Content-Type-Options", "nosniff");
  if (req.method === "HEAD") return res.status(200).end();

  const body = Buffer.from(await upstream.arrayBuffer());
  return res.status(200).send(body);
};
