#!/usr/bin/env node
/**
 * HYDRA Terminal Browse (Node.js)
 * Deterministic page extraction for terminal-first workflows.
 */

import fs from "node:fs";
import path from "node:path";
import { URL } from "node:url";

function parseArgs(argv) {
  const out = {
    url: "",
    out: "",
    timeout: 15000,
    maxChars: 6000,
    maxLinks: 30,
    userAgent: "hydra-terminal-browse/1.0 (+SCBE-AETHERMOORE)",
  };

  for (let i = 2; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === "--help" || a === "-h") {
      out.help = true;
      break;
    }
    if (a === "--url") out.url = argv[++i] ?? "";
    else if (a === "--out") out.out = argv[++i] ?? "";
    else if (a === "--timeout") out.timeout = Number(argv[++i] ?? out.timeout);
    else if (a === "--max-chars") out.maxChars = Number(argv[++i] ?? out.maxChars);
    else if (a === "--max-links") out.maxLinks = Number(argv[++i] ?? out.maxLinks);
    else if (a === "--user-agent") out.userAgent = argv[++i] ?? out.userAgent;
    else if (!out.url && !a.startsWith("--")) out.url = a;
  }
  return out;
}

function printHelp() {
  console.log(`
HYDRA Terminal Browse (Node.js)

Usage:
  node hydra_terminal_browse.mjs --url "https://example.com"
  node hydra_terminal_browse.mjs --url "https://example.com" --out artifacts/page.json

Options:
  --url <url>           Target URL (required)
  --out <path>          Write JSON output to file (optional)
  --timeout <ms>        Request timeout in ms (default: 15000)
  --max-chars <n>       Max excerpt characters (default: 6000)
  --max-links <n>       Max extracted links (default: 30)
  --user-agent <value>  HTTP User-Agent
  --help, -h            Show help
`);
}

function decodeEntities(s) {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&nbsp;/g, " ");
}

function extractTitle(html) {
  const m = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  return m ? decodeEntities(m[1].trim()) : "";
}

function stripHtml(html) {
  let s = html;
  s = s.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ");
  s = s.replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ");
  s = s.replace(/<noscript\b[^>]*>[\s\S]*?<\/noscript>/gi, " ");
  s = s.replace(/<[^>]+>/g, " ");
  s = decodeEntities(s);
  s = s.replace(/\s+/g, " ").trim();
  return s;
}

function extractLinks(html, baseUrl, maxLinks) {
  const links = [];
  const seen = new Set();
  const re = /<a\b[^>]*\bhref\s*=\s*["']([^"']+)["'][^>]*>/gi;
  let m;
  while ((m = re.exec(html)) !== null) {
    const raw = m[1]?.trim();
    if (!raw) continue;
    if (raw.startsWith("#") || raw.toLowerCase().startsWith("javascript:")) continue;
    let abs = "";
    try {
      abs = new URL(raw, baseUrl).toString();
    } catch {
      continue;
    }
    if (!seen.has(abs)) {
      seen.add(abs);
      links.push(abs);
      if (links.length >= maxLinks) break;
    }
  }
  return links;
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help || !args.url) {
    printHelp();
    process.exit(args.help ? 0 : 1);
  }

  const controller = new AbortController();
  const t = setTimeout(() => controller.abort(), Math.max(1000, args.timeout));

  let res;
  let html = "";
  try {
    res = await fetch(args.url, {
      signal: controller.signal,
      headers: {
        "user-agent": args.userAgent,
        "accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
      },
      redirect: "follow",
    });
    html = await res.text();
  } catch (err) {
    clearTimeout(t);
    const out = {
      url: args.url,
      error: String(err?.message || err),
      fetched_at: new Date().toISOString(),
    };
    console.error(JSON.stringify(out, null, 2));
    process.exit(2);
  }
  clearTimeout(t);

  const title = extractTitle(html);
  const text = stripHtml(html);
  const excerpt = text.slice(0, Math.max(200, args.maxChars));
  const links = extractLinks(html, res.url || args.url, Math.max(1, args.maxLinks));

  const result = {
    url: args.url,
    resolved_url: res.url || args.url,
    status: res.status,
    title,
    text_excerpt: excerpt,
    links,
    metrics: {
      html_chars: html.length,
      text_chars: text.length,
      link_count: links.length,
      truncated: excerpt.length < text.length,
    },
    fetched_at: new Date().toISOString(),
  };

  if (args.out) {
    fs.mkdirSync(path.dirname(args.out), { recursive: true });
    fs.writeFileSync(args.out, JSON.stringify(result, null, 2), "utf8");
  }

  console.log(JSON.stringify(result, null, 2));
}

main();

