#!/usr/bin/env node

const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { execFileSync } = require('node:child_process');

const ROOT = path.resolve(__dirname, '..');
const DEFAULT_WORKDIR = path.join(ROOT, 'docs', 'legal', 'patent-workbench');

const OFFICIAL_SOURCES = [
  {
    id: 'uspto_nonprovisional_utility_guide',
    title: 'USPTO Nonprovisional Utility Patent Application Filing Guide',
    url: 'https://www.uspto.gov/patents/basics/apply/utility-patent',
    use: 'Required parts, application order, DOCX and drawing requirements.',
  },
  {
    id: 'patent_center',
    title: 'USPTO Patent Center',
    url: 'https://patentcenter.uspto.gov',
    use: 'Electronic filing, application data, receipts, upload validation.',
  },
  {
    id: 'uspto_docx',
    title: 'USPTO DOCX Filing Guidance',
    url: 'https://www.uspto.gov/patents/docx',
    use: 'DOCX specification, claims, abstract, and drawing upload guidance.',
  },
  {
    id: 'uspto_fee_schedule',
    title: 'USPTO Fee Schedule',
    url: 'https://www.uspto.gov/learning-and-resources/fees-and-payment/uspto-fee-schedule',
    use: 'Current filing, search, examination, excess-claim, and surcharge fees.',
  },
  {
    id: 'uspto_forms',
    title: 'USPTO Patent Forms',
    url: 'https://www.uspto.gov/patents/apply/forms',
    use: 'ADS, oath/declaration, transmittal, and micro-entity forms.',
  },
  {
    id: 'patent_public_search',
    title: 'USPTO Patent Public Search',
    url: 'https://ppubs.uspto.gov/pubwebapp/',
    use: 'Primary patent and published-application prior-art search.',
  },
  {
    id: 'uspto_open_data_search_api',
    title: 'USPTO Open Data Search API',
    url: 'https://data.uspto.gov/apis/patent-file-wrapper/search',
    use: 'Programmatic file-wrapper and application-data discovery where applicable.',
  },
  {
    id: 'inventors_assistance_center',
    title: 'USPTO Inventors Assistance Center',
    url: 'https://www.uspto.gov/learning-and-resources/support-centers/inventors-assistance-center-iac',
    use: 'Self-filer support and official procedural help.',
  },
];

const PRIOR_ART_QUERIES = [
  'hyperbolic access control',
  'hyperbolic anomaly detection cybersecurity',
  'Poincare embedding security authorization',
  'AI prompt injection firewall',
  'LLM tool use governance runtime',
  'agentic workflow authorization gate',
  'semantic authorization cryptographic key derivation',
  'Unicode canonicalization tamper detection source code',
  'bijective tokenizer tamper detection',
  'runtime quarantine containment artificial intelligence agent',
  'post quantum authorization gate semantic context',
  'harmonic cost function security distance metric',
];

const SUPPORT_TARGETS = [
  {
    family: 'topological_linearization_cfi',
    terms: ['topological', 'linearization', 'phase', 'Hamiltonian', 'control flow', 'integrity'],
    paths: [
      'packages/kernel/src/topologicalLinearization.ts',
      'packages/kernel/src/hamiltonianCFI.ts',
      'python/scbe/loomflow.py',
      'python/scbe/material_flow.py',
      'tests/harmonic/topologicalLinearization.test.ts',
      'tests/harmonic/hamiltonianCFI.test.ts',
      'tests/test_loomflow.py',
      'tests/test_material_flow.py',
      'scripts/benchmark/loomflow_topological_cfi_proof.py',
      'docs/SCBE_SYSTEM_OVERVIEW.md',
    ],
  },
  {
    family: 'hyperbolic_governance_gate',
    terms: ['hyperbolic', 'Poincare', 'Poincare', 'distance', 'governance', 'decision'],
    paths: [
      'docs/PATENT_DETAILED_DESCRIPTION.md',
      'src/symphonic_cipher/scbe_aethermoore/organic_hyperbolic.py',
      'packages/kernel/src/hyperbolic.ts',
      'src/governance/runtime_gate.py',
    ],
  },
  {
    family: 'harmonic_cost_scaling',
    terms: ['harmonic', 'wall', 'cost', 'R^', 'distance'],
    paths: [
      'docs/PATENT_DETAILED_DESCRIPTION.md',
      'src/symphonic_cipher/scbe_aethermoore/layer_13.py',
      'src/symphonic_cipher/scbe_aethermoore/layers_9_12.py',
      'src/agent/types.ts',
    ],
  },
  {
    family: 'semantic_tongue_weighting',
    terms: ['Sacred', 'Tongue', 'semantic', 'weight', 'phi'],
    paths: [
      'docs/PATENT_DETAILED_DESCRIPTION.md',
      'src/tokenizer/ss1.ts',
      'packages/kernel/src/languesMetric.ts',
      'src/agent/types.ts',
    ],
  },
  {
    family: 'bijective_tamper_canonicality',
    terms: ['bijective', 'tamper', 'canonical', 'normalization', 'identifier'],
    paths: [
      'src/governance/bijective_tamper.py',
      'src/governance/identifier_canonicality.py',
      'src/governance/runtime_gate.py',
      'src/tokenizer/ss1.ts',
    ],
  },
  {
    family: 'quarantine_containment',
    terms: ['quarantine', 'containment', 'lock', 'timeout', 'restrict'],
    paths: [
      'src/agentic/quarantine_lock.py',
      'tests/agentic/test_quarantine_lock.py',
      'src/governance/runtime_gate.py',
    ],
  },
];

function usage() {
  process.stdout.write(`scbe-patent

Self-filing patent workbench for SCBE. This is not legal advice and does not file
with the USPTO. It prepares evidence, checklists, source registries, and logs.

Usage:
  scbe-patent init [--workdir <path>] [--json]
  scbe-patent sources [--workdir <path>] [--json]
  scbe-patent prior-art-plan [--workdir <path>] [--json]
  scbe-patent support-scan [--workdir <path>] [--json]
  scbe-patent benchmark [--workdir <path>] [--json]
  scbe-patent readiness [--workdir <path>] [--json]
  scbe-patent status [--workdir <path>] [--json]

Default workdir:
  docs/legal/patent-workbench
`);
}

function parse(argv) {
  const args = { command: '', workdir: DEFAULT_WORKDIR, json: false, help: false };
  args.command = argv[2] || '';
  for (let i = 3; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === '--workdir') {
      args.workdir = path.resolve(argv[++i] || '');
    } else if (token === '--json') {
      args.json = true;
    } else if (token === '--help' || token === '-h') {
      args.help = true;
    }
  }
  return args;
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function writeJson(filePath, value) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function writeText(filePath, text) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, text.endsWith('\n') ? text : `${text}\n`, 'utf8');
}

function sha256(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

function readIfExists(filePath) {
  if (!fs.existsSync(filePath)) return '';
  return fs.readFileSync(filePath, 'utf8');
}

function lineHits(relativePath, terms) {
  const absolute = path.join(ROOT, relativePath);
  const text = readIfExists(absolute);
  if (!text) return { path: relativePath, exists: false, hits: [] };
  const loweredTerms = terms.map((term) => term.toLowerCase());
  const hits = [];
  text.split(/\r?\n/).forEach((line, idx) => {
    const lower = line.toLowerCase();
    if (loweredTerms.some((term) => lower.includes(term))) {
      hits.push({
        line: idx + 1,
        text: line.trim().slice(0, 220),
      });
    }
  });
  return {
    path: relativePath,
    exists: true,
    sha256: sha256(text),
    hit_count: hits.length,
    hits: hits.slice(0, 20),
  };
}

function markdownSources() {
  return `# Official Patent Source Registry

Generated by \`scbe-patent sources\`.

${OFFICIAL_SOURCES.map(
  (source) => `## ${source.title}

- id: \`${source.id}\`
- url: ${source.url}
- use: ${source.use}
`
).join('\n')}
`;
}

function runSources(workdir) {
  const payload = {
    schema: 'scbe_patent_official_sources_v1',
    generated_at: new Date().toISOString(),
    sources: OFFICIAL_SOURCES,
  };
  writeJson(path.join(workdir, 'official_sources.json'), payload);
  writeText(path.join(workdir, 'official_sources.md'), markdownSources());
  return payload;
}

function runPriorArtPlan(workdir) {
  const rows = PRIOR_ART_QUERIES.map((query) => ({
    query,
    tools: ['USPTO Patent Public Search', 'Google Patents', 'Lens.org', 'Semantic Scholar/arXiv'],
    status: 'not_started',
    relevant_results: [],
    notes: '',
  }));
  const payload = {
    schema: 'scbe_patent_prior_art_plan_v1',
    generated_at: new Date().toISOString(),
    rows,
  };
  writeJson(path.join(workdir, 'prior_art_search_plan.json'), payload);
  writeText(
    path.join(workdir, 'prior_art_search_log.md'),
    `# Prior Art Search Log

Generated by \`scbe-patent prior-art-plan\`.

| Query | USPTO | Google Patents | Lens | Scholar/arXiv | Notes |
|---|---|---|---|---|---|
${rows.map((row) => `| ${row.query} |  |  |  |  |  |`).join('\n')}
`
  );
  return payload;
}

function runSupportScan(workdir) {
  const families = SUPPORT_TARGETS.map((target) => ({
    family: target.family,
    terms: target.terms,
    evidence: target.paths.map((p) => lineHits(p, target.terms)),
  }));
  const payload = {
    schema: 'scbe_patent_claim_support_scan_v1',
    generated_at: new Date().toISOString(),
    families,
  };
  writeJson(path.join(workdir, 'claim_support_scan.json'), payload);
  writeText(
    path.join(workdir, 'claim_support_scan.md'),
    `# Claim Support Scan

Generated by \`scbe-patent support-scan\`.

${families
  .map((family) => {
    const files = family.evidence
      .map((entry) => {
        const status = entry.exists ? `${entry.hit_count} hits` : 'missing';
        const sample = entry.hits?.[0]
          ? `\n  - sample: line ${entry.hits[0].line}: ${entry.hits[0].text}`
          : '';
        return `- \`${entry.path}\`: ${status}${sample}`;
      })
      .join('\n');
    return `## ${family.family}

Terms: ${family.terms.map((t) => `\`${t}\``).join(', ')}

${files}
`;
  })
  .join('\n')}
`
  );
  return payload;
}

function runReadiness(workdir) {
  const items = [
    ['provisional_exported', 'Filed provisional packet and receipt exported from Patent Center.'],
    ['priority_claim_checked', 'ADS will properly claim benefit of provisional application.'],
    ['micro_entity_checked', 'Micro entity eligibility checked and correct form selected.'],
    ['claim_count_checked', 'Independent and total claim counts checked for fee impact.'],
    ['spec_claim_support_checked', 'Every claim element mapped to specification support.'],
    ['drawings_complete', 'Drawings cover each claimed feature requiring a figure.'],
    ['prior_art_logged', 'Prior-art search log completed and reviewed.'],
    ['docx_validated', 'DOCX accepted by Patent Center validation.'],
    ['oath_declaration_ready', 'Inventor oath/declaration ready.'],
    ['fees_rechecked', 'USPTO fees checked on filing day.'],
  ];
  const payload = {
    schema: 'scbe_patent_readiness_checklist_v1',
    generated_at: new Date().toISOString(),
    checklist: items.map(([id, text]) => ({ id, text, status: 'open', evidence: '' })),
  };
  writeJson(path.join(workdir, 'filing_readiness_checklist.json'), payload);
  writeText(
    path.join(workdir, 'filing_readiness_checklist.md'),
    `# Filing Readiness Checklist

Generated by \`scbe-patent readiness\`.

${payload.checklist.map((item) => `- [ ] **${item.id}** - ${item.text}`).join('\n')}
`
  );
  return payload;
}

function runBenchmark(workdir) {
  const script = path.join(ROOT, 'scripts', 'legal', 'resonant_thought_lattice_benchmark.py');
  const outputDir = path.join(workdir, 'benchmarks');
  const python = process.env.PYTHON || 'python';
  execFileSync(python, [script, '--output-dir', outputDir], {
    cwd: ROOT,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const reportPath = path.join(outputDir, 'resonant_thought_lattice_benchmark.json');
  const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'));
  const manifestPath = path.join(workdir, 'manifest.json');
  if (fs.existsSync(manifestPath)) {
    const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
    for (const file of [
      'benchmarks/resonant_thought_lattice_benchmark.json',
      'benchmarks/resonant_thought_lattice_benchmark.md',
    ]) {
      if (!manifest.files.includes(file)) manifest.files.push(file);
    }
    manifest.counts = manifest.counts || {};
    manifest.counts.benchmark_results = 1;
    writeJson(manifestPath, manifest);
  }
  return {
    schema: 'scbe_patent_benchmark_command_v1',
    generated_at: new Date().toISOString(),
    workdir,
    application_number: report.application_number,
    docket: report.docket,
    title: report.title,
    files: [
      'benchmarks/resonant_thought_lattice_benchmark.json',
      'benchmarks/resonant_thought_lattice_benchmark.md',
    ],
    counts: {
      benchmark_results: 1,
      cases: report.case_count,
      improved_cases: report.metrics.improved_cases,
      regressed_cases: report.metrics.regressed_cases,
    },
    metrics: report.metrics,
  };
}

function runInit(workdir) {
  ensureDir(workdir);
  const sources = runSources(workdir);
  const priorArt = runPriorArtPlan(workdir);
  const support = runSupportScan(workdir);
  const readiness = runReadiness(workdir);
  const manifest = {
    schema: 'scbe_patent_workbench_manifest_v1',
    generated_at: new Date().toISOString(),
    workdir,
    files: [
      'official_sources.json',
      'official_sources.md',
      'prior_art_search_plan.json',
      'prior_art_search_log.md',
      'claim_support_scan.json',
      'claim_support_scan.md',
      'filing_readiness_checklist.json',
      'filing_readiness_checklist.md',
    ],
    counts: {
      official_sources: sources.sources.length,
      prior_art_queries: priorArt.rows.length,
      support_families: support.families.length,
      readiness_items: readiness.checklist.length,
    },
  };
  writeJson(path.join(workdir, 'manifest.json'), manifest);
  return manifest;
}

function runStatus(workdir) {
  const files = [
    'manifest.json',
    'official_sources.json',
    'prior_art_search_plan.json',
    'prior_art_search_log.md',
    'claim_support_scan.json',
    'filing_readiness_checklist.json',
  ];
  const payload = {
    schema: 'scbe_patent_workbench_status_v1',
    generated_at: new Date().toISOString(),
    workdir,
    files: files.map((file) => {
      const absolute = path.join(workdir, file);
      return {
        file,
        exists: fs.existsSync(absolute),
        bytes: fs.existsSync(absolute) ? fs.statSync(absolute).size : 0,
      };
    }),
  };
  return payload;
}

function print(result, json) {
  if (json) {
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
    return;
  }
  process.stdout.write(`${result.schema}\n`);
  if (result.workdir) process.stdout.write(`workdir: ${result.workdir}\n`);
  if (result.counts) {
    for (const [key, value] of Object.entries(result.counts)) {
      process.stdout.write(`${key}: ${value}\n`);
    }
  }
  if (result.files) {
    for (const file of result.files) {
      if (typeof file === 'string') process.stdout.write(`wrote: ${file}\n`);
      else
        process.stdout.write(
          `${file.exists ? '[ok]' : '[missing]'} ${file.file} (${file.bytes} bytes)\n`
        );
    }
  }
}

function main() {
  const args = parse(process.argv);
  if (args.help || !args.command) {
    usage();
    process.exitCode = args.command ? 0 : 1;
    return;
  }

  let result;
  switch (args.command) {
    case 'init':
      result = runInit(args.workdir);
      break;
    case 'sources':
      result = runSources(args.workdir);
      break;
    case 'prior-art-plan':
      result = runPriorArtPlan(args.workdir);
      break;
    case 'support-scan':
      result = runSupportScan(args.workdir);
      break;
    case 'benchmark':
      result = runBenchmark(args.workdir);
      break;
    case 'readiness':
      result = runReadiness(args.workdir);
      break;
    case 'status':
      result = runStatus(args.workdir);
      break;
    default:
      usage();
      process.exitCode = 1;
      return;
  }
  print(result, args.json);
}

main();
