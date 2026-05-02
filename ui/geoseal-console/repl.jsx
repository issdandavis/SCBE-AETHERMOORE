// REPL — terminal-style command surface for the GeoSeal CLI.

const { useState, useEffect, useRef, useCallback } = React;

const G = window.GeoSeal;

// ---- HF pair-call harness (replaces window.claude.complete) ----
async function harnessPairCall(harness, prompt, system) {
  const url = (harness?.bridgeUrl || "http://127.0.0.1:8765") + "/harness/pair";
  const body = {
    prompt,
    system: system || undefined,
    temperature: harness?.temperature ?? 0.2,
    max_tokens: harness?.maxTokens || 1024,
  };
  const models = [harness?.modelA, harness?.modelB].filter(Boolean);
  if (models.length === 2) body.models = models;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const txt = await resp.text().catch(() => "");
    throw new Error(`bridge ${resp.status}: ${txt.slice(0, 200) || resp.statusText}`);
  }
  return await resp.json();
}

// Pick one completion for downstream parsing — prefer the agreed text;
// otherwise fall back to whichever side returned ok=true first.
function pickPairText(pair) {
  if (!pair) return "";
  if (pair.agree && pair.a?.text) return pair.a.text;
  if (pair.a?.ok && pair.a.text) return pair.a.text;
  if (pair.b?.ok && pair.b.text) return pair.b.text;
  return pair.a?.text || pair.b?.text || "";
}

// ---- argument parsing: `geoseal swarm add --a 2 --b 3 --tongues KO,AV,UM` ----
function parseCommand(line) {
  const tokens = line.trim().split(/\s+/).filter(Boolean);
  if (tokens.length === 0) return null;
  // strip a leading `geoseal` / `python -m src.geoseal_cli`
  if (tokens[0] === "geoseal") tokens.shift();
  else if (tokens[0] === "python" && tokens[1] === "-m") tokens.splice(0, 3);

  const cmd = tokens.shift();
  const positional = [];
  const flags = {};
  while (tokens.length) {
    const t = tokens.shift();
    if (t.startsWith("--")) {
      const key = t.slice(2);
      const next = tokens[0];
      if (next !== undefined && !next.startsWith("--")) {
        flags[key] = tokens.shift();
      } else {
        flags[key] = true;
      }
    } else {
      positional.push(t);
    }
  }
  return { cmd, positional, flags };
}

// ---- output line builders ----
const L = {
  prompt: (cmd) => ({ kind: "prompt", text: cmd }),
  text:   (text, tone="neutral") => ({ kind: "text", text, tone }),
  rule:   () => ({ kind: "rule" }),
  banner: () => ({ kind: "banner" }),
  table:  (rows) => ({ kind: "table", rows }),
  swarm:  (data) => ({ kind: "swarm", data }),
  seal:   (data) => ({ kind: "seal", data }),
  emit:   (data) => ({ kind: "emit", data }),
  help:   (data) => ({ kind: "help", data }),
};

// ---- command implementations ----
const COMMANDS = {
  help: {
    summary: "list commands and usage",
    run: ({ args, push }) => {
      push(L.help({
        title: "GEOSEAL · console reference",
        rows: [
          ["ops",        "list lexicon ops",                "ops [--band ARITH|LOGIC|...]"],
          ["emit",       "emit op in all tongues",          "emit <op> [--<arg> <val>] [--tongue KO]"],
          ["run",        "emit + execute one tongue",       "run <op> --<arg> <val> --tongue KO"],
          ["swarm",      "dispatch to N tongues",           "swarm <op> --tongues KO,AV --<a> 7 --<b> 3"],
          ["seal",       "stamp arbitrary payload",         "seal <text> [--tongue KO]"],
          ["verify",     "verify a seal hash",              "verify <seal> --op <op> --tongue T --code C"],
          ["","",""],
          ["encode",     "text → Sacred Tongue tokens",     "encode <text> --tongue KO"],
          ["decode",     "tokens → text",                   "decode <tok1 tok2 …> --tongue KO"],
          ["xlate",      "translate tokens across tongues", "xlate <toks…> --from KO --to DR"],
          ["tokenizer-verify","prove 256-byte bijection",   "tokenizer-verify"],
          ["","",""],
          ["history",    "show ledger entries",             "history [--n 10]"],
          ["replay",     "replay a ledger entry",           "replay <id|index>"],
          ["atomic",     "atomic substrate row for an op",  "atomic <op>"],
          ["","",""],
          ["workflow",   ".geoseal.yaml runner",            "workflow [list|validate|run]"],
          ["project-scaffold","build project scaffold",     "project-scaffold <task>"],
          ["arc",        "synthesize ARC program",          "arc <task>"],
          ["cursor",     "delegate to Cursor Agent",        "cursor <prompt>"],
          ["agent-harness","emit harness manifest",         "agent-harness"],
          ["","",""],
          ["egg-create", "GeoSeal-encrypted ritual egg",    "egg-create <secret> [--shell sigil]"],
          ["egg-hatch",  "hatch a Sacred Egg",              "egg-hatch <egg-id>"],
          ["egg-paint",  "reshell, keep yolk",              "egg-paint <egg-id> --shell geode"],
          ["","",""],
          ["topology-view",     "6-tongue topology graph",  "topology-view"],
          ["cognition-map",     "ternary well projection",  "cognition-map"],
          ["honeycomb-analysis","route-cell stability",     "honeycomb-analysis"],
          ["backend-registry",  "backends ↔ tongues",       "backend-registry"],
          ["mars-mission",      "compass + minimap packet", "mars-mission"],
          ["","",""],
          ["ask",     "AI: natural-language → swarm",       "ask <free-text request>"],
          ["explain", "AI: explain last ledger entry",      "explain"],
          ["agent",   "rule-based task tokenizer",          "agent <task...>"],
          ["shell",   "run a nested geoseal command",       "shell '<cmd>'"],
          ["tongues", "show 6-tongue map",                  "tongues"],
          ["clear",   "clear scrollback (^L)",              "clear"],
        ],
      }));
      return 0;
    }
  },

  tongues: {
    summary: "show tongue map",
    run: ({ push }) => {
      push(L.text("┌─────┬───────────────┬──────────────┬─────────┬──────────┐", "dim"));
      push(L.text("│ CODE│ CONLANG       │ LANGUAGE     │ φ-WEIGHT│ PHASE θ  │", "dim"));
      push(L.text("├─────┼───────────────┼──────────────┼─────────┼──────────┤", "dim"));
      G.TONGUES.forEach(t => {
        const phaseDeg = (t.phase * 180 / Math.PI).toFixed(0).padStart(3);
        push({
          kind: "tongue-row", t, phaseDeg
        });
      });
      push(L.text("└─────┴───────────────┴──────────────┴─────────┴──────────┘", "dim"));
      return 0;
    }
  },

  ops: {
    summary: "list lexicon",
    run: ({ args, push }) => {
      const band = args.flags.band;
      const list = G.LEXICON.filter(e => !band || e.band === String(band).toUpperCase());
      if (list.length === 0) {
        push(L.text(`no ops in band ${band}`, "warn"));
        return 1;
      }
      push(L.text(`  ID    NAME           BAND        χ      ARGS`, "dim"));
      list.forEach(e => {
        push({ kind: "op-row", op: e });
      });
      push(L.text(`  ${list.length} op${list.length===1?"":"s"} listed`, "dim"));
      return 0;
    }
  },

  emit: {
    summary: "emit code in all tongues",
    run: ({ args, push }) => {
      const opName = args.positional[0];
      if (!opName) { push(L.text("usage: emit <op> [--<arg> <val>] [--tongue KO]","err")); return 1; }
      const op = G.LEXICON_BY_NAME[opName];
      if (!op) { push(L.text(`unknown op: ${opName}`,"err")); return 1; }
      const filterTongue = args.flags.tongue ? String(args.flags.tongue).toUpperCase() : null;
      const argVals = op.args.map(a => args.flags[a] ?? `<${a}>`);
      const tongues = G.TONGUES.filter(t => !filterTongue || t.code === filterTongue);
      const emits = tongues.map(t => ({
        tongue: t,
        code: op.emit[t.code](...argVals),
      }));
      push(L.emit({ op, args: argVals, emits }));
      return 0;
    }
  },

  run: {
    summary: "emit + execute one tongue",
    run: async ({ args, push, swarmDispatch }) => {
      const opName = args.positional[0];
      const tongue = String(args.flags.tongue || "KO").toUpperCase();
      if (!opName) { push(L.text("usage: run <op> --<arg> <val> --tongue KO","err")); return 1; }
      const op = G.LEXICON_BY_NAME[opName];
      if (!op) { push(L.text(`unknown op: ${opName}`,"err")); return 1; }
      const argVals = op.args.map(a => args.flags[a] ?? "0");
      await swarmDispatch(op, [tongue], argVals, /*execute*/true);
      return 0;
    }
  },

  swarm: {
    summary: "dispatch to multiple tongues",
    run: async ({ args, push, swarmDispatch }) => {
      const opName = args.positional[0];
      if (!opName) { push(L.text("usage: swarm <op> --tongues KO,AV,RU --<arg> <val>","err")); return 1; }
      const op = G.LEXICON_BY_NAME[opName];
      if (!op) { push(L.text(`unknown op: ${opName}`,"err")); return 1; }
      const tongueList = String(args.flags.tongues || "KO,AV,RU,CA,UM,DR")
        .toUpperCase().split(",").map(s=>s.trim()).filter(Boolean);
      const argVals = op.args.map(a => args.flags[a] ?? "0");
      await swarmDispatch(op, tongueList, argVals, /*execute*/true);
      return 0;
    }
  },

  seal: {
    summary: "stamp a payload",
    run: ({ args, push }) => {
      const payload = args.positional.join(" ") || args.flags.payload;
      if (!payload) { push(L.text("usage: seal <text> [--tongue KO]","err")); return 1; }
      const tongue = String(args.flags.tongue || "KO").toUpperCase();
      const op = "seal";
      const code = `seal(${JSON.stringify(payload)})`;
      const cost = G.phiWallCost(0.55, tongue);
      const tier = G.phiWallTier(cost);
      const trust = G.phiTrustScore(cost);
      const seal = G.computeSeal(op, tongue, code, payload, cost, tier);
      push(L.seal({ payload, tongue, op, code, seal, cost, tier, trust, phase: G.TONGUE_BY_CODE[tongue].phase }));
      return 0;
    }
  },

  verify: {
    summary: "verify a seal",
    run: ({ args, push }) => {
      const expected = args.positional[0];
      const op = String(args.flags.op || "");
      const tongue = String(args.flags.tongue || "KO").toUpperCase();
      const code = String(args.flags.code || "");
      const payload = String(args.flags.payload || "");
      if (!expected || !op) {
        push(L.text("usage: verify <seal> --op <op> --tongue KO --code <code> [--payload <p>]","err"));
        return 1;
      }
      const cost = G.phiWallCost(G.LEXICON_BY_NAME[op]?.chi ?? 0.5, tongue);
      const tier = G.phiWallTier(cost);
      const recomputed = G.computeSeal(op, tongue, code, payload, cost, tier);
      const ok = recomputed === expected;
      push(L.text(ok ? "  ✓ seal verified · phase + φ-cost match"
                     : "  ✗ seal MISMATCH · governance violation",
                  ok ? "ok" : "err"));
      push(L.text(`    expected: ${expected.slice(0,32)}…`, "dim"));
      push(L.text(`    computed: ${recomputed.slice(0,32)}…`, "dim"));
      return ok ? 0 : 2;
    }
  },

  ask: {
    summary: "ask the AI harness in natural language",
    run: async ({ args, push, swarmDispatch, harness }) => {
      const prompt = args.positional.join(" ");
      if (!prompt) { push(L.text("usage: ask <natural language request>","err")); return 1; }
      if (!harness?.enabled) { push(L.text("  AI harness is OFFLINE — toggle in Tweaks → AI Harness", "warn")); return 1; }
      push(L.text(`  ⟳ harness · ${harness.model} · temp ${harness.temperature.toFixed(2)} · "${prompt}"`, "dim"));
      const opNames = G.LEXICON.map(o => `${o.name}(${o.args.join(",")})[χ=${o.chi}]`).join(", ");
      const tongueList = G.TONGUES.map(t => `${t.code}=${t.lang}`).join(", ");
      const sys = `You are a router for the GeoSeal CLI. Convert the user's natural-language request into ONE JSON object with this exact shape (no prose, no fences):
{"cmd":"swarm|run|emit|seal","op":"<op-name>","args":{"<arg>":"<val>",...},"tongues":["KO","AV",...],"reason":"<one short sentence>"}
Available ops: ${opNames}
Tongues: ${tongueList}
Pick at least 3 tongues for swarm. For seal, set "op":"seal" and put the payload in args.payload.`;
      try {
        const pair = await harnessPairCall(harness, `User: ${prompt}`, sys);
        const aTag = (harness?.modelA || "A").split("/").pop();
        const bTag = (harness?.modelB || "B").split("/").pop();
        push(L.text(`  ⇣ ${aTag} (${pair.a?.latency_ms ?? "?"}ms) ${pair.a?.ok ? "ok" : "ERR"}` + (pair.a?.error ? ` · ${pair.a.error.slice(0,120)}` : ""), pair.a?.ok ? "dim" : "err"));
        push(L.text(`  ⇣ ${bTag} (${pair.b?.latency_ms ?? "?"}ms) ${pair.b?.ok ? "ok" : "ERR"}` + (pair.b?.error ? ` · ${pair.b.error.slice(0,120)}` : ""), pair.b?.ok ? "dim" : "err"));
        push(L.text(`  ⇣ pair-quorum: ${pair.agree ? "AGREE" : "DISAGREE"}`, pair.agree ? "ok" : "warn"));
        const reply = pickPairText(pair);
        if (!reply) { push(L.text("  pair returned no usable completion", "err")); return 1; }
        const m = reply.match(/\{[\s\S]*\}/);
        if (!m) { push(L.text("  harness returned no parseable plan", "err")); push(L.text("    " + reply.slice(0,200), "dim")); return 1; }
        const plan = JSON.parse(m[0]);
        push(L.text(`  ↳ plan · ${plan.cmd} ${plan.op} → [${(plan.tongues||[]).join(",")}]   ${plan.reason||""}`, "ok"));
        if (plan.cmd === "seal") {
          const payload = plan.args?.payload || prompt;
          const tongue = (plan.tongues?.[0] || "KO").toUpperCase();
          const code = `seal(${JSON.stringify(payload)})`;
          const cost = G.phiWallCost(0.55, tongue);
          const tier = G.phiWallTier(cost);
          const trust = G.phiTrustScore(cost);
          const seal = G.computeSeal("seal", tongue, code, payload, cost, tier);
          push(L.seal({ payload, tongue, op:"seal", code, seal, cost, tier, trust, phase: G.TONGUE_BY_CODE[tongue].phase }));
          return 0;
        }
        const op = G.LEXICON_BY_NAME[plan.op];
        if (!op) { push(L.text(`  harness chose unknown op: ${plan.op}`, "err")); return 1; }
        const argVals = op.args.map(a => String(plan.args?.[a] ?? "0"));
        const tongues = (plan.tongues && plan.tongues.length) ? plan.tongues.map(t=>t.toUpperCase()) : ["KO","AV","RU"];
        await swarmDispatch(op, tongues, argVals, plan.cmd !== "emit");
        return 0;
      } catch (e) {
        push(L.text(`  harness error: ${e.message || e}`, "err"));
        return 1;
      }
    }
  },

  explain: {
    summary: "AI explains the most recent ledger entry",
    run: async ({ push, harness, lastLedger }) => {
      if (!harness?.enabled) { push(L.text("  AI harness is OFFLINE — toggle in Tweaks", "warn")); return 1; }
      if (!lastLedger) { push(L.text("  no ledger entries yet — run a swarm first", "warn")); return 1; }
      push(L.text(`  ⟳ harness · explaining ${lastLedger.op} · ${lastLedger.tongues.join(",")}`, "dim"));
      try {
        const userPrompt =
          `Explain this GeoSeal swarm result in 2-3 short sentences. Mention quorum, tier, and any tongue that disagreed.\n\n` +
          JSON.stringify({ op: lastLedger.op, tongues: lastLedger.tongues, tier: lastLedger.tier,
            quorum_ok: lastLedger.quorum_ok,
            outputs: lastLedger.calls.map(c=>({tongue:c.tongue, stdout:c.stdout, error:c.error, tier:c.tier}))
          });
        const pair = await harnessPairCall(harness, userPrompt, "You are a paired coding agent in the GeoSeal Console. Be concise.");
        const aTag = (harness?.modelA || "A").split("/").pop();
        const bTag = (harness?.modelB || "B").split("/").pop();
        if (pair.a?.ok) push(L.text(`  ${aTag}: ${pair.a.text.trim()}`, "ok"));
        else push(L.text(`  ${aTag}: ERR · ${(pair.a?.error||"no text").slice(0,160)}`, "err"));
        if (pair.b?.ok) push(L.text(`  ${bTag}: ${pair.b.text.trim()}`, "ok"));
        else push(L.text(`  ${bTag}: ERR · ${(pair.b?.error||"no text").slice(0,160)}`, "err"));
        push(L.text(`  pair-quorum: ${pair.agree ? "AGREE" : "DISAGREE"}`, pair.agree ? "ok" : "warn"));
        return pair.both_ok ? 0 : 1;
      } catch (e) { push(L.text(`  harness error: ${e.message||e}`, "err")); return 1; }
    }
  },

  agent: {
    summary: "tokenize + dispatch a task (rule-based)",
    run: async ({ args, push, swarmDispatch }) => {
      const task = args.positional.join(" ");
      if (!task) { push(L.text("usage: agent <task...>","err")); return 1; }
      push(L.text(`  ⟳ atomic-tokenize: "${task}"`, "dim"));
      // crude task-to-op classifier for the demo
      const lower = task.toLowerCase();
      let op = G.LEXICON_BY_NAME.add;
      if (lower.match(/divide|ratio|over/))      op = G.LEXICON_BY_NAME.div;
      else if (lower.match(/multiply|product/))  op = G.LEXICON_BY_NAME.mul;
      else if (lower.match(/hash|digest/))       op = G.LEXICON_BY_NAME.sha256;
      else if (lower.match(/seal|stamp/))        op = G.LEXICON_BY_NAME.seal;
      else if (lower.match(/spiral|harmoniz/))   op = G.LEXICON_BY_NAME.spiral;
      else if (lower.match(/print|output|emit/)) op = G.LEXICON_BY_NAME.print;
      push(L.text(`  ↳ routed → ${op.name}  (band ${op.band}, χ=${op.chi.toFixed(2)})`, "ok"));
      const argVals = op.args.map(a => "$"+a);
      await swarmDispatch(op, ["KO","AV","UM"], argVals, /*execute*/false);
      return 0;
    }
  },

  clear: {
    summary: "clear scrollback",
    run: ({ setLines }) => { setLines([L.banner()]); return 0; }
  },
};

// merge in extra commands defined in extra-commands.jsx
if (window.ExtraCommands) {
  Object.assign(COMMANDS, window.ExtraCommands);
}

// ---- REPL component ----
function REPL({ onSwarm, onSeal, history, setHistory, setActiveTongues, setBusy, setResults, registerLedger, harness, lastLedger, ledger }) {
  const [lines, setLines] = useState([L.banner()]);
  const [input, setInput] = useState("");
  const [hidx, setHidx] = useState(-1);
  const [running, setRunning] = useState(false);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const push = useCallback((line) => setLines(ls => [...ls, line]), []);

  const swarmDispatch = useCallback(async (op, tongues, argVals, execute) => {
    setActiveTongues(tongues);
    push(L.text(`  ⟳ dispatch → ${op.name}(${argVals.join(", ")}) ⇢ [${tongues.join(", ")}]`, "dim"));

    const calls = [];
    for (const t of tongues) {
      setBusy(b => ({...b, [t]: true}));
      const tongueData = G.TONGUE_BY_CODE[t];
      const code = op.emit[t](...argVals);
      const cost = G.phiWallCost(op.chi, t);
      const tier = G.phiWallTier(cost);
      const trust = G.phiTrustScore(cost);
      const seal = G.computeSeal(op.name, t, code, "", cost, tier);
      // simulate execution
      let stdout = "", error = null, ok = false;
      if (execute && tier !== "DENY") {
        // crude eval for arithmetic ops to simulate consensus
        try {
          if (op.band === "ARITH" && argVals.every(v => !isNaN(Number(v)))) {
            const a = Number(argVals[0]), b = Number(argVals[1]);
            const result = ({add:a+b, sub:a-b, mul:a*b, div:b!==0?a/b:NaN, mod:a%b, pow:a**b})[op.name];
            stdout = String(result);
            ok = true;
          } else if (op.name === "print") {
            stdout = argVals[0];
            ok = true;
          } else if (op.band === "COMPARE") {
            const a = Number(argVals[0]), b = Number(argVals[1]);
            stdout = String(({eq:a===b,lt:a<b,gt:a>b})[op.name]);
            ok = true;
          } else if (op.band === "LOGIC") {
            stdout = "<bool>";
            ok = true;
          } else {
            stdout = `<${op.name}-result>`;
            ok = true;
          }
        } catch (e) { error = String(e); }
      } else if (tier === "DENY") {
        error = "DENIED by φ-wall";
      }
      // small async stagger for animation
      await new Promise(r => setTimeout(r, 220 + Math.random()*180));
      calls.push({ tongue: t, lang: tongueData.lang, code, cost, tier, trust, seal,
                   stdout, error, ok, color: tongueData.color, phase: tongueData.phase,
                   duration_ms: 80 + Math.random()*340 });
      setBusy(b => ({...b, [t]: false}));
      setResults(r => ({...r, [t]: {ok, error, stdout}}));
    }
    // consensus
    const successful = calls.filter(c => c.ok && c.stdout);
    const tally = {};
    successful.forEach(c => { tally[c.stdout] = (tally[c.stdout]||0)+1; });
    let quorum_ok = false, consensus_hash = "", consensus_value = "";
    if (successful.length > 0) {
      const [top, count] = Object.entries(tally).sort((a,b)=>b[1]-a[1])[0];
      if (count * 2 > successful.length) {
        quorum_ok = true;
        consensus_hash = G.fnv1aHex(top).slice(0,16);
        consensus_value = top;
      }
    }
    push(L.swarm({ op, argVals, calls, quorum_ok, consensus_hash, consensus_value }));

    // append to ledger
    const ledgerEntry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2,7)}`,
      time: new Date().toLocaleTimeString("en-GB", {hour12:false}),
      op: op.name,
      tongue: tongues[0],
      tongues,
      tier: calls[0]?.tier || "ALLOW",
      seal: calls[0]?.seal || "",
      quorum_ok,
      consensus_hash,
      calls,
      args: argVals,
    };
    registerLedger(ledgerEntry);

    // reset after a beat
    setTimeout(() => {
      setActiveTongues([]);
      setResults({});
    }, 2500);
  }, [push, setActiveTongues, setBusy, setResults, registerLedger]);

  // runLine is the same as submit but reusable from inside other commands (e.g. `shell`)
  const runLineRef = useRef(null);

  const submit = useCallback(async (raw) => {
    const text = raw.trim();
    if (!text) return;
    push(L.prompt(text));
    setHistory(h => [...h, text]);
    setHidx(-1);
    const parsed = parseCommand(text);
    if (!parsed) { return; }
    const cmd = COMMANDS[parsed.cmd];
    if (!cmd) {
      push(L.text(`unknown command: ${parsed.cmd}  · type 'help'`, "err"));
      return;
    }
    setRunning(true);
    try {
      await cmd.run({
        args: parsed, push, setLines,
        swarmDispatch, harness, lastLedger, ledger,
        runLine: runLineRef.current,
      });
    } catch (e) {
      push(L.text(`error: ${e.message || e}`, "err"));
    } finally {
      setRunning(false);
    }
  }, [push, setHistory, swarmDispatch, harness, lastLedger, ledger]);

  // keep ref updated for nested-shell calls
  useEffect(() => { runLineRef.current = submit; }, [submit]);

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      const v = input;
      setInput("");
      submit(v);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (history.length === 0) return;
      const next = hidx < 0 ? history.length - 1 : Math.max(0, hidx - 1);
      setHidx(next);
      setInput(history[next]);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (hidx < 0) return;
      const next = hidx + 1;
      if (next >= history.length) { setHidx(-1); setInput(""); }
      else { setHidx(next); setInput(history[next]); }
    } else if (e.key === "Tab") {
      e.preventDefault();
      const head = input.trim().split(/\s+/)[0] || "";
      const cmds = Object.keys(COMMANDS);
      const matches = cmds.filter(c => c.startsWith(head));
      if (matches.length === 1) setInput(matches[0] + " ");
      else if (matches.length > 1) push(L.text("  " + matches.join("  "), "dim"));
    } else if (e.key === "l" && e.ctrlKey) {
      e.preventDefault();
      setLines([L.banner()]);
    }
  };

  return (
    <div className="repl">
      <div className="repl-scroll" ref={scrollRef}>
        {lines.map((ln, i) => <RenderLine key={i} ln={ln} />)}
        <div className="prompt-row live">
          <span className="prompt-sigil">geoseal ❯</span>
          <input
            ref={inputRef}
            className="prompt-input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={onKey}
            spellCheck={false}
            autoComplete="off"
            placeholder={running ? "…" : "type a command — try 'help' or 'swarm add --a 7 --b 3'"}
            disabled={running}
          />
          <span className="prompt-cursor">{running ? "⟳" : "▍"}</span>
        </div>
      </div>
    </div>
  );
}

// ---- line renderer ----
function RenderLine({ ln }) {
  // delegate extra line kinds to extra-commands renderer
  if (window.ExtraRenderLine) {
    const extraKinds = new Set(["art","block","tokens","atomic","history","scaffold","workflow","egg","manifest"]);
    if (extraKinds.has(ln.kind)) return window.ExtraRenderLine({ ln });
  }
  if (ln.kind === "banner") return <Banner/>;
  if (ln.kind === "prompt") return (
    <div className="prompt-row">
      <span className="prompt-sigil">geoseal ❯</span>
      <span className="prompt-echo">{ln.text}</span>
    </div>
  );
  if (ln.kind === "rule")  return <div className="rule"/>;
  if (ln.kind === "text")  return <div className={`out tone-${ln.tone}`}>{ln.text}</div>;
  if (ln.kind === "tongue-row") {
    const t = ln.t;
    return (
      <div className="out tongue-row">
        <span className="dim">│ </span>
        <span style={{color:t.color, fontWeight:600}}>{t.code.padEnd(4)}</span>
        <span className="dim">│ </span>
        <span>{t.name.padEnd(14)}</span>
        <span className="dim">│ </span>
        <span>{t.lang.padEnd(13)}</span>
        <span className="dim">│ </span>
        <span>φ^{Math.log(t.phi)/Math.log(G.PHI)|0 + (Math.log(t.phi)/Math.log(G.PHI)).toFixed(2).slice(-3) }</span>
        <span className="dim"> │ </span>
        <span>{ln.phaseDeg}°</span>
        <span className="dim">    │</span>
      </div>
    );
  }
  if (ln.kind === "op-row") {
    const e = ln.op;
    return (
      <div className="out op-row">
        <span className="dim">  </span>
        <span className="op-id">0x{e.id.toString(16).padStart(2,"0").toUpperCase()}</span>
        <span className="op-name">{e.name.padEnd(14)}</span>
        <span className={`op-band band-${e.band}`}>{e.band.padEnd(10)}</span>
        <span className="op-chi">χ={e.chi.toFixed(2)}</span>
        <span className="dim"> ({e.args.join(", ")})</span>
      </div>
    );
  }
  if (ln.kind === "help") {
    return (
      <div className="help-block">
        <div className="help-title">{ln.data.title}</div>
        <div className="help-grid">
          {ln.data.rows.map(([cmd, sum, usage]) => (
            <React.Fragment key={cmd}>
              <span className="help-cmd">{cmd}</span>
              <span className="help-sum">{sum}</span>
              <span className="help-usage">{usage}</span>
            </React.Fragment>
          ))}
        </div>
      </div>
    );
  }
  if (ln.kind === "emit") {
    const { op, emits, args } = ln.data;
    return (
      <div className="emit-block">
        <div className="emit-head">
          <span className="emit-op">{op.name}</span>
          <span className="emit-args">({args.join(", ")})</span>
          <span className="emit-meta">band {op.band} · χ={op.chi.toFixed(2)}</span>
        </div>
        <div className="emit-grid">
          {emits.map(({tongue, code}) => (
            <div className="emit-row" key={tongue.code}>
              <div className="emit-tongue" style={{color: tongue.color, borderColor: tongue.color}}>
                <span className="et-code">{tongue.code}</span>
                <span className="et-lang">{tongue.lang}</span>
              </div>
              <div className="emit-code">{code}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }
  if (ln.kind === "swarm") {
    const { op, calls, quorum_ok, consensus_hash, consensus_value, argVals } = ln.data;
    return (
      <div className="swarm-block">
        <div className="swarm-head">
          <span className="swarm-tag">SWARM</span>
          <span className="swarm-op">{op.name}({argVals.join(", ")})</span>
          <span className={`swarm-quorum ${quorum_ok ? "ok":"no"}`}>
            {quorum_ok ? `✓ quorum · consensus ${consensus_value}` : "— no quorum —"}
          </span>
        </div>
        <div className="swarm-grid">
          {calls.map(c => (
            <div key={c.tongue} className={`swarm-call tier-${c.tier}`}>
              <div className="sc-head">
                <span className="sc-code" style={{color:c.color}}>{c.tongue}</span>
                <span className="sc-lang">{c.lang}</span>
                <span className={`sc-tier tier-${c.tier}`}>{c.tier}</span>
              </div>
              <div className="sc-emit">{c.code}</div>
              <div className="sc-foot">
                <span className="sc-out">
                  {c.error
                    ? <span className="sc-err">✕ {c.error}</span>
                    : <span className="sc-ok">→ {c.stdout}</span>}
                </span>
                <span className="sc-cost">φ={c.cost.toFixed(3)}</span>
                <span className="sc-dur">{c.duration_ms.toFixed(0)}ms</span>
              </div>
              <div className="sc-seal">⌬ {c.seal.slice(0,40)}…</div>
            </div>
          ))}
        </div>
        {quorum_ok && (
          <div className="swarm-consensus">
            <span className="dim">→ ledger ← </span>
            <span className="mono">consensus_hash {consensus_hash}…</span>
          </div>
        )}
      </div>
    );
  }
  if (ln.kind === "seal") {
    const d = ln.data;
    return (
      <div className="seal-block">
        <div className="seal-head">
          <span className="seal-tag">SEAL</span>
          <span className="seal-payload">"{d.payload}"</span>
          <span className={`seal-tier tier-${d.tier}`}>{d.tier}</span>
        </div>
        <div className="seal-grid">
          <div><span className="sk">tongue</span><span className="sv">{d.tongue}</span></div>
          <div><span className="sk">phase</span><span className="sv">{(d.phase*180/Math.PI).toFixed(1)}°</span></div>
          <div><span className="sk">φ-cost</span><span className="sv">{d.cost.toFixed(4)}</span></div>
          <div><span className="sk">trust</span><span className="sv">{(d.trust*100).toFixed(1)}%</span></div>
        </div>
        <div className="seal-hash">⌬ {d.seal}</div>
      </div>
    );
  }
  return null;
}

function Banner() {
  return (
    <div className="banner">
      <pre className="banner-art">{
`   ▄████  ███████  ██████  ███████ ███████  █████  ██
  ██      ██      ██    ██ ██      ██      ██   ██ ██
  ██  ███ █████   ██    ██ ███████ █████   ███████ ██
  ██   ██ ██      ██    ██      ██ ██      ██   ██ ██
   ██████ ███████  ██████  ███████ ███████ ██   ██ ███████`
      }</pre>
      <div className="banner-sub">
        swarm dispatcher · 6 sacred tongues · φ-wall governance · v0.6.4
      </div>
      <div className="banner-hint">
        type <span className="kbd">help</span> · arrow keys for history · <span className="kbd">tab</span> to complete
      </div>
    </div>
  );
}

window.REPL = REPL;
window.parseCommand = parseCommand;
