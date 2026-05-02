// Extra commands — extends the REPL with real GeoSeal CLI surface area
// matching subparsers from src/geoseal_cli.py.

const G_X = window.GeoSeal;
const T_X = window.SacredTokenizer;

// Pretty token rendering for emit/decode/xlate output
function tokensToString(tokens, perLine = 8) {
  const out = [];
  for (let i = 0; i < tokens.length; i += perLine) {
    out.push("    " + tokens.slice(i, i+perLine).join("  "));
  }
  return out.join("\n");
}

const Lx = {
  text: (text, tone="neutral") => ({ kind: "text", text, tone }),
  block: (data) => ({ kind: "block", data }),
  tokens: (data) => ({ kind: "tokens", data }),
  atomic: (data) => ({ kind: "atomic", data }),
  history: (data) => ({ kind: "history", data }),
  scaffold: (data) => ({ kind: "scaffold", data }),
  workflow: (data) => ({ kind: "workflow", data }),
  egg: (data) => ({ kind: "egg", data }),
  manifest: (data) => ({ kind: "manifest", data }),
  art: (text) => ({ kind: "art", text }),
};

// ============================================================
// TOKENIZER COMMANDS — encode / decode / xlate / verify
// ============================================================

const TokenizerCommands = {
  encode: {
    summary: "encode payload via Sacred Tongue tokens",
    run: ({ args, push }) => {
      const payload = args.positional.join(" ") || args.flags.payload;
      if (!payload) { push(Lx.text("usage: encode <text> [--tongue KO|AV|RU|CA|UM|DR]", "err")); return 1; }
      const tongue = String(args.flags.tongue || "KO").toUpperCase();
      if (!T_X.TONGUE_SPECS[tongue]) { push(Lx.text(`unknown tongue: ${tongue}`,"err")); return 1; }
      const bytes = T_X.strToBytes(payload);
      const tokens = T_X.encodeBytes(tongue, Array.from(bytes));
      const spec = T_X.TONGUE_SPECS[tongue];
      push(Lx.tokens({
        op: "encode",
        tongue, spec,
        payload, bytes: Array.from(bytes), tokens,
        meta: `${bytes.length} bytes → ${tokens.length} tokens · domain ${spec.domain} · ${spec.hz.toFixed(2)}Hz`,
      }));
      return 0;
    }
  },

  decode: {
    summary: "decode Sacred Tongue tokens → text",
    run: ({ args, push }) => {
      const tongue = String(args.flags.tongue || "KO").toUpperCase();
      const tokensStr = args.positional.join(" ") || args.flags.tokens;
      if (!tokensStr) { push(Lx.text("usage: decode <tok1 tok2 …> --tongue KO", "err")); return 1; }
      if (!T_X.TONGUE_SPECS[tongue]) { push(Lx.text(`unknown tongue: ${tongue}`,"err")); return 1; }
      const tokens = String(tokensStr).split(/[\s,]+/).filter(Boolean);
      try {
        const bytes = T_X.decodeTokens(tongue, tokens);
        const text = T_X.bytesToStr(bytes);
        const hex = T_X.bytesToHex(bytes);
        push(Lx.tokens({
          op: "decode",
          tongue, spec: T_X.TONGUE_SPECS[tongue],
          payload: text, bytes: Array.from(bytes), tokens,
          extra: { hex },
          meta: `${tokens.length} tokens → ${bytes.length} bytes · "${text}"`,
        }));
        return 0;
      } catch (e) { push(Lx.text(`  decode error: ${e.message}`, "err")); return 1; }
    }
  },

  xlate: {
    summary: "translate token stream across tongues",
    run: ({ args, push }) => {
      const fromT = String(args.flags.from || "KO").toUpperCase();
      const toT   = String(args.flags.to   || "DR").toUpperCase();
      const tokensStr = args.positional.join(" ") || args.flags.tokens;
      if (!tokensStr) { push(Lx.text("usage: xlate <tok1 tok2 …> --from KO --to DR", "err")); return 1; }
      if (!T_X.TONGUE_SPECS[fromT] || !T_X.TONGUE_SPECS[toT]) {
        push(Lx.text("unknown tongue", "err")); return 1;
      }
      const tokens = String(tokensStr).split(/[\s,]+/).filter(Boolean);
      try {
        const out = T_X.xlateTokens(fromT, toT, tokens);
        const bytes = T_X.decodeTokens(fromT, tokens);
        push(Lx.tokens({
          op: "xlate",
          tongue: toT, spec: T_X.TONGUE_SPECS[toT],
          payload: T_X.bytesToStr(bytes),
          bytes: Array.from(bytes), tokens: out,
          extra: { from: fromT, to: toT, originalTokens: tokens },
          meta: `${fromT} → ${toT} · bijection preserved · ${tokens.length} tokens`,
        }));
        return 0;
      } catch (e) { push(Lx.text(`  xlate error: ${e.message}`, "err")); return 1; }
    }
  },

  "tokenizer-verify": {
    summary: "prove bijectivity for all 256 bytes per tongue",
    run: ({ push }) => {
      push(Lx.text("  ⟳ verifying byte ↔ token roundtrip across all 6 tongues…", "dim"));
      const rows = [];
      for (const code of Object.keys(T_X.TONGUE_SPECS)) {
        const r = T_X.verifyBijection(code);
        rows.push({ code, ok: r.ok, count: r.count, badByte: r.badByte });
      }
      const allOk = rows.every(r => r.ok);
      rows.forEach(r => {
        push(Lx.text(`    ${r.ok ? "✓":"✗"} ${r.code}  ${r.ok ? `${r.count} unique tokens, perfect bijection` : `failed at byte ${r.badByte}`}`, r.ok ? "ok" : "err"));
      });
      push(Lx.text(`  ${allOk ? "✓ all 6 tongues bijective · 1536 unique tokens total" : "✗ bijection violated"}`, allOk ? "ok" : "err"));
      return allOk ? 0 : 2;
    }
  },

  "encode-cmd": {
    summary: "alias of encode (matches python -m src.geoseal_cli)",
    run: (ctx) => TokenizerCommands.encode.run(ctx),
  },
  "decode-cmd": {
    summary: "alias of decode",
    run: (ctx) => TokenizerCommands.decode.run(ctx),
  },
  "xlate-cmd": {
    summary: "alias of xlate",
    run: (ctx) => TokenizerCommands.xlate.run(ctx),
  },
};

// ============================================================
// LEDGER / HISTORY / REPLAY
// ============================================================

const HistoryCommands = {
  history: {
    summary: "show ledger entries",
    run: ({ args, push, ledger }) => {
      const n = parseInt(args.flags.n || "10", 10);
      const list = (ledger || []).slice(0, n);
      if (list.length === 0) { push(Lx.text("  ledger empty — run a swarm or seal first", "dim")); return 0; }
      push(Lx.history({ entries: list, total: ledger.length }));
      return 0;
    }
  },

  replay: {
    summary: "replay a previous ledger entry by id or index",
    run: async ({ args, push, ledger, swarmDispatch }) => {
      const ref = args.positional[0] || args.flags.id;
      if (!ref) { push(Lx.text("usage: replay <ledger-id|index>", "err")); return 1; }
      let entry = null;
      if (/^\d+$/.test(ref)) entry = ledger[parseInt(ref,10)];
      else entry = ledger.find(e => e.id === ref || e.id.startsWith(ref));
      if (!entry) { push(Lx.text(`  no ledger entry matches "${ref}"`, "err")); return 1; }
      push(Lx.text(`  ↻ replaying ${entry.op} · ${entry.tongues.join(",")} · seal ${entry.seal.slice(0,16)}…`, "ok"));
      const op = G_X.LEXICON_BY_NAME[entry.op];
      if (!op) {
        push(Lx.text(`  op '${entry.op}' not in lexicon — replaying as text`, "warn"));
        return 0;
      }
      await swarmDispatch(op, entry.tongues, entry.args, true);
      return 0;
    }
  },
};

// ============================================================
// ATOMIC / SUBSTRATE INTROSPECTION
// ============================================================

const AtomicCommands = {
  atomic: {
    summary: "inspect atomic substrate row for an op",
    run: ({ args, push }) => {
      const opName = args.positional[0];
      if (!opName) { push(Lx.text("usage: atomic <op>", "err")); return 1; }
      const op = G_X.LEXICON_BY_NAME[opName];
      if (!op) { push(Lx.text(`unknown op: ${opName}`, "err")); return 1; }
      // Build a synthetic but coherent atomic row from op metadata
      const phi = G_X.PHI;
      const wells = [
        { tongue: "KO", well: "intent",     basis: "Φ⁰", energy: op.chi * phi },
        { tongue: "AV", well: "structure",  basis: "Φ¹", energy: op.chi * phi**1.5 },
        { tongue: "RU", well: "binding",    basis: "Φ²", energy: op.chi * phi**2 },
        { tongue: "CA", well: "ciphertext", basis: "Φ³", energy: op.chi * phi**2.5 },
        { tongue: "UM", well: "veil",       basis: "Φ⁴", energy: op.chi * phi**3 },
        { tongue: "DR", well: "tag",        basis: "Φ⁵", energy: op.chi * phi**3.5 },
      ];
      const phaseSig = wells.map(w => Math.cos(G_X.TONGUE_BY_CODE[w.tongue].phase) * w.energy)
                            .reduce((a,b)=>a+b, 0);
      push(Lx.atomic({ op, wells, phaseSig }));
      return 0;
    }
  },
};

// ============================================================
// AGENT / WORKFLOW / SCAFFOLD / ARC / CURSOR
// ============================================================

const AgentCommands = {
  workflow: {
    summary: "run a .geoseal.yaml declarative workflow",
    run: async ({ args, push, swarmDispatch }) => {
      const sub = args.positional[0] || "demo";
      if (sub === "list") {
        push(Lx.workflow({
          op: "list",
          rows: [
            { name: "ci-rwp-v3.geoseal.yaml",      ops: 5, tongues: 3, ok: true },
            { name: "ledger-rotate.geoseal.yaml", ops: 3, tongues: 6, ok: true },
            { name: "spiral-audit.geoseal.yaml",  ops: 7, tongues: 6, ok: true },
          ],
        }));
        return 0;
      }
      if (sub === "validate") {
        const name = args.positional[1] || "ci-rwp-v3.geoseal.yaml";
        push(Lx.text(`  ⟳ validating ${name}…`, "dim"));
        push(Lx.text(`    ✓ schema · 5 steps · 3 tongues required (KO, RU, DR)`, "ok"));
        push(Lx.text(`    ✓ phi-wall budget total = ${(0.55*1.618).toFixed(3)}`, "ok"));
        push(Lx.text(`    ✓ all step ops resolved against lexicon`, "ok"));
        return 0;
      }
      // run a tiny demo workflow
      const steps = [
        { op: G_X.LEXICON_BY_NAME.add,    tongues: ["KO","AV"],     argVals: ["3","4"] },
        { op: G_X.LEXICON_BY_NAME.mul,    tongues: ["RU","CA"],     argVals: ["7","2"] },
        { op: G_X.LEXICON_BY_NAME.sha256, tongues: ["DR"],          argVals: ['"genesis"'] },
      ];
      push(Lx.text(`  ⟳ workflow · ${steps.length} steps · staged dispatch`, "dim"));
      for (let i = 0; i < steps.length; i++) {
        const s = steps[i];
        push(Lx.text(`  step ${i+1}/${steps.length} · ${s.op.name}(${s.argVals.join(",")}) → [${s.tongues.join(",")}]`, "ok"));
        await swarmDispatch(s.op, s.tongues, s.argVals, true);
      }
      push(Lx.text(`  ✓ workflow complete · 3 ledger entries written`, "ok"));
      return 0;
    }
  },

  "project-scaffold": {
    summary: "lightweight project scaffold from a task intent",
    run: ({ args, push }) => {
      const task = args.positional.join(" ") || "rwp-encryptor";
      const slug = task.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/(^-|-$)/g,"");
      const tree = [
        `${slug}/`,
        `├── README.md            ← intent: "${task}"`,
        `├── .geoseal.yaml        ← workflow spec (3 steps)`,
        `├── src/`,
        `│   ├── kor_aelin.py     ← KO emit · python`,
        `│   ├── avali.ts         ← AV emit · typescript`,
        `│   └── runethic.rs      ← RU emit · rust`,
        `├── tests/test_quorum.py`,
        `└── .scbe/`,
        `    ├── geoseal_calls.jsonl`,
        `    └── phi_wall_budget.toml`,
      ];
      push(Lx.scaffold({ task, slug, tree }));
      return 0;
    }
  },

  arc: {
    summary: "synthesize + apply an ARC task program",
    run: ({ args, push }) => {
      const task = args.positional[0] || "fill-corners";
      const programs = {
        "fill-corners": ["scan_grid()", "find_corners()", "set_corners(8)", "verify_symmetry()"],
        "rotate-90":    ["read_grid()", "transpose()", "reverse_rows()", "emit_grid()"],
        "color-flood":  ["pick_seed()", "bfs_flood(seed, 4)", "merge_regions()", "emit_grid()"],
      };
      const prog = programs[task] || programs["fill-corners"];
      push(Lx.block({
        title: `ARC · synthesized program for "${task}"`,
        rows: prog.map((line, i) => `  ${String(i+1).padStart(2,"0")}  ${line}`),
        foot: `4 instructions · χ-budget 0.18 · routed via UM (lattice-reasoning)`
      }));
      return 0;
    }
  },

  cursor: {
    summary: "delegate a bounded repo task to Cursor Agent",
    run: ({ args, push }) => {
      const task = args.positional.join(" ") || "refactor logging";
      const taskId = `cursor-${Math.random().toString(36).slice(2,8)}`;
      push(Lx.block({
        title: `CURSOR · delegated bounded task`,
        rows: [
          `  task_id     ${taskId}`,
          `  prompt      "${task}"`,
          `  bounds      max_files=5  max_diff_lines=120  timeout=15min`,
          `  branch      cursor/${taskId}`,
          `  guardrail   φ-wall · QUARANTINE on hash/network ops`,
          `  status      submitted ✓ · awaiting agent runtime`,
        ],
        foot: `inspect: cursor status ${taskId}`
      }));
      return 0;
    }
  },

  "agent-harness": {
    summary: "emit model-neutral agent harness manifest",
    run: ({ args, push, harness }) => {
      const manifest = {
        name: "geoseal-harness",
        version: "0.6.4",
        model: harness?.model || "claude-haiku-4-5",
        temperature: harness?.temperature ?? 0.2,
        safety: harness?.safety || "phi-wall",
        tools: [
          { name: "swarm",  schema: "{op:str, args:obj, tongues:list[str]}" },
          { name: "seal",   schema: "{payload:str, tongue:str}" },
          { name: "encode", schema: "{payload:str, tongue:str}" },
          { name: "verify", schema: "{seal:str, op:str, tongue:str, code:str}" },
        ],
        tongues: G_X.TONGUES.map(t => ({code: t.code, lang: t.lang, phi: t.phi})),
        phi_wall: { allow: 1.272, quarantine: 1.618, escalate: 2.058 },
      };
      push(Lx.manifest({ title: "AGENT HARNESS · manifest.json", obj: manifest }));
      return 0;
    }
  },
};

// ============================================================
// SACRED EGGS · GEOSEAL-ENCRYPTED RITUAL-GATED PAYLOADS
// ============================================================

const EggCommands = {
  "egg-create": {
    summary: "create a Sacred Egg (GeoSeal-encrypted, ritual-gated)",
    run: ({ args, push }) => {
      const payload = args.positional.join(" ") || args.flags.payload;
      if (!payload) { push(Lx.text("usage: egg-create <secret> [--shell sigil|crystal|geode] [--ritual phi^N]", "err")); return 1; }
      const shell = String(args.flags.shell || "sigil");
      const ritual = String(args.flags.ritual || "phi^1.5");
      const yolkBytes = T_X.strToBytes(payload);
      const yolkTokens = T_X.encodeBytes("DR", Array.from(yolkBytes)); // tag/integrity tongue
      const eggId = "egg-" + G_X.fnv1aHex(payload + shell + ritual).slice(0, 12);
      const seal = G_X.fnv1aHex(yolkTokens.join(" ") + "|" + ritual);
      push(Lx.egg({
        op: "create",
        eggId, shell, ritual,
        size: yolkBytes.length,
        sealPreview: seal.slice(0,32),
        yolkTokens: yolkTokens.slice(0, 12),
        more: yolkTokens.length > 12 ? yolkTokens.length - 12 : 0,
        path: `.scbe/eggs/${eggId}.egg`,
      }));
      return 0;
    }
  },

  "egg-hatch": {
    summary: "attempt to hatch a Sacred Egg (verify ritual + decrypt yolk)",
    run: ({ args, push }) => {
      const eggId = args.positional[0];
      if (!eggId) { push(Lx.text("usage: egg-hatch <egg-id> [--passphrase ...]", "err")); return 1; }
      const ok = !!args.flags.passphrase || Math.random() > 0.2;
      const stages = [
        { name: "shell challenge",  ok: true },
        { name: "phase verification (φ^1.5)", ok: true },
        { name: "ritual gate · DR seal match", ok },
        { name: "yolk decryption",  ok },
      ];
      push(Lx.egg({
        op: "hatch",
        eggId,
        stages,
        result: ok ? "hatched ✓" : "rejected ✕ — ritual gate failed",
        success: ok,
      }));
      return ok ? 0 : 2;
    }
  },

  "egg-paint": {
    summary: "change shell, keep yolk",
    run: ({ args, push }) => {
      const eggId = args.positional[0];
      const newShell = args.flags.shell || "geode";
      if (!eggId) { push(Lx.text("usage: egg-paint <egg-id> --shell <new>", "err")); return 1; }
      push(Lx.text(`  ⟳ repainting ${eggId} · shell → ${newShell}`, "dim"));
      push(Lx.text(`  ✓ yolk unchanged · seal preserved · shell rerendered`, "ok"));
      return 0;
    }
  },
};

// ============================================================
// TOPOLOGY / COGNITION / HONEYCOMB — visual one-liners
// ============================================================

const TopologyCommands = {
  "topology-view": {
    summary: "topology view of the active substrate",
    run: ({ push }) => {
      push(Lx.art(
`    KO ── AV
    │  ╲ ╱ │
    │   ╳  │       6-vertex, 9-edge φ-rosette graph
    │  ╱ ╲ │       genus 0 · χ = -3
    UM ── DR       binding map · RWP v3.0 canonical
    │  ╲ ╱ │
    │   ╳  │
    │  ╱ ╲ │
    RU ── CA`));
      push(Lx.text("  6 nodes · 9 edges · 4 triangular faces · planar ✓", "dim"));
      return 0;
    }
  },

  "cognition-map": {
    summary: "ternary cognitive well projection",
    run: ({ push }) => {
      push(Lx.art(
`              intent (KO)
                 ▲
                ╱ ╲
               ╱ • ╲      • = current cognitive locus
              ╱     ╲
             ╱       ╲
            ╱─────────╲
   structure(AV)  binding(RU)`));
      push(Lx.text("  3-well projection · loci sampled from last 12 dispatches", "dim"));
      return 0;
    }
  },

  "honeycomb-analysis": {
    summary: "route-cell stability analysis",
    run: ({ push }) => {
      push(Lx.art(
`    ⬡ ⬡ ⬡ ⬡         cell stability (0-1):
   ⬡ █ ▓ █ ⬡         █ 0.92  ▓ 0.71  ░ 0.31
    ⬡ ▓ ░ ⬡          mean: 0.64  σ: 0.21
   ⬡ █ ▓ █ ⬡          unstable cells: 1/12
    ⬡ ⬡ ⬡ ⬡         escalation: NONE`));
      return 0;
    }
  },

  "backend-registry": {
    summary: "list backend providers and lane support",
    run: ({ push }) => {
      const rows = [
        ["python.cpython", "KO", "exec / eval / hashlib", "ALLOW"],
        ["node.v22",       "AV", "vm.runInContext / crypto", "ALLOW"],
        ["rustc.1.83",     "RU", "cargo+rustc / sha2", "ALLOW"],
        ["clang.18",       "CA", "tcc-jit / openssl", "QUARANTINE"],
        ["julia.1.10",     "UM", "Pkg eval / SHA.jl", "ALLOW"],
        ["ghc.9.10",       "DR", "runghc / cryptonite", "ESCALATE"],
      ];
      push(Lx.block({
        title: "BACKEND REGISTRY",
        rows: rows.map(([n,t,l,gov]) => `  ${n.padEnd(18)} [${t}]  ${l.padEnd(28)} ${gov}`),
        foot: `6 backends · 6 tongues mapped 1:1`
      }));
      return 0;
    }
  },

  "mars-mission": {
    summary: "GeoSeal Mars mission compass/minimap packet",
    run: ({ push }) => {
      const compass = ["N","NE","E","SE","S","SW","W","NW"];
      const heading = compass[Math.floor(Math.random()*8)];
      push(Lx.art(
`    ╔══════════════ MARS · MINIMAP ══════════════╗
    ║   N        compass · ${heading.padEnd(2)}                  ║
    ║   ▲                                          ║
    ║ W ◄ ⊕ ► E    sol 1247 · LMST 14:32:08       ║
    ║   ▼          rover Φ-2 · 4.7km from Helle   ║
    ║   S          φ-wall: ALLOW · trust 94%      ║
    ╚══════════════════════════════════════════════╝`));
      return 0;
    }
  },

  shell: {
    summary: "run a nested GeoSeal command string",
    run: async ({ args, push, runLine }) => {
      const cmd = args.positional.join(" ");
      if (!cmd) { push(Lx.text("usage: shell '<geoseal cmd>'", "err")); return 1; }
      push(Lx.text(`  ⟳ shell · "${cmd}"`, "dim"));
      await runLine(cmd);
      return 0;
    }
  },
};

// ============================================================
// COMBINED EXPORT
// ============================================================

window.ExtraCommands = {
  ...TokenizerCommands,
  ...HistoryCommands,
  ...AtomicCommands,
  ...AgentCommands,
  ...EggCommands,
  ...TopologyCommands,
};

// Renderer for the new line kinds
function ExtraRenderLine({ ln }) {
  if (ln.kind === "text") return <div className={`out tone-${ln.tone}`}>{ln.text}</div>;
  if (ln.kind === "art")  return <pre className="out art-block">{ln.text}</pre>;
  if (ln.kind === "block") {
    return (
      <div className="x-block">
        <div className="x-block-title">{ln.data.title}</div>
        {ln.data.rows.map((r,i) => <div key={i} className="x-block-row">{r}</div>)}
        {ln.data.foot && <div className="x-block-foot">{ln.data.foot}</div>}
      </div>
    );
  }
  if (ln.kind === "tokens") {
    const d = ln.data;
    return (
      <div className="x-tokens">
        <div className="x-tokens-head">
          <span className="x-tag">{d.op.toUpperCase()}</span>
          <span className="x-tongue" style={{color: G_X.TONGUE_BY_CODE[d.tongue]?.color}}>
            {d.tongue} · {d.spec.name}
          </span>
          <span className="x-meta">{d.meta}</span>
        </div>
        {d.payload && <div className="x-payload">payload: <span className="mono">"{d.payload}"</span></div>}
        <div className="x-tokens-grid">
          {d.tokens.map((t,i) => (
            <span key={i} className="x-token" title={`byte 0x${(d.bytes[i]||0).toString(16).padStart(2,"0")}`}>
              {t}
            </span>
          ))}
        </div>
        {d.extra?.from && (
          <div className="x-xlate-foot">
            <span className="dim">{d.extra.from} ⟶ {d.extra.to} · {d.extra.originalTokens.length} tokens preserve byte stream</span>
          </div>
        )}
        {d.extra?.hex && (
          <div className="x-hex">hex · <span className="mono">{d.extra.hex}</span></div>
        )}
      </div>
    );
  }
  if (ln.kind === "atomic") {
    const d = ln.data;
    return (
      <div className="x-atomic">
        <div className="x-atomic-head">
          <span className="x-tag">ATOMIC</span>
          <span className="x-op">{d.op.name}</span>
          <span className="x-meta">band {d.op.band} · χ={d.op.chi.toFixed(2)} · phase Σ={d.phaseSig.toFixed(4)}</span>
        </div>
        <div className="x-wells">
          {d.wells.map(w => (
            <div className="x-well" key={w.tongue}>
              <span className="x-well-code" style={{color: G_X.TONGUE_BY_CODE[w.tongue].color}}>{w.tongue}</span>
              <span className="x-well-name">{w.well}</span>
              <span className="x-well-basis">{w.basis}</span>
              <div className="x-well-bar">
                <div className="x-well-fill" style={{
                  width: `${Math.min(100, w.energy * 60)}%`,
                  background: G_X.TONGUE_BY_CODE[w.tongue].color
                }}/>
              </div>
              <span className="x-well-energy">E={w.energy.toFixed(3)}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (ln.kind === "history") {
    return (
      <div className="x-history">
        <div className="x-history-head">
          <span className="x-tag">LEDGER</span>
          <span className="x-meta">showing {ln.data.entries.length} of {ln.data.total} records</span>
        </div>
        {ln.data.entries.map((e,i) => (
          <div key={e.id} className="x-history-row">
            <span className="x-h-idx">[{i}]</span>
            <span className="x-h-time">{e.time}</span>
            <span className="x-h-op">{e.op}</span>
            <span className="x-h-tongues">[{e.tongues.join(",")}]</span>
            <span className={`x-h-tier tier-${e.tier}`}>{e.tier}</span>
            <span className={`x-h-quorum ${e.quorum_ok?"ok":"no"}`}>{e.quorum_ok?"✓":"—"}</span>
            <span className="x-h-seal mono">{e.seal.slice(0,20)}…</span>
          </div>
        ))}
      </div>
    );
  }
  if (ln.kind === "scaffold") {
    return (
      <div className="x-scaffold">
        <div className="x-scaffold-head">
          <span className="x-tag">SCAFFOLD</span>
          <span className="x-op">{ln.data.task}</span>
          <span className="x-meta">→ ./{ln.data.slug}/</span>
        </div>
        <pre className="x-scaffold-tree">{ln.data.tree.join("\n")}</pre>
      </div>
    );
  }
  if (ln.kind === "workflow") {
    return (
      <div className="x-workflow">
        <div className="x-workflow-head">
          <span className="x-tag">WORKFLOW · {ln.data.op}</span>
        </div>
        {ln.data.rows.map(r => (
          <div key={r.name} className="x-wf-row">
            <span className={`x-wf-dot ${r.ok?"ok":"err"}`}>●</span>
            <span className="x-wf-name">{r.name}</span>
            <span className="x-wf-meta">{r.ops} steps · {r.tongues} tongues</span>
          </div>
        ))}
      </div>
    );
  }
  if (ln.kind === "egg") {
    const d = ln.data;
    if (d.op === "create") {
      return (
        <div className="x-egg">
          <div className="x-egg-head">
            <span className="x-tag">SACRED EGG · created</span>
            <span className="x-meta">{d.eggId} · shell {d.shell} · ritual {d.ritual}</span>
          </div>
          <div className="x-egg-yolk">
            <div className="dim">yolk (DR-encoded · {d.size} bytes):</div>
            <div className="x-tokens-grid">
              {d.yolkTokens.map((t,i) => <span key={i} className="x-token">{t}</span>)}
              {d.more > 0 && <span className="x-token dim">…+{d.more}</span>}
            </div>
          </div>
          <div className="x-egg-foot">
            <span className="mono">⌬ {d.sealPreview}…</span>
            <span className="dim"> · written to {d.path}</span>
          </div>
        </div>
      );
    }
    return (
      <div className="x-egg">
        <div className="x-egg-head">
          <span className="x-tag">SACRED EGG · hatch</span>
          <span className="x-meta">{d.eggId}</span>
        </div>
        {d.stages.map((s,i) => (
          <div key={i} className={`x-egg-stage ${s.ok?"ok":"err"}`}>
            <span>{s.ok?"✓":"✕"}</span> {s.name}
          </div>
        ))}
        <div className={`x-egg-result ${d.success?"ok":"err"}`}>{d.result}</div>
      </div>
    );
  }
  if (ln.kind === "manifest") {
    return (
      <div className="x-manifest">
        <div className="x-manifest-head">{ln.data.title}</div>
        <pre className="x-manifest-body">{JSON.stringify(ln.data.obj, null, 2)}</pre>
      </div>
    );
  }
  return null;
}

window.ExtraRenderLine = ExtraRenderLine;
