#!/usr/bin/env node
/**
 * bench_semantic_sphere.cjs
 *
 * Benchmarks the live surfaces of:
 *   A) Semantic Bridge (48-bit hex/binary encoder in packages/agent-bus)
 *      decompose, recompose, analyzeDimensions, dimsToHex, hexToDims,
 *      dimsToBinary, scoreDialogue
 *
 *   B) Cross-Build Quasi-Sphere (src/harmonic → packages/kernel, cross-built)
 *      createQuasiSphere, computeOverlap, squadOverlapMatrix, sharedContextRadius,
 *      padAccessibilityMap (light), consensusGradient, gradientAgreement,
 *      computeSlice (low-res), extractZeroSets, simulateDrift2D (short)
 *
 * Output:
 *   packages/agent-bus/docs/benchmarks/semantic_sphere_<timestamp>.json
 *   packages/agent-bus/docs/SEMANTIC_SPHERE_BENCH.md  (latest snapshot)
 *
 * Usage:
 *   node packages/agent-bus/scripts/bench_semantic_sphere.cjs
 *   node packages/agent-bus/scripts/bench_semantic_sphere.cjs --runs 50
 *   node packages/agent-bus/scripts/bench_semantic_sphere.cjs --no-sphere
 *
 * Prerequisites: npm run build (root) + npm run build (packages/agent-bus)
 */

'use strict';

const path = require('node:path');
const fs = require('node:fs');
const os = require('node:os');

const REPO_ROOT = path.resolve(__dirname, '..', '..', '..');
const PKG_ROOT = path.resolve(__dirname, '..');

// ── Load surfaces ─────────────────────────────────────────────────────────────

function loadOrFail(filePath, label) {
  try {
    return require(filePath);
  } catch (e) {
    process.stderr.write(
      `ERROR: Cannot load ${label} from ${filePath}.\n` +
        `Run: npm run build && cd packages/agent-bus && npm run build\n` +
        `  ${e.message}\n`
    );
    process.exit(1);
  }
}

const bus = loadOrFail(path.join(PKG_ROOT, 'dist', 'index.js'), 'agent-bus dist');
const {
  decompose,
  recompose,
  analyzeDimensions,
  dimsToHex,
  hexToDims,
  dimsToBinary,
  scoreDialogue,
} = bus;

const args = process.argv.slice(2);
const noSphere = args.includes('--no-sphere');
const RUNS = (() => {
  const r = args.find((a) => a.startsWith('--runs=') || a === '--runs');
  if (!r) return 20;
  if (r.includes('=')) return parseInt(r.split('=')[1], 10);
  const idx = args.indexOf('--runs');
  return parseInt(args[idx + 1], 10) || 20;
})();

let sphereOverlap = null;
let sphereSlice = null;

if (!noSphere) {
  const sphereOverlapPath = path.join(
    REPO_ROOT,
    'dist',
    'src',
    'harmonic',
    'quasiSphereOverlap.js'
  );
  const sphereSlicePath = path.join(REPO_ROOT, 'dist', 'src', 'harmonic', 'quasiSphereSlice.js');

  if (!fs.existsSync(sphereOverlapPath)) {
    process.stderr.write(
      `WARNING: quasiSphereOverlap.js not found at ${sphereOverlapPath}.\n` +
        `Run: npm run build from repo root. Sphere benchmarks will be skipped.\n`
    );
  } else {
    sphereOverlap = loadOrFail(sphereOverlapPath, 'quasiSphereOverlap');
    sphereSlice = loadOrFail(sphereSlicePath, 'quasiSphereSlice');
  }
}

// ── Timing harness ────────────────────────────────────────────────────────────

function bench(label, fn, runs = RUNS) {
  const times = [];
  let result;
  let error = null;
  for (let i = 0; i < runs; i++) {
    const t0 = performance.now();
    try {
      result = fn();
    } catch (e) {
      error = e.message || String(e);
      break;
    }
    times.push(performance.now() - t0);
  }
  if (times.length === 0) {
    return { label, ok: false, error, runs: 0, mean_us: null, min_us: null, max_us: null };
  }
  times.sort((a, b) => a - b);
  const mean = times.reduce((s, t) => s + t, 0) / times.length;
  return {
    label,
    ok: true,
    error: null,
    runs: times.length,
    mean_us: Math.round(mean * 1000),
    min_us: Math.round(times[0] * 1000),
    max_us: Math.round(times[times.length - 1] * 1000),
    p50_us: Math.round(times[Math.floor(times.length * 0.5)] * 1000),
  };
}

// ── Test corpus ───────────────────────────────────────────────────────────────

const SAMPLES = {
  governance: 'but actually the command was blocked and denied — this is an error',
  code: 'transform the input data to compile and convert it to the output format',
  dialogue:
    "let me explain. i remember when I was there and I've seen this. for example consider this: however, that said, but wait",
  numeric: '3.14159 hyperbolic distance 42 vectors 256',
  empty: '',
};

const ATOM_COMBOS = [
  ['BLOCK', 'FLOW'],
  ['TRANSFORM', 'FLOW'],
  ['ANNOUNCE', 'EXPAND'],
  ['PIVOT', 'BLOCK'],
  ['CARRY', 'EXPAND'],
];

// ── Run: Semantic Bridge ──────────────────────────────────────────────────────

const semanticResults = [];

// decompose
for (const [name, text] of Object.entries(SAMPLES)) {
  semanticResults.push(
    bench(`decompose:${name}`, () => {
      const r = decompose(text);
      if (r.schemaVersion !== 'scbe-decomposition-v1') throw new Error('bad schema');
      if (typeof r.combinedHex !== 'string' || r.combinedHex.length !== 12)
        throw new Error(`bad hex: ${r.combinedHex}`);
      if (typeof r.combinedBinary !== 'string' || r.combinedBinary.split(' ').length !== 6)
        throw new Error(`bad binary: ${r.combinedBinary}`);
      return r;
    })
  );
}

// recompose round-trip
const sampleDecomped = decompose(SAMPLES.governance);
semanticResults.push(
  bench('recompose:governance_hex', () => {
    const r = recompose(sampleDecomped.combinedHex);
    if (r.schemaVersion !== 'scbe-recomposition-v1') throw new Error('bad schema');
    return r;
  })
);

// analyzeDimensions
for (const combo of ATOM_COMBOS) {
  semanticResults.push(
    bench(`analyzeDimensions:${combo.join('+')}`, () => {
      const r = analyzeDimensions(combo);
      if (r.schemaVersion !== 'scbe-dim-analysis-v1') throw new Error('bad schema');
      if (typeof r.dominantAxis !== 'string') throw new Error('no dominantAxis');
      return r;
    })
  );
}

// dimsToHex / hexToDims round-trip
semanticResults.push(
  bench('dimsToHex:round_trip', () => {
    const original = [0.85, 0.1, 0.9, 0.88, 0.8, 0.05];
    const hex = dimsToHex(original);
    if (hex.length !== 12) throw new Error('hex length not 12');
    const decoded = hexToDims(hex);
    if (decoded.length !== 6) throw new Error('decoded length not 6');
    // Quantization: each value should be within 1/255 ≈ 0.004 of original
    for (let i = 0; i < 6; i++) {
      if (Math.abs(decoded[i] - original[i]) > 1 / 255 + 0.001)
        throw new Error(`dim ${i} drift: ${decoded[i]} vs ${original[i]}`);
    }
    return { hex, decoded };
  })
);

// dimsToBinary
semanticResults.push(
  bench('dimsToBinary:format', () => {
    const dims = [0.85, 0.1, 0.9, 0.88, 0.8, 0.05];
    const b = dimsToBinary(dims);
    const parts = b.split(' ');
    if (parts.length !== 6) throw new Error('not 6 groups');
    for (const p of parts) {
      if (p.length !== 8) throw new Error(`group not 8 bits: ${p}`);
      if (!/^[01]+$/.test(p)) throw new Error(`non-binary: ${p}`);
    }
    return b;
  })
);

// scoreDialogue
for (const [name, text] of Object.entries(SAMPLES)) {
  if (name === 'empty' || name === 'numeric') continue; // skip trivial
  semanticResults.push(
    bench(`scoreDialogue:${name}`, () => {
      const r = scoreDialogue(text);
      if (r.schemaVersion !== 'scbe-dialogue-score-v1') throw new Error('bad schema');
      if (r.total < 0 || r.total > r.max)
        throw new Error(`score out of range: ${r.total}/${r.max}`);
      return r;
    })
  );
}

// ── Run: Quasi-Sphere ─────────────────────────────────────────────────────────

const sphereResults = [];

if (sphereOverlap && sphereSlice) {
  const {
    createQuasiSphere,
    computeOverlap,
    squadOverlapMatrix,
    sharedContextRadius,
    padAccessibilityMap,
    consensusGradient,
    gradientAgreement,
  } = sphereOverlap;

  const { computeSlice, extractZeroSets, simulateDrift2D } = sphereSlice;

  // Minimal CHSFN state (only needs position + phase + mass)
  const makeState = (offset = 0) => ({
    position: [
      0.1 + offset,
      0.05 + offset,
      0.08 + offset,
      0.12 + offset,
      0.06 + offset,
      0.09 + offset,
    ],
    phase: [0, Math.PI / 3, (2 * Math.PI) / 3, Math.PI, (4 * Math.PI) / 3, (5 * Math.PI) / 3],
    mass: 1.0,
  });

  const states = [makeState(0), makeState(0.05), makeState(0.1)];
  const spheres = states.map((s, i) => createQuasiSphere(`unit-${i}`, s, 0.7 + i * 0.05));

  sphereResults.push(
    bench('createQuasiSphere', () => {
      const s = createQuasiSphere('bench', makeState(), 0.8);
      if (typeof s.trustRadius !== 'number') throw new Error('no trustRadius');
      return s;
    })
  );

  sphereResults.push(
    bench('computeOverlap', () => {
      const r = computeOverlap(spheres[0], spheres[1]);
      if (typeof r.overlaps !== 'boolean') throw new Error('no overlaps field');
      if (typeof r.phaseCoherence !== 'number') throw new Error('no phaseCoherence');
      return r;
    })
  );

  sphereResults.push(
    bench('squadOverlapMatrix:3x3', () => {
      const m = squadOverlapMatrix(spheres);
      if (m.size !== 3) throw new Error(`expected 3 pairs, got ${m.size}`);
      return m;
    })
  );

  sphereResults.push(
    bench('sharedContextRadius:3_units', () => {
      return sharedContextRadius(spheres);
    })
  );

  sphereResults.push(
    bench('padAccessibilityMap:sampleCount=20', () => {
      const center = [0.1, 0.05, 0.08, 0.12, 0.06, 0.09];
      const m = padAccessibilityMap(center, 0.8, 20); // 20 samples for bench speed
      if (m.size !== 6) throw new Error(`expected 6 modes, got ${m.size}`);
      return m;
    })
  );

  const gradients = [
    [0.1, 0.0, 0.2, 0.0, 0.1, 0.0],
    [0.09, 0.01, 0.18, 0.01, 0.12, 0.01],
    [0.11, 0.0, 0.22, 0.0, 0.08, 0.0],
  ];

  sphereResults.push(
    bench('consensusGradient:3_units', () => {
      const cg = consensusGradient(gradients);
      if (cg.length !== 6) throw new Error('not a 6-vec');
      return cg;
    })
  );

  sphereResults.push(
    bench('gradientAgreement:3_units', () => {
      const ga = gradientAgreement(gradients);
      if (ga < 0 || ga > 1) throw new Error(`out of [0,1]: ${ga}`);
      return ga;
    })
  );

  // Sphere slice — low-res so it's fast
  const axes = { dimA: 0, dimB: 1, fixed: [0, 0, 0.08, 0.12, 0.06, 0.09] };

  sphereResults.push(
    bench(
      'computeSlice:20x20',
      () => {
        const s = computeSlice(axes, 20);
        if (s.resolution !== 20) throw new Error('resolution mismatch');
        if (s.grid.length !== 20) throw new Error('grid rows mismatch');
        return s;
      },
      Math.min(RUNS, 5)
    ) // cap at 5 — slice is expensive
  );

  // extractZeroSets from a pre-computed slice
  const referenceSlice = computeSlice(axes, 20);
  sphereResults.push(
    bench('extractZeroSets', () => {
      const pts = extractZeroSets(referenceSlice);
      if (!Array.isArray(pts)) throw new Error('not an array');
      return pts;
    })
  );

  sphereResults.push(
    bench('simulateDrift2D:10_steps', () => {
      const path = simulateDrift2D(axes, 0.1, 0.1, 10, 0.005);
      if (!Array.isArray(path)) throw new Error('not an array');
      if (path.length < 1) throw new Error('empty path');
      return path;
    })
  );
} else {
  sphereResults.push({
    label: 'sphere:SKIPPED',
    ok: false,
    error: 'quasiSphereOverlap.js not found — run npm run build from repo root',
    runs: 0,
    mean_us: null,
  });
}

// ── Gap inventory ─────────────────────────────────────────────────────────────

const GAPS = [
  {
    id: 'GAP-1',
    title: 'Atomic-tokenizer tooling',
    description:
      'The semantic bridge uses substring form-matching (greedy overlap). ' +
      'There is no sub-word tokenizer that maps Sacred Tongue atoms to atomic token IDs. ' +
      'The decompose() engine cannot yet participate in a BPE/WordPiece vocabulary — ' +
      'atom boundaries are only detected by regex surface forms, not by model-level token splits. ' +
      'Required: an atomic tokenizer that assigns stable integer IDs to each atom and produces ' +
      'token-level hex fingerprints compatible with the 48-bit encoding.',
    status: 'open',
    priority: 'high',
  },
  {
    id: 'GAP-2',
    title: 'Tier-2 arbitrary AST compilation',
    description:
      'analyzeDimensions() accepts only named atom IDs from ATOM_TABLE. ' +
      'There is no Tier-2 compiler that takes an arbitrary AST (e.g. a TypeScript or Python ' +
      'parse tree) and maps it to a DimVec. The current surface is limited to the 10 named atoms ' +
      '(4 domain + 6 discourse). A Tier-2 compiler would: (1) walk the AST, (2) classify each ' +
      'node as a domain or discourse atom using structural heuristics, (3) aggregate DimVecs with ' +
      'valence-weighted combination, and (4) emit a combinedHex that acts as a semantic fingerprint ' +
      'for the whole file/module. This would enable cross-file similarity search.',
    status: 'open',
    priority: 'high',
  },
  {
    id: 'GAP-3',
    title: 'Sphere ↔ bridge binding layer',
    description:
      'The quasi-sphere (quasiSphereOverlap/Slice) operates on CHSFNState (Poincaré positions). ' +
      'The semantic bridge operates on DimVec (6D Sacred Tongue axes). ' +
      'There is no binding layer that maps a DecompositionResult.combinedDims to a CHSFNState.position, ' +
      'or that uses a sphere overlap result to gate semantic similarity routing. ' +
      'Required: a DimVec → CHSFNState adapter that preserves ball containment (||x|| < 1).',
    status: 'open',
    priority: 'medium',
  },
];

// ── Aggregate results ─────────────────────────────────────────────────────────

const allResults = [...semanticResults, ...sphereResults];
const passed = allResults.filter((r) => r.ok).length;
const failed = allResults.filter((r) => !r.ok).length;
const totalRuns = allResults.reduce((s, r) => s + r.runs, 0);

const artifact = {
  schema: 'scbe.agent_bus.semantic_sphere_bench.v1',
  generated_at: new Date().toISOString(),
  platform: process.platform,
  node_version: process.version,
  arch: os.arch(),
  runs_per_surface: RUNS,
  score: { passed, failed, total: allResults.length },
  total_benchmark_runs: totalRuns,
  semantic_bridge: semanticResults,
  quasi_sphere: sphereResults,
  gaps: GAPS,
};

// ── Write JSON artifact ───────────────────────────────────────────────────────

const DOCS_BENCH = path.join(PKG_ROOT, 'docs', 'benchmarks');
if (!fs.existsSync(DOCS_BENCH)) fs.mkdirSync(DOCS_BENCH, { recursive: true });

const stamp = new Date().toISOString().replace(/[:.]/g, '-');
const jsonPath = path.join(DOCS_BENCH, `semantic_sphere_${stamp}.json`);
fs.writeFileSync(jsonPath, JSON.stringify(artifact, null, 2));

// ── Write MD snapshot ─────────────────────────────────────────────────────────

function mdRow(r) {
  const status = r.ok ? '✓' : '✗';
  const mean = r.mean_us != null ? `${r.mean_us} µs` : '—';
  const min = r.min_us != null ? `${r.min_us} µs` : '—';
  const max = r.max_us != null ? `${r.max_us} µs` : '—';
  const err = r.error ? ` ⚠ ${r.error.slice(0, 60)}` : '';
  return `| ${status} | \`${r.label}\` | ${r.runs} | ${mean} | ${min} | ${max} |${err}`;
}

function renderTable(results) {
  const hdr =
    '| OK | Surface | Runs | Mean | Min | Max |\n' + '|----|---------|------|------|-----|-----|';
  return [hdr, ...results.map(mdRow)].join('\n');
}

const md = `# Semantic Sphere Benchmark — ${artifact.generated_at.slice(0, 19)}Z

> Auto-generated by \`bench_semantic_sphere.cjs\`. Do not edit manually.

**Score**: ${passed}/${allResults.length} surfaces passing  ${failed > 0 ? `⚠ ${failed} failed` : ''}
**Runs per surface**: ${RUNS}  Total benchmark iterations: ${totalRuns}
**Platform**: ${process.platform} / ${os.arch()} / Node ${process.version}

---

## A. Semantic Bridge (48-bit hex/binary encoder)

${renderTable(semanticResults)}

### Key semantics
- \`decompose(input)\` → \`combinedHex\` (12-char, 6 bytes, 48 bits) + \`combinedBinary\` (space-separated by axis)
- \`recompose(hex)\` → nearest atom by cosine similarity in 6D Sacred Tongue space
- \`analyzeDimensions(atomIds)\` → consistency check + dominant axis
- \`dimsToHex\` / \`hexToDims\` are exact inverses up to 8-bit quantization (≤1/255 drift per axis)
- \`scoreDialogue(input)\` → 7-dimension spoken-longform rubric (total 10)

---

## B. Cross-Build Quasi-Sphere

Cross-built surface: lives in \`packages/kernel/src/\`, re-exported from \`src/harmonic/\`.

${renderTable(sphereResults)}

### Key semantics
- \`createQuasiSphere\` derives \`trustRadius = -ln(1 - coherence)\`
- \`computeOverlap\` gates shared context on distance + phase coherence ≥ threshold
- \`padAccessibilityMap\` — gold-angle sampling; 100 probes default, use 20 for bench speed
- \`computeSlice\` — expensive at high res; 20×20 used here for bench, 50×50 for visualization

---

## Open Gaps

${GAPS.map(
  (g) => `### ${g.id}: ${g.title}
**Status**: ${g.status}  **Priority**: ${g.priority}

${g.description}
`
).join('\n')}

---

*JSON artifact*: \`docs/benchmarks/semantic_sphere_${stamp}.json\`
`;

const mdPath = path.join(PKG_ROOT, 'docs', 'SEMANTIC_SPHERE_BENCH.md');
fs.writeFileSync(mdPath, md);

// ── Console summary ───────────────────────────────────────────────────────────

const hr = '─'.repeat(80);
console.log(`\n${hr}`);
console.log('SEMANTIC SPHERE BENCH — Surface Exercise Report');
console.log(hr);

for (const r of allResults) {
  const tag = r.ok ? '[PASS]' : '[FAIL]';
  const t = r.mean_us != null ? `  mean=${r.mean_us}µs` : '';
  const e = r.error ? `  ERR: ${r.error.slice(0, 60)}` : '';
  console.log(`  ${tag}  ${r.label}${t}${e}`);
}

console.log(hr);
console.log(`\nScore: ${passed}/${allResults.length}   total_runs: ${totalRuns}`);
console.log(`\nGaps (${GAPS.length}):`);
for (const g of GAPS) {
  console.log(`  [${g.priority.toUpperCase()}] ${g.id}: ${g.title}`);
}
console.log(`\nJSON  → ${jsonPath}`);
console.log(`MD    → ${mdPath}`);
console.log(hr);

process.exit(failed > 0 ? 1 : 0);
