#!/usr/bin/env node
'use strict';

// Proves the router consolidation before it is pushed. Three checks, each of which maps
// to a real failure mode seen or risked in this repo:
//
// 1. FUNCTION COUNT — parse vercel.json builds, resolve each glob/file, count. The whole
//    point of the change is <= 12 on the Hobby plan; this is the number the plan gate reads.
// 2. EVERY ROUTE RESOLVES — walk every route dest. Static ?fn= names must exist in the
//    router map AND the handler file must actually require() (catches a typo'd map entry,
//    a deleted handler, or an import-time crash — which under lazy thunks would otherwise
//    surface as a runtime 500 in production, not at build).
// 3. ROUTER MAP IS CURRENT — regenerate the map from the directory and diff against what
//    is checked in, so adding a handler file without rerunning generate-router.cjs fails
//    loudly here instead of 404ing in production.
//
// Plus a live smoke: invoke each router in-process with a mock req/res for one cheap
// handler to prove the dispatch path end to end.

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const cfg = JSON.parse(fs.readFileSync(path.join(ROOT, 'vercel.json'), 'utf8'));
let failures = 0;

function fail(msg) {
  failures += 1;
  console.error(`FAIL  ${msg}`);
}

// ── 1. function count ─────────────────────────────────────────────────────────
const built = [];
for (const b of cfg.builds || []) {
  if (b.src.includes('*')) {
    // only the one glob shape ever used here: dir/*.js
    const dir = path.join(ROOT, path.dirname(b.src));
    for (const f of fs.readdirSync(dir))
      if (f.endsWith('.js')) built.push(`${path.dirname(b.src)}/${f}`);
  } else {
    built.push(b.src);
  }
}
console.log(`functions: ${built.length}  (${built.join(', ')})`);
if (built.length > 12) fail(`${built.length} functions exceeds the 12-function Hobby cap`);
for (const f of built)
  if (!fs.existsSync(path.join(ROOT, f))) fail(`build src missing on disk: ${f}`);

// ── 2. every route resolves ───────────────────────────────────────────────────
const requireOk = new Map();
function loads(rel) {
  if (!requireOk.has(rel)) {
    try {
      const handler = require(path.join(ROOT, rel));
      if (typeof handler !== 'function') {
        throw new TypeError('module does not export a request handler');
      }
      requireOk.set(rel, true);
    } catch (err) {
      requireOk.set(rel, `${err.name}: ${err.message}`);
    }
  }
  return requireOk.get(rel);
}

let checkedRoutes = 0;
for (const r of cfg.routes || []) {
  if (!r.dest) continue;
  const m = r.dest.match(/^\/api\/(agent|polly)\/router\.js\?fn=([^&]+)/);
  if (m) {
    const [, lane, fn] = m;
    if (fn.startsWith('$')) continue; // catch-all: dynamic name, router 404s unknowns
    const handler = `api/${lane}/${fn}.js`;
    if (!fs.existsSync(path.join(ROOT, handler)))
      fail(`route '${r.src}' -> fn=${fn} but ${handler} does not exist`);
    else {
      const ok = loads(handler);
      if (ok !== true) fail(`route '${r.src}' -> ${handler} fails to require: ${ok}`);
    }
    checkedRoutes += 1;
  } else if (/^\/api\/(agent|polly)\/[^?]+\.js/.test(r.dest)) {
    fail(`route '${r.src}' still points at a per-file function: ${r.dest}`);
  } else if (r.dest.startsWith('/api/billing/')) {
    const rel = r.dest.replace(/^\//, '').split('?')[0];
    if (!fs.existsSync(path.join(ROOT, rel))) fail(`billing route missing on disk: ${rel}`);
    checkedRoutes += 1;
  }
}
console.log(`routes resolved: ${checkedRoutes} static dests checked`);

// ── 3. router maps are current ────────────────────────────────────────────────
const HANDLER_EXPORT = /^module\.exports\s*=\s*(async\s+)?function/m;
const HELPER_ALLOWLIST = {
  agent: new Set(),
  polly: new Set(['commerce.js']),
};
for (const lane of ['agent', 'polly']) {
  const dir = path.join(ROOT, 'api', lane);
  const laneFiles = fs.readdirSync(dir).filter((f) => f.endsWith('.js') && f !== 'router.js');
  const expected = laneFiles
    .filter((f) => !f.startsWith('_'))
    .filter((f) => HANDLER_EXPORT.test(fs.readFileSync(path.join(dir, f), 'utf8')))
    .map((f) => f.slice(0, -3))
    .sort();
  const unexplained = laneFiles.filter(
    (f) =>
      !f.startsWith('_') &&
      !HELPER_ALLOWLIST[lane].has(f) &&
      !HANDLER_EXPORT.test(fs.readFileSync(path.join(dir, f), 'utf8'))
  );
  for (const file of unexplained) {
    fail(`api/${lane}/${file} is neither a request handler nor an allowlisted helper`);
  }
  const src = fs.readFileSync(path.join(dir, 'router.js'), 'utf8');
  // keys are unquoted when identifier-safe (prettier style), quoted otherwise
  const entries = [
    ...src.matchAll(
      /^ {2}(?:'([^']+)'|([A-Za-z0-9_$]+)): \(\) => require\('\.\/([^']+)\.js'\),$/gm
    ),
  ];
  const mapped = entries.map((m) => m[1] || m[2]).sort();
  for (const entry of entries) {
    const key = entry[1] || entry[2];
    const target = entry[3];
    if (key !== target) {
      fail(`api/${lane}/router.js maps '${key}' to './${target}.js'`);
    }
  }
  if (JSON.stringify(mapped) !== JSON.stringify(expected)) {
    const missing = expected.filter((n) => !mapped.includes(n));
    const stale = mapped.filter((n) => !expected.includes(n));
    fail(
      `api/${lane}/router.js map is out of date — rerun generate-router.cjs ` +
        `(missing: ${missing.join(',') || 'none'}; stale: ${stale.join(',') || 'none'})`
    );
  } else {
    console.log(`api/${lane}/router.js map current: ${mapped.length} handlers`);
  }
  for (const name of mapped) {
    const handler = `api/${lane}/${name}.js`;
    const ok = loads(handler);
    if (ok !== true) fail(`mapped handler ${handler} fails to require: ${ok}`);
  }
}

// ── smoke: dispatch through each router in-process ────────────────────────────
function mockRes() {
  const res = {
    statusCode: 200,
    headers: {},
    body: '',
    setHeader(k, v) {
      this.headers[k.toLowerCase()] = v;
    },
    getHeader(k) {
      return this.headers[k.toLowerCase()];
    },
    end(chunk) {
      if (chunk) this.body += chunk;
      this.finished = true;
      return this;
    },
    write(chunk) {
      this.body += chunk;
      return true;
    },
  };
  res.status = (c) => ((res.statusCode = c), res);
  res.json = (o) => res.end(JSON.stringify(o));
  res.send = (b) => res.end(typeof b === 'string' ? b : JSON.stringify(b));
  return res;
}

async function smoke(lane, fn, expectStatus, expectedBody, query = { fn }) {
  const router = require(path.join(ROOT, 'api', lane, 'router.js'));
  const res = mockRes();
  await router({ method: 'GET', url: `/api/${lane}/router.js?fn=${fn}`, headers: {}, query }, res);
  const statusOk = expectStatus.includes(res.statusCode);
  const finished = res.finished === true;
  const bodyOk = !expectedBody || res.body.includes(expectedBody);
  const ok = statusOk && finished && bodyOk;
  console.log(
    `smoke ${lane}/${fn || '(none)'} -> ${res.statusCode} ` +
      `${finished ? 'finished' : 'NO RESPONSE'} ${ok ? 'ok' : 'UNEXPECTED'}`
  );
  if (!statusOk)
    fail(
      `router ${lane} fn=${fn || '(none)'} returned ${res.statusCode}, wanted one of ${expectStatus}`
    );
  if (!finished) {
    fail(`router ${lane} fn=${fn || '(none)'} returned without completing the response`);
  }
  if (!bodyOk) {
    fail(`router ${lane} fn=${fn || '(none)'} response omitted '${expectedBody}'`);
  }
}

(async () => {
  await smoke('agent', 'health', [200], '"service":"scbe-agent-vercel-bridge"', {
    fn: ['health', 'status'],
  });
  await smoke('agent', 'dispatch', [405], 'POST required');
  await smoke('agent', 'no-such-handler', [404], '"error":"not_found"');
  await smoke('agent', '', [404], '"error":"not_found"');
  await smoke('polly', 'catalog', [200], '"products"');
  process.exitCode = failures ? 1 : 0;
  console.log(failures ? `\n${failures} FAILURE(S)` : '\nall checks passed');
})();
