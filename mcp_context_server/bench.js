'use strict';

/**
 * SCBE MCP Context Server — benchmark harness.
 *
 * Measures per-tool latency under repeated calls. Writes a JSON
 * report to artifacts/mcp_context_bench/ that captures p50/p95/p99
 * for each tool against a fixed mix of queries.
 *
 * Run:
 *   node mcp_context_server/bench.js
 *   node mcp_context_server/bench.js --iters 200
 */

const fs = require('fs');
const path = require('path');
const { performance } = require('perf_hooks');

const ctx = require('./server.js');

const REPO_ROOT = ctx.REPO_ROOT;
const DOC_ROOTS = ctx.DOC_ROOTS;
const REPORT_DIR = path.join(REPO_ROOT, 'artifacts', 'mcp_context_bench');
const DEFAULT_ITERS = 100;
const DEFAULT_WARMUP = 10;

function utcStamp() {
  return new Date().toISOString().replace(/[-:]/g, '').replace(/\..*/, 'Z');
}

function quantiles(values) {
  if (!values.length) return { mean: 0, p50: 0, p95: 0, p99: 0, max: 0, min: 0 };
  const sorted = [...values].sort((a, b) => a - b);
  const at = (q) => sorted[Math.min(sorted.length - 1, Math.floor(q * sorted.length))];
  const mean = sorted.reduce((s, v) => s + v, 0) / sorted.length;
  return {
    mean: round(mean),
    p50: round(at(0.5)),
    p95: round(at(0.95)),
    p99: round(at(0.99)),
    max: round(sorted[sorted.length - 1]),
    min: round(sorted[0]),
    n: sorted.length,
  };
}

function round(n) {
  return Math.round(n * 1000) / 1000;
}

async function timed(fn, iters) {
  const samples = [];
  for (let i = 0; i < iters; i++) {
    const t0 = performance.now();
    try {
      await fn();
    } catch (_err) {
      // measure error path too — error handling is part of the cost.
    }
    samples.push(performance.now() - t0);
  }
  return samples;
}

const SCENARIOS = [
  {
    id: 'list_docs_all',
    label: 'list_docs (no prefix)',
    fn: () => {
      const files = DOC_ROOTS.flatMap((root) => ctx.listMarkdownFiles(root));
      return files.length;
    },
  },
  {
    id: 'list_docs_prefix',
    label: 'list_docs (prefix=docs/specs/)',
    fn: () => {
      const files = ctx.listMarkdownFiles(path.join(REPO_ROOT, 'docs'));
      return files.filter((f) => f.startsWith('docs/specs/')).length;
    },
  },
  {
    id: 'read_doc_one_pager',
    label: 'read_doc (one-pager)',
    fn: () => ctx.readDocStrict('docs/SCBE_AETHERMOORE_ONE_PAGER.md'),
  },
  {
    id: 'search_docs_common',
    label: 'search_docs (common term: "the")',
    fn: () => ctx.searchDocs('the', 25),
  },
  {
    id: 'search_docs_rare',
    label: 'search_docs (rare term: "Poincare")',
    fn: () => ctx.searchDocs('Poincare', 25),
  },
  {
    id: 'search_docs_specific',
    label: 'search_docs (specific: "AetherDesk")',
    fn: () => ctx.searchDocs('AetherDesk', 25),
  },
  {
    id: 'search_docs_unique',
    label: 'search_docs (likely-unique: "harmonicScaling")',
    fn: () => ctx.searchDocs('harmonicScaling', 25),
  },
  {
    id: 'search_docs_zero_hits',
    label: 'search_docs (no-match: "zzqxqzz_unique")',
    fn: () => ctx.searchDocs('zzqxqzz_unique', 25),
  },
];

async function runBench({ iters, warmup }) {
  const started = new Date().toISOString();
  const results = [];

  for (const scenario of SCENARIOS) {
    process.stdout.write(`[bench] ${scenario.id}: warmup x${warmup}... `);
    await timed(scenario.fn, warmup);
    process.stdout.write(`measure x${iters}... `);
    const samples = await timed(scenario.fn, iters);
    const stats = quantiles(samples);
    results.push({
      id: scenario.id,
      label: scenario.label,
      stats_ms: stats,
    });
    process.stdout.write(`p50=${stats.p50}ms p95=${stats.p95}ms\n`);
  }

  const finished = new Date().toISOString();
  return {
    schema: 'mcp_context_bench_v1',
    started_at: started,
    finished_at: finished,
    node_version: process.version,
    repo_root: REPO_ROOT,
    iters,
    warmup,
    docs_count_at_run: countDocs(),
    scenarios: results,
  };
}

function countDocs() {
  const counts = {};
  let total = 0;
  for (const root of DOC_ROOTS) {
    const name = path.relative(REPO_ROOT, root).replace(/\\/g, '/') || path.basename(root);
    const n = ctx.listMarkdownFiles(root).length;
    counts[name] = n;
    total += n;
  }
  counts.total = total;
  return counts;
}

function parseArgs(argv) {
  const args = { iters: DEFAULT_ITERS, warmup: DEFAULT_WARMUP };
  for (let i = 2; i < argv.length; i++) {
    if (argv[i] === '--iters') args.iters = Number(argv[++i] || DEFAULT_ITERS);
    if (argv[i] === '--warmup') args.warmup = Number(argv[++i] || DEFAULT_WARMUP);
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv);
  const report = await runBench(args);

  fs.mkdirSync(REPORT_DIR, { recursive: true });
  const out = path.join(REPORT_DIR, `bench_${utcStamp()}.json`);
  fs.writeFileSync(out, JSON.stringify(report, null, 2) + '\n');

  console.log('');
  console.log(`Report: ${path.relative(REPO_ROOT, out)}`);
  console.log(`Docs at run: ${report.docs_count_at_run.total}`);
  console.log('');
  console.log(
    'Scenario'.padEnd(50) +
      'p50'.padStart(9) +
      'p95'.padStart(9) +
      'p99'.padStart(9) +
      'max'.padStart(9)
  );
  for (const s of report.scenarios) {
    const r = s.stats_ms;
    console.log(
      s.label.padEnd(50) +
        `${r.p50}ms`.padStart(9) +
        `${r.p95}ms`.padStart(9) +
        `${r.p99}ms`.padStart(9) +
        `${r.max}ms`.padStart(9)
    );
  }
}

if (require.main === module) {
  main().catch((err) => {
    console.error(err);
    process.exit(1);
  });
}

module.exports = { runBench, quantiles };
