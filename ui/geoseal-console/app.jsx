// Main app — composes REPL, panels, status bar, tweaks panel.

const { useState, useEffect, useCallback, useMemo } = React;

const LEDGER_STORAGE_KEY = "geoseal.ledger.v1";

function loadLedgerFromStorage() {
  try {
    const raw = window.localStorage.getItem(LEDGER_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function exportLedgerJSONL(entries) {
  const lines = entries.map(e => JSON.stringify(e)).join("\n") + (entries.length ? "\n" : "");
  const blob = new Blob([lines], { type: "application/x-ndjson" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  a.href = url;
  a.download = `geoseal_calls_${stamp}.jsonl`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "accent": "amber",
  "density": "comfortable",
  "rosetteSize": 260,
  "scanlines": true,
  "phiWallStrictness": 1.0,
  "autoCommandDemo": false,
  "harnessEnabled": true,
  "harnessModel": "hf-pair",
  "harnessModelA": "scbe-geoseal-coder:q8",
  "harnessModelB": "smollm2:135m",
  "harnessBridgeUrl": "http://127.0.0.1:8766",
  "harnessMaxTokens": 1024,
  "harnessTemperature": 0.2,
  "harnessAutoSeal": true,
  "harnessSafety": "phi-wall"
}/*EDITMODE-END*/;

function App() {
  const [tweaks, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [activeTongues, setActiveTongues] = useState([]);
  const [busy, setBusy] = useState({});
  const [results, setResults] = useState({});
  const [history, setHistory] = useState([]);
  const [ledger, setLedger] = useState(loadLedgerFromStorage);
  const [selectedLedgerId, setSelectedLedgerId] = useState(null);

  useEffect(() => {
    try {
      window.localStorage.setItem(LEDGER_STORAGE_KEY, JSON.stringify(ledger));
    } catch {
      // quota or private-mode; persistence becomes session-only
    }
  }, [ledger]);

  const onExportLedger = useCallback(() => exportLedgerJSONL(ledger), [ledger]);
  const onClearLedger = useCallback(() => {
    if (window.confirm(`Clear ${ledger.length} ledger entries? Export first if you want to keep them.`)) {
      setLedger([]);
      setSelectedLedgerId(null);
    }
  }, [ledger.length]);
  const [harnessBusy, setHarnessBusy] = useState(false);
  const [harnessLog, setHarnessLog] = useState([]);

  const harness = useMemo(() => ({
    enabled: tweaks.harnessEnabled,
    model: tweaks.harnessModel,
    modelA: tweaks.harnessModelA,
    modelB: tweaks.harnessModelB,
    bridgeUrl: tweaks.harnessBridgeUrl,
    maxTokens: tweaks.harnessMaxTokens,
    temperature: tweaks.harnessTemperature,
    autoSeal: tweaks.harnessAutoSeal,
    safety: tweaks.harnessSafety,
  }), [
    tweaks.harnessEnabled, tweaks.harnessModel, tweaks.harnessModelA, tweaks.harnessModelB,
    tweaks.harnessBridgeUrl, tweaks.harnessMaxTokens,
    tweaks.harnessTemperature, tweaks.harnessAutoSeal, tweaks.harnessSafety,
  ]);

  const lastLedger = ledger[0] || null;

  // current φ-wall reading reflects either the active dispatch or the most recent ledger entry
  const currentPhi = useMemo(() => {
    if (selectedLedgerId) {
      const e = ledger.find(x => x.id === selectedLedgerId);
      if (e?.calls?.length) {
        const c = e.calls.reduce((m,c) => c.cost > m.cost ? c : m, e.calls[0]);
        return { cost: c.cost, tier: c.tier, trust: c.trust };
      }
    }
    if (activeTongues.length > 0) {
      const costs = activeTongues.map(t => 0.55 * (window.GeoSeal.TONGUE_BY_CODE[t]?.phi ?? 1) / 11.090);
      const peak = Math.max(...costs.map(d => (window.GeoSeal.PHI ** d) / (1 + Math.exp(-5))));
      return { cost: peak, tier: window.GeoSeal.phiWallTier(peak), trust: window.GeoSeal.phiTrustScore(peak) };
    }
    return { cost: 1.0, tier: "ALLOW", trust: 1.0 };
  }, [selectedLedgerId, ledger, activeTongues]);

  const registerLedger = useCallback((entry) => {
    setLedger(l => [entry, ...l].slice(0, 50));
  }, []);

  return (
    <div className={`app density-${tweaks.density} accent-${tweaks.accent} ${tweaks.scanlines?"scanlines":""}`}>
      <TitleBar tweaks={tweaks}/>
      <div className="main-grid">
        <window.REPL
          history={history} setHistory={setHistory}
          setActiveTongues={setActiveTongues}
          setBusy={setBusy}
          setResults={setResults}
          registerLedger={registerLedger}
          harness={harness}
          lastLedger={lastLedger}
          ledger={ledger}
        />
        <aside className="rail">
          <section className="rail-card">
            <HarnessPanel harness={harness} setTweak={setTweak} busy={harnessBusy}/>
          </section>
          <section className="rail-card">
            <div className="panel-head">
              <span className="panel-tag">SWARM · φ-ROSETTE</span>
              <span className="panel-meta">{activeTongues.length>0 ? "dispatching…" : "idle"}</span>
            </div>
            <window.PhiRosette
              activeTongues={activeTongues}
              busy={busy}
              results={results}
              size={tweaks.rosetteSize}/>
          </section>
          <section className="rail-card">
            <window.PhiWallGauge {...currentPhi}/>
          </section>
          <section className="rail-card flex-grow">
            <window.SealLedger entries={ledger}
              onSelect={setSelectedLedgerId}
              selectedId={selectedLedgerId}
              onExport={onExportLedger}
              onClear={onClearLedger}/>
          </section>
        </aside>
      </div>
      <StatusBar phi={currentPhi} ledgerCount={ledger.length} active={activeTongues}/>
      <Tweaks tweaks={tweaks} setTweak={setTweak}/>
    </div>
  );
}

function TitleBar({ tweaks }) {
  return (
    <header className="title-bar">
      <div className="tb-left">
        <div className="tb-glyph">
          <svg width="22" height="22" viewBox="0 0 22 22">
            <circle cx="11" cy="11" r="8" fill="none" stroke="currentColor" strokeWidth="1"/>
            <circle cx="11" cy="11" r="4" fill="none" stroke="currentColor" strokeWidth="1"/>
            <line x1="11" y1="3" x2="11" y2="19" stroke="currentColor" strokeWidth="0.6"/>
            <line x1="3" y1="11" x2="19" y2="11" stroke="currentColor" strokeWidth="0.6"/>
            <circle cx="11" cy="11" r="1.2" fill="currentColor"/>
          </svg>
        </div>
        <div className="tb-name">geoseal</div>
        <div className="tb-sep">·</div>
        <div className="tb-sub">swarm console</div>
      </div>
      <div className="tb-mid">
        <span className="tb-pill">~/scbe-aethermoore</span>
        <span className="tb-pill">.scbe/geoseal_calls.jsonl</span>
        <span className="tb-pill">tongues: 6</span>
        <span className="tb-pill">lexicon: 64 ops</span>
      </div>
      <div className="tb-right">
        <span className="tb-dot ok"/> sacred-tokenizer up
      </div>
    </header>
  );
}

function StatusBar({ phi, ledgerCount, active }) {
  const tierColor = {
    ALLOW: "oklch(0.72 0.13 155)",
    QUARANTINE: "oklch(0.78 0.14 75)",
    ESCALATE: "oklch(0.70 0.16 45)",
    DENY: "oklch(0.64 0.18 25)",
  }[phi.tier];
  return (
    <footer className="status-bar">
      <span className="sb-cell"><span className="sb-k">tier</span>
        <span className="sb-v" style={{color:tierColor}}>{phi.tier}</span>
      </span>
      <span className="sb-cell"><span className="sb-k">φ-cost</span><span className="sb-v">{phi.cost.toFixed(4)}</span></span>
      <span className="sb-cell"><span className="sb-k">trust</span><span className="sb-v">{(phi.trust*100).toFixed(1)}%</span></span>
      <span className="sb-cell"><span className="sb-k">active</span><span className="sb-v">{active.join(",") || "—"}</span></span>
      <span className="sb-cell"><span className="sb-k">ledger</span><span className="sb-v">{ledgerCount} rec</span></span>
      <span className="sb-spacer"/>
      <span className="sb-cell sb-cell-r"><span className="sb-k">^L</span><span className="sb-v">clear</span></span>
      <span className="sb-cell sb-cell-r"><span className="sb-k">↑↓</span><span className="sb-v">history</span></span>
      <span className="sb-cell sb-cell-r"><span className="sb-k">tab</span><span className="sb-v">complete</span></span>
    </footer>
  );
}

function Tweaks({ tweaks, setTweak }) {
  return (
    <TweaksPanel title="Tweaks">
      <TweakSection title="Theme">
        <TweakRadio
          label="Accent"
          value={tweaks.accent}
          onChange={v => setTweak("accent", v)}
          options={[
            {value:"amber", label:"Amber"},
            {value:"sage",  label:"Sage"},
            {value:"mauve", label:"Mauve"},
          ]}/>
        <TweakRadio
          label="Density"
          value={tweaks.density}
          onChange={v => setTweak("density", v)}
          options={[
            {value:"compact",     label:"Compact"},
            {value:"comfortable", label:"Comfortable"},
          ]}/>
        <TweakToggle
          label="CRT scanlines"
          value={tweaks.scanlines}
          onChange={v => setTweak("scanlines", v)}/>
      </TweakSection>
      <TweakSection title="Visualizer">
        <TweakSlider
          label="Rosette size"
          value={tweaks.rosetteSize}
          min={180} max={360} step={10}
          onChange={v => setTweak("rosetteSize", v)}/>
      </TweakSection>
      <TweakSection title="Governance">
        <TweakSlider
          label="φ-wall strictness"
          value={tweaks.phiWallStrictness}
          min={0.5} max={1.5} step={0.05}
          onChange={v => setTweak("phiWallStrictness", v)}/>
      </TweakSection>
      <TweakSection title="AI Harness">
        <TweakToggle
          label="Enable harness"
          value={tweaks.harnessEnabled}
          onChange={v => setTweak("harnessEnabled", v)}/>
        <TweakSelect
          label="Mode"
          value={tweaks.harnessModel}
          onChange={v => setTweak("harnessModel", v)}
          options={[
            {value:"hf-pair", label:"Local Paired Coders"},
            {value:"claude-haiku-4-5", label:"Claude Haiku 4.5"},
            {value:"claude-sonnet-4-6", label:"Claude Sonnet 4.6"},
            {value:"local-tongue-router", label:"Local Tongue Router"},
          ]}/>
        <TweakText
          label="Model A"
          value={tweaks.harnessModelA}
          onChange={v => setTweak("harnessModelA", v)}
          placeholder="org/model-a"/>
        <TweakText
          label="Model B"
          value={tweaks.harnessModelB}
          onChange={v => setTweak("harnessModelB", v)}
          placeholder="org/model-b"/>
        <TweakText
          label="Bridge URL"
          value={tweaks.harnessBridgeUrl}
          onChange={v => setTweak("harnessBridgeUrl", v)}
          placeholder="http://127.0.0.1:8765"/>
        <TweakSlider
          label="Max tokens"
          value={tweaks.harnessMaxTokens}
          min={128} max={4096} step={64}
          onChange={v => setTweak("harnessMaxTokens", v)}/>
        <TweakSlider
          label="Temperature"
          value={tweaks.harnessTemperature}
          min={0} max={1} step={0.05}
          onChange={v => setTweak("harnessTemperature", v)}/>
        <TweakRadio
          label="Safety"
          value={tweaks.harnessSafety}
          onChange={v => setTweak("harnessSafety", v)}
          options={[
            {value:"off",      label:"Off"},
            {value:"phi-wall", label:"φ-wall"},
            {value:"strict",   label:"Strict"},
          ]}/>
        <TweakToggle
          label="Auto-seal AI dispatches"
          value={tweaks.harnessAutoSeal}
          onChange={v => setTweak("harnessAutoSeal", v)}/>
        <TweakButton onClick={() => {
          const input = document.querySelector(".prompt-input");
          if (input) {
            input.focus();
            input.value = "ask divide 22 by 7 across three tongues and tell me which agree";
            input.dispatchEvent(new Event("input", {bubbles:true}));
          }
        }}>Demo: ask the harness</TweakButton>
      </TweakSection>
      <TweakSection title="Try it">
        <TweakButton onClick={() => {
          const input = document.querySelector(".prompt-input");
          if (input) {
            input.focus();
            input.value = "swarm add --a 7 --b 3 --tongues KO,AV,RU,CA,UM,DR";
            input.dispatchEvent(new Event("input", {bubbles:true}));
          }
        }}>Demo: swarm add</TweakButton>
        <TweakButton onClick={() => {
          const input = document.querySelector(".prompt-input");
          if (input) {
            input.focus();
            input.value = "seal aethermoore-genesis-block --tongue DR";
            input.dispatchEvent(new Event("input", {bubbles:true}));
          }
        }}>Demo: high-φ seal</TweakButton>
      </TweakSection>
    </TweaksPanel>
  );
}

function HarnessPanel({ harness, setTweak, busy }) {
  const dotColor = harness.enabled ? "oklch(0.72 0.13 155)" : "oklch(0.50 0.014 70)";
  return (
    <div>
      <div className="panel-head">
        <span className="panel-tag">AI HARNESS</span>
        <span className="panel-meta" style={{color: dotColor}}>
          ● {harness.enabled ? (busy ? "thinking…" : "online") : "offline"}
        </span>
      </div>
      <div className="harness-grid">
        <div className="hg-row">
          <span className="hg-k">mode</span>
          <select className="hg-select" value={harness.model}
            onChange={e => setTweak("harnessModel", e.target.value)}>
            <option value="hf-pair">hf-pair (paired coders)</option>
            <option value="claude-haiku-4-5">claude-haiku-4-5</option>
            <option value="claude-sonnet-4-6">claude-sonnet-4-6</option>
            <option value="local-tongue-router">local-tongue-router</option>
          </select>
        </div>
        {harness.model === "hf-pair" && (
          <>
            <div className="hg-row">
              <span className="hg-k">A</span>
              <span className="hg-v" title={harness.modelA}
                style={{fontFamily:"'IBM Plex Mono',monospace",fontSize:"10px",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                {harness.modelA?.split("/").pop() || "—"}
              </span>
            </div>
            <div className="hg-row">
              <span className="hg-k">B</span>
              <span className="hg-v" title={harness.modelB}
                style={{fontFamily:"'IBM Plex Mono',monospace",fontSize:"10px",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                {harness.modelB?.split("/").pop() || "—"}
              </span>
            </div>
          </>
        )}
        <div className="hg-row">
          <span className="hg-k">temp</span>
          <input type="range" min="0" max="1" step="0.05"
            value={harness.temperature}
            onChange={e => setTweak("harnessTemperature", parseFloat(e.target.value))}/>
          <span className="hg-v">{harness.temperature.toFixed(2)}</span>
        </div>
        <div className="hg-row">
          <span className="hg-k">safety</span>
          <div className="hg-segs">
            {["off","phi-wall","strict"].map(s => (
              <button key={s}
                className={`hg-seg ${harness.safety===s?"on":""}`}
                onClick={() => setTweak("harnessSafety", s)}>{s}</button>
            ))}
          </div>
        </div>
        <div className="hg-row">
          <span className="hg-k">auto-seal</span>
          <button
            className={`hg-toggle ${harness.autoSeal?"on":""}`}
            onClick={() => setTweak("harnessAutoSeal", !harness.autoSeal)}>
            {harness.autoSeal ? "ON" : "OFF"}
          </button>
        </div>
        <div className="hg-row">
          <span className="hg-k">power</span>
          <button
            className={`hg-toggle big ${harness.enabled?"on":""}`}
            onClick={() => setTweak("harnessEnabled", !harness.enabled)}>
            {harness.enabled ? "● ENABLED" : "○ DISABLED"}
          </button>
        </div>
      </div>
      <div className="harness-hint">
        try: <span className="kbd">ask divide 22 by 7 in three tongues</span>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
