#!/usr/bin/env node

const { spawnSync } = require('node:child_process');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const { performance } = require('node:perf_hooks');

const repoRoot = path.resolve(__dirname, '..', '..', '..');
const pkgRoot = path.resolve(__dirname, '..');
const outDir = path.join(pkgRoot, 'docs', 'benchmarks');
const jsonOut = path.join(outDir, 'agentic_os_cli_benchmark.json');
const mdOut = path.join(outDir, 'agentic_os_cli_benchmark.md');
const python = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');

function runCommand(label, command, args, opts = {}) {
  const started = performance.now();
  const proc = spawnSync(command, args, {
    cwd: opts.cwd || repoRoot,
    env: { ...process.env, ...(opts.env || {}) },
    encoding: 'utf8',
    timeout: opts.timeout || 60000,
    maxBuffer: 1024 * 1024 * 8,
  });
  const elapsedMs = performance.now() - started;
  let parsed = null;
  try {
    parsed = proc.stdout ? JSON.parse(proc.stdout) : null;
  } catch {
    parsed = null;
  }
  return {
    label,
    command,
    args,
    elapsed_ms: Number(elapsedMs.toFixed(3)),
    ok: proc.status === 0,
    exit_code: proc.status,
    stdout_chars: proc.stdout.length,
    stderr_tail: proc.stderr.slice(-1000),
    parsed,
  };
}

function benchmarkCase(label, fn) {
  const started = performance.now();
  try {
    const result = fn();
    return {
      label,
      ok: Boolean(result?.ok ?? true),
      elapsed_ms: Number((performance.now() - started).toFixed(3)),
      result,
      error: null,
    };
  } catch (err) {
    return {
      label,
      ok: false,
      elapsed_ms: Number((performance.now() - started).toFixed(3)),
      result: null,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

function median(values) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)];
}

function percentile(values, pct) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.ceil((pct / 100) * sorted.length) - 1);
  return sorted[idx];
}

function requireBuiltBus() {
  const distPath = path.join(pkgRoot, 'dist', 'index.js');
  if (!fs.existsSync(distPath)) {
    throw new Error('packages/agent-bus/dist/index.js is missing; run npm run build first');
  }
  return require(distPath);
}

function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const bus = requireBuiltBus();

  const cases = [];

  cases.push(
    benchmarkCase('tool_registry_audit_full_surface', () => {
      bus.clearTools();
      process.env.SCBE_BUS_TOOLS = path.join(pkgRoot, 'tools.json');
      bus.autoDiscoverTools();
      const audit = bus.auditToolRegistry(bus.listTools());
      return {
        ok:
          audit.ok &&
          audit.tool_count >= 37 &&
          audit.surface_counts.unknown === 0 &&
          audit.surface_counts['atomic-tokenizer'] >= 2 &&
          audit.surface_counts['agent-harness'] > 0,
        tool_count: audit.tool_count,
        surface_counts: audit.surface_counts,
        missing_required_env: audit.missing_required_env,
      };
    })
  );

  const semanticInputs = [
    'compile add operation across language lanes and verify binary hex transport',
    'block denied command but preserve route evidence for governance',
    'transform water flow into a computed pipeline example',
    'convert prompt to tokens then recompose the closest semantic atom',
  ];
  for (const input of semanticInputs) {
    cases.push(
      benchmarkCase(`semantic_hex_roundtrip:${input.slice(0, 32)}`, () => {
        const decomp = bus.decompose(input);
        const recomposed = bus.recompose(decomp.combinedHex);
        const binaryGroups = decomp.combinedBinary.split(' ');
        return {
          ok:
            /^[0-9a-f]{12}$/.test(decomp.combinedHex) &&
            binaryGroups.length === 6 &&
            recomposed.closest !== null,
          input_hash: decomp.inputHash,
          combined_hex: decomp.combinedHex,
          combined_binary: decomp.combinedBinary,
          dominant: decomp.dominant,
          recomposed_closest: recomposed.closest,
        };
      })
    );
  }

  const compassTasks = [
    {
      label: 'compass_plan_forge_cross_domain',
      task: 'cross-language compiler with binary hex interpolation and tokenizer self-check',
      expectMode: 'compiler',
      expectFormation: 'forge',
      expectTool: 'geoseal-cross-build',
    },
    {
      label: 'compass_plan_broadcast_youtube_pipeline',
      task: 'write a YouTube script, dry-run the video, review upload metadata',
      expectMode: 'youtube',
      expectFormation: 'broadcast',
      expectTool: 'youtube-video-review',
    },
    {
      label: 'compass_plan_council_model_lanes_free_limits',
      task: 'check ollama and huggingface model API routes',
      expectMode: 'model',
      expectFormation: 'council',
      expectTool: 'ai-router-health',
    },
  ];
  for (const spec of compassTasks) {
    cases.push(
      benchmarkCase(spec.label, () => {
        const plan = bus.planScbeCompassRoute(spec.task);
        const tiers = plan.model_lanes.map((lane) => lane.costTier);
        return {
          ok:
            plan.mode === spec.expectMode &&
            plan.formation === spec.expectFormation &&
            typeof plan.command_path === 'string' &&
            plan.octree_context?.octree_retrieval?.surfaces?.includes(
              'octree spatial / structural retrieval'
            ) &&
            plan.primary_tools.includes(spec.expectTool) &&
            plan.adapter_slots.length >= 4 &&
            tiers.includes('local-free-after-install') &&
            tiers.includes('remote-free-tier-limited') &&
            plan.governance.budget_cents === 0,
          mode: plan.mode,
          formation: plan.formation,
          command_path: plan.command_path,
          primary_tools: plan.primary_tools,
          octree_surfaces: plan.octree_context.octree_retrieval.surfaces,
          adapter_slots: plan.adapter_slots,
          model_cost_tiers: tiers,
          blocked_actions: plan.governance.blocked_actions,
        };
      })
    );
  }

  cases.push(
    benchmarkCase('compass_board_rules_source_anchored', () => {
      const rules = bus.scbeCompassBoardRules('compiler');
      const sourcePaths = rules.flatMap((rule) => rule.source_paths || []);
      const schemas = rules.flatMap((rule) => rule.schemas || []);
      return {
        ok:
          rules.some((rule) => rule.mechanic === 'pazaak-hand') &&
          rules.some((rule) => rule.mechanic === 'go-board-territory') &&
          rules.some((rule) => rule.mechanic === 'chessboard-stack') &&
          sourcePaths.includes('scripts/system/agentic_pazaak_board.py') &&
          sourcePaths.includes('src/coding_board/pipeline.py') &&
          sourcePaths.includes('scripts/system/chessboard_dev_stack.py') &&
          schemas.includes('scbe_agentic_pazaak_board_report_v1') &&
          schemas.includes('scbe-coding-trial-v1'),
        mechanic_count: rules.length,
        mechanics: rules.map((rule) => rule.mechanic),
        source_paths: sourcePaths,
        schemas,
      };
    })
  );

  const pazaakRun = runCommand(
    'agentic_pazaak_board_default_moves',
    python,
    ['scripts/system/agentic_pazaak_board.py', '--limit', '3'],
    { timeout: 30000 }
  );
  const pazaakOk =
    pazaakRun.parsed?.schema === 'scbe_agentic_pazaak_board_report_v1' &&
    Array.isArray(pazaakRun.parsed?.moves) &&
    pazaakRun.parsed.moves.length === 3 &&
    pazaakRun.parsed.moves[0]?.card_id === 'claim_territory' &&
    typeof pazaakRun.parsed?.bitboards?.conflict === 'number';
  cases.push({
    label: pazaakRun.label,
    ok: pazaakOk,
    elapsed_ms: pazaakRun.elapsed_ms,
    result: {
      exit_code: pazaakRun.exit_code,
      schema: pazaakRun.parsed?.schema,
      top_move: pazaakRun.parsed?.moves?.[0],
      bitboards: pazaakRun.parsed?.bitboards,
    },
    error: pazaakOk ? null : pazaakRun.stderr_tail || 'unexpected pazaak board output',
  });

  const hardeningCandidates = [];

  const binaryTokenizerRun = runCommand(
    'geoseal_binary_tokenizer_roundtrip',
    python,
    [
      '-m',
      'src.geoseal_cli',
      'binary-to-tokenizer',
      '--tongue',
      'KO',
      '--bits',
      '01000001',
      '--json',
    ],
    { timeout: 30000 }
  );
  const binaryTokenizerOk =
    binaryTokenizerRun.parsed?.version === 'geoseal-binary-tokenizer-map-v1' &&
    binaryTokenizerRun.parsed?.roundtrip?.bytes_ok === true &&
    binaryTokenizerRun.parsed?.rows?.[0]?.byte_hex === '0x41';
  hardeningCandidates.push(
    hardeningCandidate({
      label: binaryTokenizerRun.label,
      surface: 'internal-tokenizer',
      source_paths: ['src/geoseal_cli.py', 'src/tokenizer/ss1.ts'],
      run: binaryTokenizerRun,
      ok: binaryTokenizerOk,
      maturity: 'hold-internal',
      next_round:
        'Keep out of published CLI; promote only after threat model, input bounds, and redaction policy are documented.',
      result: {
        version: binaryTokenizerRun.parsed?.version,
        token: binaryTokenizerRun.parsed?.rows?.[0]?.token,
        roundtrip: binaryTokenizerRun.parsed?.roundtrip,
      },
    })
  );

  const lightningRun = runCommand(
    'lightning_indexer_octree_context',
    python,
    [
      '-m',
      'src.geoseal_cli',
      'lightning-indexer',
      '--goal',
      'cross language tokenizer compiler evidence',
      '--inline-candidates',
      '[{"id":"compiler","text":"cross language tokenizer compiler evidence","kind":"tool","lane":"compiler","priority":4},{"id":"youtube","text":"youtube upload metadata review","kind":"tool","lane":"broadcast","priority":3},{"id":"governance","text":"geoseal policy verification and receipts","kind":"test","lane":"governance","priority":5}]',
      '--top-k',
      '2',
      '--json',
    ],
    { timeout: 30000 }
  );
  const lightningOk =
    lightningRun.parsed?.schema_version === 'scbe_lightning_indexer_v1' &&
    Array.isArray(lightningRun.parsed?.selected) &&
    lightningRun.parsed.selected[0]?.candidate_id === 'compiler' &&
    lightningRun.parsed?.octree_retrieval?.schema_version === 'scbe_sparse_octree_retrieval_v1';
  hardeningCandidates.push(
    hardeningCandidate({
      label: lightningRun.label,
      surface: 'internal-context-retrieval',
      source_paths: [
        'src/coding_spine/lightning_indexer.py',
        'tests/coding_spine/test_lightning_indexer.py',
      ],
      run: lightningRun,
      ok: lightningOk,
      maturity: 'hold-internal',
      next_round:
        'Keep as internal sparse-context benchmark until candidate redaction and prompt-injection isolation are added.',
      result: {
        schema_version: lightningRun.parsed?.schema_version,
        selected: lightningRun.parsed?.selected?.map((row) => row.candidate_id),
        octree_schema: lightningRun.parsed?.octree_retrieval?.schema_version,
      },
    })
  );

  const opBinaryRun = runCommand(
    'op_binary_inverse_complexity_demo',
    python,
    ['-m', 'src.symphonic.multipath.op_binary'],
    { timeout: 30000 }
  );
  const opBinaryOk =
    opBinaryRun.ok &&
    opBinaryRun.stdout_chars > 100 &&
    opBinaryRun.parsed === null &&
    opBinaryRun.stderr_tail === '';
  hardeningCandidates.push(
    hardeningCandidate({
      label: opBinaryRun.label,
      surface: 'internal-adaptive-tokenizer',
      source_paths: ['src/symphonic/multipath/op_binary.py'],
      run: opBinaryRun,
      ok: opBinaryOk,
      maturity: 'hold-internal',
      next_round:
        'Needs structured JSON output and deterministic bounds before any public tool exposure.',
      result: {
        stdout_chars: opBinaryRun.stdout_chars,
        evidence: 'op sequence / KO cost / DR cost table emitted',
      },
    })
  );

  const attentionRun = runCommand(
    'attention_fft_synthetic_control',
    python,
    [
      '-m',
      'scripts.probe_attention_fft',
      '--control',
      'banded',
      '--json',
      '--output-root',
      path.join(repoRoot, 'artifacts', 'tmp-agentic-os-attention-fft'),
    ],
    { timeout: 30000 }
  );
  const attentionOk =
    attentionRun.parsed?.record_type === 'attention_fft_probe_v1' &&
    attentionRun.parsed?.control_kind === 'banded' &&
    attentionRun.parsed?.analysis?.closer_to_banded_than_random === true;
  hardeningCandidates.push(
    hardeningCandidate({
      label: attentionRun.label,
      surface: 'internal-attention-telemetry',
      source_paths: ['scripts/probe_attention_fft.py', 'src/minimal/mirror_problem_fft.py'],
      run: attentionRun,
      ok: attentionOk,
      maturity: 'hold-internal',
      next_round:
        'Synthetic control is safe; model-backed probing stays internal until model/download and secret gates are explicit.',
      result: {
        record_type: attentionRun.parsed?.record_type,
        control_kind: attentionRun.parsed?.control_kind,
        closer_to_banded_than_random: attentionRun.parsed?.analysis?.closer_to_banded_than_random,
      },
    })
  );
  cleanupTmpAttention();

  const storageCompactionRun = runCommand(
    'storage_compaction_lab_candidate',
    python,
    [
      '-m',
      'scripts.system.storage_compaction_lab',
      '--system',
      'hyperbolic-octree',
      '--values',
      '2,3',
      '--output-json',
      path.join(repoRoot, 'artifacts', 'tmp-agentic-os-storage-compaction.json'),
    ],
    { timeout: 30000 }
  );
  const storageCompactionOk =
    storageCompactionRun.parsed?.experiment === 'storage_compaction_lab' &&
    storageCompactionRun.parsed?.best_card?.verdict === 'best-current-tradeoff';
  hardeningCandidates.push(
    hardeningCandidate({
      label: storageCompactionRun.label,
      surface: 'internal-storage-geometry',
      source_paths: ['scripts/system/storage_compaction_lab.py', 'src/crypto/octree.py'],
      run: storageCompactionRun,
      ok: storageCompactionOk,
      maturity: storageCompactionOk ? 'candidate-ready-internal' : 'flag-for-hardening',
      next_round:
        'Add generated-artifact cleanup, fixed output schema, and wider fixture set before CLI exposure.',
      result: {
        experiment: storageCompactionRun.parsed?.experiment,
        best_value: storageCompactionRun.parsed?.best_card?.value,
        best_verdict: storageCompactionRun.parsed?.best_card?.verdict,
      },
    })
  );
  cleanupTmpFile('tmp-agentic-os-storage-compaction.json');

  const storageMeshRun = runCommand(
    'storage_interaction_mesh_candidate',
    python,
    [
      '-m',
      'scripts.system.storage_interaction_mesh_lab',
      '--max-notes',
      '4',
      '--output-json',
      path.join(repoRoot, 'artifacts', 'tmp-agentic-os-storage-mesh.json'),
    ],
    { timeout: 30000 }
  );
  const storageMeshOk =
    storageMeshRun.parsed?.experiment === 'storage_interaction_mesh' &&
    storageMeshRun.parsed?.mesh?.stats?.record_count === 4;
  hardeningCandidates.push(
    hardeningCandidate({
      label: storageMeshRun.label,
      surface: 'internal-storage-mesh',
      source_paths: [
        'scripts/system/storage_interaction_mesh_lab.py',
        'src/knowledge/storage_interaction_mesh.py',
      ],
      run: storageMeshRun,
      ok: storageMeshOk,
      maturity: storageMeshOk ? 'candidate-ready-internal' : 'flag-for-hardening',
      next_round:
        'Keep internal until note-ingest privacy labels and artifact retention rules are wired.',
      result: {
        experiment: storageMeshRun.parsed?.experiment,
        note_count: storageMeshRun.parsed?.note_count,
        record_count: storageMeshRun.parsed?.mesh?.stats?.record_count,
      },
    })
  );
  cleanupTmpFile('tmp-agentic-os-storage-mesh.json');

  const coreChecksRun = runCommand(
    'core_python_checks_dry_run_candidate',
    python,
    ['scripts/system/run_core_python_checks.py', '--dry-run', '--json'],
    { timeout: 30000 }
  );
  const coreChecksOk =
    Array.isArray(coreChecksRun.parsed?.command) &&
    coreChecksRun.parsed.command.includes('tests/test_runtime_gate.py');
  hardeningCandidates.push(
    hardeningCandidate({
      label: coreChecksRun.label,
      surface: 'internal-test-lane',
      source_paths: ['scripts/system/run_core_python_checks.py'],
      run: coreChecksRun,
      ok: coreChecksOk,
      maturity: coreChecksOk ? 'candidate-ready-internal' : 'flag-for-hardening',
      next_round:
        'Can be used as internal merge-readiness evidence; public CLI should expose only summarized pass/fail receipts.',
      result: {
        command_count: coreChecksRun.parsed?.command?.length,
        optional_ignores: coreChecksRun.parsed?.optional_ignores?.length,
      },
    })
  );

  const systemCardRun = runCommand(
    'system_card_deck_candidate',
    python,
    ['scripts/system/system_card_deck.py', '--json'],
    { timeout: 30000 }
  );
  hardeningCandidates.push(
    hardeningCandidate({
      label: systemCardRun.label,
      surface: 'internal-system-map',
      source_paths: ['scripts/system/system_card_deck.py'],
      run: systemCardRun,
      ok: systemCardRun.ok && systemCardRun.parsed !== null,
      maturity: 'flag-for-hardening',
      next_round:
        'Fails without artifacts/repo-ordering/latest.json; add a dry-run/sample fallback before promotion.',
      result: {
        exit_code: systemCardRun.exit_code,
      },
    })
  );

  hardeningCandidates.push(
    staticTextCandidate({
      label: 'spiralverse_space_commerce_lineage',
      surface: 'internal-origin-lineage',
      source_paths: [
        'external_repos/spiralverse-protocol/docs/SPACE_DEBRIS_FLEET.md',
        'external_repos/spiralverse-protocol/README.md',
      ],
      checks: [
        {
          path: 'external_repos/spiralverse-protocol/docs/SPACE_DEBRIS_FLEET.md',
          includes: [
            'Autonomous Orbital Debris Removal',
            'satellite swarms',
            'Roundtable Multi-Signature Policies',
            'Docking maneuver',
          ],
        },
        {
          path: 'external_repos/spiralverse-protocol/README.md',
          includes: ['Space Debris Cleanup', '6D Vector Navigation', 'autonomous fleets'],
        },
      ],
      maturity: 'candidate-ready-internal',
      next_round:
        'Keep as lineage/evidence. Promote only as a read-only provenance report, not an execution tool.',
      result: {
        relation: 'space commerce origin for SCBE fleet/governance concepts',
        published_cli: false,
      },
    })
  );

  hardeningCandidates.push(
    staticTextCandidate({
      label: 'spiralverse_polly_tier_lineage',
      surface: 'internal-fleet-lineage',
      source_paths: [
        'external_repos/spiralverse-protocol/src/fleet/polly-pad.ts',
        'external_repos/spiralverse-protocol/src/fleet/types.ts',
        'external_repos/spiralverse-protocol/src/fleet/governance.ts',
      ],
      checks: [
        {
          path: 'external_repos/spiralverse-protocol/src/fleet/polly-pad.ts',
          includes: ['Polly Pad', 'Kindergarten', 'Doctorate', 'TIER_THRESHOLDS'],
        },
        {
          path: 'external_repos/spiralverse-protocol/src/fleet/types.ts',
          includes: ['GovernanceTier', 'trustVector', 'requiredTongues', 'Critical/destructive'],
        },
        {
          path: 'external_repos/spiralverse-protocol/src/fleet/governance.ts',
          includes: ['Roundtable', 'getRequiredTier', 'requiresRoundtable'],
        },
      ],
      maturity: 'candidate-ready-internal',
      next_round:
        'Use as provenance for SCBE fleet tiers; do not expose raw pad/workspace controls in the public CLI.',
      result: {
        relation: 'Polly Pads and grade-level governance predate SCBE Sacred Tongue tiers',
        published_cli: false,
      },
    })
  );

  hardeningCandidates.push(
    staticTextCandidate({
      label: 'spiralverse_patent_sync_candidate',
      surface: 'internal-ip-lineage',
      source_paths: [
        'external_repos/spiralverse-protocol/PATENT_PROCESS_TRACKER.md',
        'external_repos/spiralverse-protocol/PATENT_PREREQUISITES.md',
        'external_repos/spiralverse-protocol/patent/MASTER_PATENT_DOCUMENT.md',
        'external_repos/spiralverse-protocol/patent/RESEARCH_PATENT_ANALYSIS.md',
      ],
      checks: [
        {
          path: 'external_repos/spiralverse-protocol/patent/MASTER_PATENT_DOCUMENT.md',
          includes: ['6D Vector Navigation System', 'Roundtable Governance', 'Total Claims'],
        },
        {
          path: 'external_repos/spiralverse-protocol/patent/RESEARCH_PATENT_ANALYSIS.md',
          includes: ['patent landscape', 'spacecraft autonomy', 'multi-signature governance'],
        },
        {
          path: 'external_repos/spiralverse-protocol/PATENT_PROCESS_TRACKER.md',
          includes: ['patent'],
        },
      ],
      maturity: 'flag-for-sync-review',
      next_round:
        'Reconcile with SCBE patent workbench before copying any claim language; keep separate evidence layer.',
      result: {
        relation: 'older Spiralverse IP packet should stay synced but not merged blindly',
        published_cli: false,
      },
    })
  );

  const crossBuilds = [
    {
      label: 'cross_build_ko_to_ru_add',
      args: [
        'src/geoseal_cli.py',
        'cross-build',
        '--src-code',
        '(x + y)',
        '--src-tongue',
        'KO',
        '--dst-tongue',
        'RU',
      ],
      expect: (body) => body?.dst_code === 'x.wrapping_add(y)' && body?.ir?.op_name === 'add',
    },
    {
      label: 'cross_build_av_to_dr_xor',
      args: [
        'src/geoseal_cli.py',
        'cross-build',
        '--src-code',
        '(p ^ q)',
        '--src-tongue',
        'AV',
        '--dst-tongue',
        'DR',
      ],
      expect: (body) =>
        body?.ir?.op_name === 'xor' &&
        String(body?.dst_code || '')
          .toLowerCase()
          .includes('xor'),
    },
    {
      label: 'cross_build_broadcast_add_all_tongues',
      args: [
        'src/geoseal_cli.py',
        'cross-build',
        '--src-code',
        '(x + y)',
        '--src-tongue',
        'KO',
        '--all-tongues',
      ],
      expect: (body) =>
        body?.mode === 'broadcast' && Object.keys(body?.translations || {}).length === 5,
    },
    {
      label: 'cross_build_list_ops_64',
      args: ['src/geoseal_cli.py', 'cross-build', '--list-ops'],
      expect: (body) => body?.participating_count === 64 && body?.excluded_count === 0,
    },
    {
      label: 'cross_build_quarantine_arbitrary_code',
      args: [
        'src/geoseal_cli.py',
        'cross-build',
        '--src-code',
        'import os',
        '--src-tongue',
        'KO',
        '--dst-tongue',
        'RU',
      ],
      expect: (body, run) => run.exit_code === 2 && body?.verdict === 'QUARANTINE',
      expectedNonZero: true,
    },
  ];

  for (const spec of crossBuilds) {
    const run = runCommand(spec.label, python, spec.args, { timeout: 90000 });
    const ok = Boolean(spec.expect(run.parsed, run));
    cases.push({
      label: spec.label,
      ok,
      elapsed_ms: run.elapsed_ms,
      result: {
        exit_code: run.exit_code,
        stdout_chars: run.stdout_chars,
        parsed_summary: summarizeParsed(run.parsed),
      },
      error: ok ? null : run.stderr_tail || 'expectation failed',
    });
  }

  const stateRun = runCommand(
    'pipeline_state_init_governed_lane',
    process.execPath,
    [
      path.join(pkgRoot, 'bin', 'scbe-agent-bus.cjs'),
      'pipeline',
      'state',
      '--session-id',
      'bench-agentic-os',
      '--state-root',
      path.join(repoRoot, '.aethermoor-bus', 'tmp-bench-governed-state'),
      '--init',
      '--json',
    ],
    { timeout: 30000 }
  );
  const stateOk =
    stateRun.parsed?.schema_version === 'scbe.agent_bus.governed_state_summary.v1' &&
    Array.isArray(stateRun.parsed?.reachable_set) &&
    stateRun.parsed.reachable_set.join(',') === 'observe,read,verify';
  cases.push({
    label: stateRun.label,
    ok: stateOk,
    elapsed_ms: stateRun.elapsed_ms,
    result: stateRun.parsed,
    error: stateOk ? null : stateRun.stderr_tail || 'unexpected governed state output',
  });
  cleanupTmpState();

  const passed = cases.filter((c) => c.ok).length;
  const elapsed = cases.map((c) => c.elapsed_ms);
  const hardeningPassed = hardeningCandidates.filter((c) => c.ok).length;
  const nextRoundFlags = hardeningCandidates
    .filter((c) => !c.ok || c.maturity === 'flag-for-hardening')
    .map((c) => ({
      label: c.label,
      surface: c.surface,
      next_round: c.next_round,
      error: c.error,
    }));
  const report = {
    schema_version: 'scbe.agentic_os_cli_benchmark.v1',
    generated_at: new Date().toISOString(),
    repo_root: repoRoot,
    benchmark_id: crypto
      .createHash('sha256')
      .update(cases.map((c) => `${c.label}:${c.ok}`).join('|'))
      .digest('hex')
      .slice(0, 16),
    summary: {
      case_count: cases.length,
      passed,
      failed: cases.length - passed,
      pass_rate: Number((passed / cases.length).toFixed(4)),
      median_ms: Number(median(elapsed).toFixed(3)),
      p95_ms: Number(percentile(elapsed, 95).toFixed(3)),
      hardening_candidate_count: hardeningCandidates.length,
      hardening_passed: hardeningPassed,
      hardening_failed: hardeningCandidates.length - hardeningPassed,
      next_round_flag_count: nextRoundFlags.length,
    },
    lanes: {
      agent_harness: 'tools audit + governed state CLI',
      cross_language_compiler: 'geoseal cross-build Tier 1 lexicon-bounded IR',
      binary_hexa_interpolation:
        'agent-bus semantic bridge 6D -> 48-bit binary -> 12-char hex -> recomposition',
      compass_front_door:
        'SCBE formation classifier + adapter slots + local/free-tier/paid model lane planner + writing/YouTube route examples',
      board_mechanics:
        'Pazaak bitboard planner + coding-board legality probe + octree/chessboard source anchors',
      internal_hardening_candidates:
        'Vault-surfaced higher-security probes are benchmarked here but are not published as public CLI tools',
      governance: 'durable trajectory start set observe/read/verify',
    },
    best_in_class_gaps: [
      {
        gap: 'atomic-tokenizer bus surface is now registered but still only smoke-tests byte bijection',
        impact:
          'patent-ready atomic tokenizer needs a stronger task corpus covering semantic atoms, code slots, and transport packets',
      },
      {
        gap: 'cross-build is Tier 1 lexicon-bounded, not arbitrary AST translation',
        impact:
          '64 ops close cleanly, but best-in-class cross-domain compiler needs Tier 2 parser-backed lift into same LatticeOp schema',
      },
      {
        gap: 'semantic hex recomposition is nearest-atom, not lossless semantic identity',
        impact:
          'good for routing/interpolation, but benchmark should not claim perfect natural-language bijection',
      },
      {
        gap: 'YouTube upload lane is registered but intentionally unlisted-first',
        impact:
          'public publish remains a human approval gate; benchmark validates route availability, not live upload success',
      },
    ],
    cases,
    hardening_candidates: hardeningCandidates,
    next_round_flags: nextRoundFlags,
  };

  fs.writeFileSync(jsonOut, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
  fs.writeFileSync(mdOut, renderMarkdown(report), 'utf8');
  formatReportFiles();
  process.stdout.write(
    `${JSON.stringify({ ok: report.summary.failed === 0, jsonOut, mdOut, summary: report.summary }, null, 2)}\n`
  );
  process.exitCode = report.summary.failed === 0 ? 0 : 1;
}

function formatReportFiles() {
  const prettierBin = path.join(pkgRoot, 'node_modules', 'prettier', 'bin', 'prettier.cjs');
  spawnSync(process.execPath, [prettierBin, '--write', jsonOut, mdOut], {
    cwd: pkgRoot,
    encoding: 'utf8',
    stdio: 'ignore',
    timeout: 30000,
  });
}

function summarizeParsed(body) {
  if (!body || typeof body !== 'object') return null;
  if (body.ir) {
    return {
      mode: body.mode || 'single',
      src_tongue: body.src_tongue,
      dst_tongue: body.dst_tongue,
      dst_code: body.dst_code,
      op_name: body.ir.op_name,
      op_id: body.ir.op_id,
    };
  }
  if (body.translations) {
    return {
      mode: body.mode,
      translation_count: Object.keys(body.translations).length,
      translations: body.translations,
    };
  }
  if (typeof body.participating_count === 'number') {
    return {
      participating_count: body.participating_count,
      excluded_count: body.excluded_count,
    };
  }
  if (body.verdict) {
    return {
      verdict: body.verdict,
      error_type: body.error_type,
    };
  }
  return body;
}

function hardeningCandidate({
  label,
  surface,
  source_paths,
  run,
  ok,
  maturity,
  next_round,
  result,
}) {
  return {
    label,
    surface,
    source_paths,
    ok: Boolean(ok),
    maturity,
    elapsed_ms: run.elapsed_ms,
    exit_code: run.exit_code,
    result,
    error: ok ? null : run.stderr_tail || run.error || 'candidate expectation failed',
    next_round,
    published_cli: false,
  };
}

function staticTextCandidate({
  label,
  surface,
  source_paths,
  checks,
  maturity,
  next_round,
  result,
}) {
  const started = performance.now();
  const missing = [];
  const matched = [];
  for (const check of checks) {
    const target = path.join(repoRoot, check.path);
    if (!target.startsWith(repoRoot) || !fs.existsSync(target)) {
      missing.push({ path: check.path, reason: 'missing-file' });
      continue;
    }
    const text = fs.readFileSync(target, 'utf8');
    for (const snippet of check.includes) {
      if (text.includes(snippet)) {
        matched.push({ path: check.path, snippet });
      } else {
        missing.push({ path: check.path, snippet });
      }
    }
  }
  const ok = missing.length === 0;
  return {
    label,
    surface,
    source_paths,
    ok,
    maturity: ok ? maturity : 'flag-for-hardening',
    elapsed_ms: Number((performance.now() - started).toFixed(3)),
    exit_code: ok ? 0 : 1,
    result: {
      ...result,
      matched_count: matched.length,
      missing_count: missing.length,
    },
    error: ok ? null : JSON.stringify(missing.slice(0, 5)),
    next_round,
    published_cli: false,
  };
}

function cleanupTmpState() {
  const target = path.join(repoRoot, '.aethermoor-bus', 'tmp-bench-governed-state');
  if (target.startsWith(repoRoot) && fs.existsSync(target)) {
    fs.rmSync(target, { recursive: true, force: true });
  }
}

function cleanupTmpAttention() {
  const target = path.join(repoRoot, 'artifacts', 'tmp-agentic-os-attention-fft');
  if (target.startsWith(repoRoot) && fs.existsSync(target)) {
    fs.rmSync(target, { recursive: true, force: true });
  }
}

function cleanupTmpFile(name) {
  const target = path.join(repoRoot, 'artifacts', name);
  if (target.startsWith(repoRoot) && fs.existsSync(target)) {
    fs.rmSync(target, { force: true });
  }
}

function renderMarkdown(report) {
  const lines = [
    '# Agentic OS CLI Benchmark',
    '',
    `Generated: ${report.generated_at}`,
    `Benchmark id: ${report.benchmark_id}`,
    '',
    '## Summary',
    '',
    `- Cases: ${report.summary.case_count}`,
    `- Passed: ${report.summary.passed}`,
    `- Failed: ${report.summary.failed}`,
    `- Pass rate: ${report.summary.pass_rate}`,
    `- Median ms: ${report.summary.median_ms}`,
    `- P95 ms: ${report.summary.p95_ms}`,
    `- Internal hardening candidates: ${report.summary.hardening_candidate_count}`,
    `- Hardening passed: ${report.summary.hardening_passed}`,
    `- Hardening failed: ${report.summary.hardening_failed}`,
    `- Next-round flags: ${report.summary.next_round_flag_count}`,
    '',
    '## Lanes',
    '',
    ...Object.entries(report.lanes).map(([k, v]) => `- ${k}: ${v}`),
    '',
    '## Cases',
    '',
    '| Case | OK | ms | Evidence |',
    '| --- | --- | ---: | --- |',
  ];
  for (const c of report.cases) {
    const evidence =
      c.result?.combined_hex ||
      c.result?.mode ||
      c.result?.parsed_summary?.op_name ||
      c.result?.parsed_summary?.mode ||
      c.result?.schema_version ||
      c.result?.tool_count ||
      c.error ||
      '';
    lines.push(
      `| ${c.label} | ${c.ok ? 'PASS' : 'FAIL'} | ${c.elapsed_ms} | ${String(evidence).replace(/\|/g, '/')} |`
    );
  }
  lines.push('', '## Internal Hardening Candidates', '');
  lines.push('| Candidate | Status | Surface | Maturity | Next Round |');
  lines.push('| --- | --- | --- | --- | --- |');
  for (const c of report.hardening_candidates || []) {
    lines.push(
      `| ${c.label} | ${c.ok ? 'PASS' : 'FLAG'} | ${c.surface} | ${c.maturity} | ${String(c.next_round).replace(/\|/g, '/')} |`
    );
  }
  lines.push('', '## Best-In-Class Gaps', '');
  for (const gap of report.best_in_class_gaps) {
    lines.push(`- ${gap.gap}: ${gap.impact}`);
  }
  lines.push('');
  return `${lines.join('\n')}\n`;
}

main();
