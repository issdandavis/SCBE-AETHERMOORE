#!/usr/bin/env node
import http from "node:http";
import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const args = process.argv.slice(2);
const readArg = (flag, fallback) => {
  const idx = args.indexOf(flag);
  if (idx === -1 || idx + 1 >= args.length) return fallback;
  return args[idx + 1];
};

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");

const rootDir = path.resolve(readArg("--root", path.join(repoRoot, "kindle-app", "www")));
const host = readArg("--host", "0.0.0.0");
const port = Number.parseInt(readArg("--port", "8088"), 10);

const MIME = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".svg", "image/svg+xml"],
  [".png", "image/png"],
  [".jpg", "image/jpeg"],
  [".jpeg", "image/jpeg"],
  [".ico", "image/x-icon"],
  [".txt", "text/plain; charset=utf-8"],
  [".webmanifest", "application/manifest+json; charset=utf-8"],
]);

const safeResolve = (reqPath) => {
  const clean = reqPath.split("?")[0].split("#")[0];
  const decoded = decodeURIComponent(clean || "/");
  const trimmed = decoded.startsWith("/") ? decoded.slice(1) : decoded;
  const resolved = path.resolve(rootDir, trimmed || "index.html");
  if (!resolved.startsWith(rootDir)) return null;
  return resolved;
};

const send = (res, status, body, contentType = "text/plain; charset=utf-8") => {
  res.writeHead(status, { "Content-Type": contentType });
  res.end(body);
};

const server = http.createServer(async (req, res) => {
  if (!req.url) {
    send(res, 400, "Bad request");
    return;
  }

  let filePath = safeResolve(req.url);
  if (!filePath) {
    send(res, 403, "Forbidden");
    return;
  }

  try {
    let stat = await fs.stat(filePath);
    if (stat.isDirectory()) {
      filePath = path.join(filePath, "index.html");
      stat = await fs.stat(filePath);
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME.get(ext) || "application/octet-stream";
    const content = await fs.readFile(filePath);
    res.writeHead(200, { "Content-Type": contentType });
    res.end(content);
  } catch {
    const fallback = path.join(rootDir, "index.html");
    try {
      const content = await fs.readFile(fallback);
      res.writeHead(200, { "Content-Type": "text/html; charset=utf-8" });
      res.end(content);
    } catch {
      send(res, 404, "Not found");
    }
  }
});

server.listen(port, host, () => {
  console.log(
    JSON.stringify(
      {
        ok: true,
        root: rootDir,
        host,
        port,
        url: `http://${host}:${port}/index.html`,
      },
      null,
      2,
    ),
  );
});
