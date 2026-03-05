#!/usr/bin/env node
import fs from "fs";
import http from "http";
import path from "path";
import { fileURLToPath } from "url";
import { chromium } from "playwright";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");

const args = process.argv.slice(2);
const options = {
  webRoot: path.join(repoRoot, "kindle-app", "www"),
  outDir: path.join(repoRoot, "kindle-app", "store-assets", "screenshots"),
  width: 1024,
  height: 600,
};

for (let i = 0; i < args.length; i++) {
  const a = args[i];
  if (a === "--web-root" && args[i + 1]) options.webRoot = path.resolve(args[++i]);
  else if (a === "--out-dir" && args[i + 1]) options.outDir = path.resolve(args[++i]);
  else if (a === "--width" && args[i + 1]) options.width = Number(args[++i]);
  else if (a === "--height" && args[i + 1]) options.height = Number(args[++i]);
}

function ensureDir(p) {
  fs.mkdirSync(p, { recursive: true });
}

function contentType(filePath) {
  if (filePath.endsWith(".html")) return "text/html; charset=utf-8";
  if (filePath.endsWith(".js")) return "application/javascript; charset=utf-8";
  if (filePath.endsWith(".json")) return "application/json; charset=utf-8";
  if (filePath.endsWith(".css")) return "text/css; charset=utf-8";
  if (filePath.endsWith(".png")) return "image/png";
  if (filePath.endsWith(".jpg") || filePath.endsWith(".jpeg")) return "image/jpeg";
  if (filePath.endsWith(".svg")) return "image/svg+xml";
  return "application/octet-stream";
}

function startStaticServer(rootDir) {
  const server = http.createServer((req, res) => {
    const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
    let rel = urlPath === "/" ? "/index.html" : urlPath;
    const filePath = path.join(rootDir, rel);
    const normalized = path.normalize(filePath);
    if (!normalized.startsWith(path.normalize(rootDir))) {
      res.statusCode = 403;
      res.end("Forbidden");
      return;
    }
    if (!fs.existsSync(normalized) || fs.statSync(normalized).isDirectory()) {
      res.statusCode = 404;
      res.end("Not found");
      return;
    }
    const data = fs.readFileSync(normalized);
    res.setHeader("Content-Type", contentType(normalized));
    res.statusCode = 200;
    res.end(data);
  });
  return new Promise((resolve) => {
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      resolve({ server, port: address.port });
    });
  });
}

async function clickIfExists(page, selector) {
  try {
    const el = page.locator(selector).first();
    if (await el.count()) {
      await el.click({ timeout: 3000 });
      return true;
    }
  } catch (_) {
    return false;
  }
  return false;
}

async function main() {
  if (!fs.existsSync(options.webRoot)) {
    console.error(`web root not found: ${options.webRoot}`);
    process.exit(2);
  }
  ensureDir(options.outDir);
  const { server, port } = await startStaticServer(options.webRoot);
  const base = `http://127.0.0.1:${port}`;

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: options.width, height: options.height } });
  const page = await context.newPage();

  const shots = [];
  async function take(name, fn) {
    const outPath = path.join(options.outDir, name);
    await fn();
    await page.screenshot({ path: outPath, fullPage: true });
    shots.push(outPath);
  }

  try {
    await take("01-welcome-screen.png", async () => {
      await page.goto(`${base}/index.html`, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(1200);
    });

    await take("02-chat-mode.png", async () => {
      await page.goto(`${base}/arena.html`, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(2000);
    });

    await take("03-code-mode.png", async () => {
      await page.goto(`${base}/arena.html`, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(1200);
      await clickIfExists(page, "#sharedEditor");
      await page.waitForTimeout(500);
    });

    await take("04-research-mode.png", async () => {
      await page.goto(`${base}/arena.html`, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(1200);
      await clickIfExists(page, "#researchBtn");
      await page.waitForTimeout(2200);
    });

    await take("05-byok-keys-modal.png", async () => {
      await page.goto(`${base}/arena.html`, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(1200);
      await clickIfExists(page, "#settingsBtn");
      await page.waitForTimeout(500);
    });

    const report = {
      generated_at_utc: new Date().toISOString(),
      web_root: options.webRoot,
      out_dir: options.outDir,
      viewport: { width: options.width, height: options.height },
      screenshots: shots,
    };
    const reportPath = path.join(options.outDir, "screenshot_prep_report.json");
    fs.writeFileSync(reportPath, JSON.stringify(report, null, 2), "utf-8");
    console.log(JSON.stringify({ ok: true, report: reportPath, screenshots: shots }, null, 2));
  } finally {
    await context.close();
    await browser.close();
    server.close();
  }
}

main().catch((err) => {
  console.error(err instanceof Error ? err.stack || err.message : String(err));
  process.exit(1);
});
