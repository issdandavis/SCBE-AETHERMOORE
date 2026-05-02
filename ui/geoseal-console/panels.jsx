// Right-rail panels: phi-rosette swarm visualizer, phi-wall gauge, seal ledger.

const { useEffect: _pUseEffect, useRef: _pUseRef, useState: _pUseState, useMemo: _pUseMemo } = React;

const _PHI = window.GeoSeal.PHI;
const _TONGUES = window.GeoSeal.TONGUES;

// ---- φ-Rosette: 6-petal swarm visualizer ----
function PhiRosette({ activeTongues = [], busy = {}, results = {} , size = 260 }) {
  const cx = size / 2;
  const cy = size / 2;
  const R  = size * 0.36;

  return (
    <div className="rosette-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <defs>
          <radialGradient id="rosetteCore" cx="50%" cy="50%" r="50%">
            <stop offset="0%"  stopColor="oklch(0.32 0.02 70)" />
            <stop offset="100%" stopColor="oklch(0.18 0.008 60)" />
          </radialGradient>
        </defs>

        {/* phi spiral guide */}
        <g opacity="0.18">
          {[0,1,2,3,4,5,6].map(i => {
            const r = R * 0.18 * (_PHI ** (i*0.35));
            return <circle key={i} cx={cx} cy={cy} r={r} fill="none" stroke="oklch(0.6 0.02 70)" strokeWidth="0.5" />;
          })}
        </g>

        {/* connecting lines between active tongues */}
        {activeTongues.length > 1 && activeTongues.map((tA, i) =>
          activeTongues.slice(i+1).map((tB, j) => {
            const a = _TONGUES.find(t => t.code === tA);
            const b = _TONGUES.find(t => t.code === tB);
            if (!a || !b) return null;
            const x1 = cx + R * Math.cos(a.phase - Math.PI/2);
            const y1 = cy + R * Math.sin(a.phase - Math.PI/2);
            const x2 = cx + R * Math.cos(b.phase - Math.PI/2);
            const y2 = cy + R * Math.sin(b.phase - Math.PI/2);
            return <line key={`${tA}-${tB}`} x1={x1} y1={y1} x2={x2} y2={y2}
              stroke="oklch(0.78 0.14 75)" strokeWidth="0.6" opacity="0.4" />;
          })
        )}

        {/* core */}
        <circle cx={cx} cy={cy} r={R * 0.28} fill="url(#rosetteCore)"
          stroke="oklch(0.5 0.02 70)" strokeWidth="0.5" />
        <text x={cx} y={cy - 2} textAnchor="middle" fontSize="9" fill="oklch(0.7 0.02 70)"
              fontFamily="'IBM Plex Mono',monospace" letterSpacing="1.5">SWARM</text>
        <text x={cx} y={cy + 9} textAnchor="middle" fontSize="7" fill="oklch(0.55 0.02 70)"
              fontFamily="'IBM Plex Mono',monospace" letterSpacing="1">{activeTongues.length}/6</text>

        {/* petals */}
        {_TONGUES.map(t => {
          const x = cx + R * Math.cos(t.phase - Math.PI/2);
          const y = cy + R * Math.sin(t.phase - Math.PI/2);
          const isActive = activeTongues.includes(t.code);
          const isBusy   = !!busy[t.code];
          const result   = results[t.code];
          const petalR   = isActive ? 16 : 12;
          let stroke = "oklch(0.4 0.02 70)";
          let fill   = "oklch(0.22 0.008 60)";
          if (isActive) { stroke = t.color; fill = "oklch(0.26 0.04 70)"; }
          if (result?.ok)    { stroke = "oklch(0.72 0.13 155)"; fill = "oklch(0.32 0.06 155)"; }
          if (result?.error) { stroke = "oklch(0.66 0.16 25)";  fill = "oklch(0.30 0.08 25)";  }

          return (
            <g key={t.code}>
              {/* spoke */}
              <line x1={cx} y1={cy} x2={x} y2={y}
                stroke={isActive ? t.color : "oklch(0.32 0.01 70)"}
                strokeWidth={isActive ? "1" : "0.5"}
                opacity={isActive ? 0.6 : 0.3}
                strokeDasharray={isBusy ? "2 2" : "none"}>
                {isBusy && <animate attributeName="stroke-dashoffset" from="0" to="8" dur="0.6s" repeatCount="indefinite"/>}
              </line>
              {/* petal */}
              <circle cx={x} cy={y} r={petalR} fill={fill} stroke={stroke} strokeWidth="1.2">
                {isBusy && <animate attributeName="r" values={`${petalR};${petalR+3};${petalR}`} dur="1s" repeatCount="indefinite"/>}
              </circle>
              <text x={x} y={y+3} textAnchor="middle" fontSize="9"
                    fill={isActive ? t.color : "oklch(0.55 0.02 70)"}
                    fontFamily="'IBM Plex Mono',monospace" fontWeight="600">{t.code}</text>
              <text x={x} y={y+petalR+10} textAnchor="middle" fontSize="7"
                    fill="oklch(0.5 0.02 70)" fontFamily="'IBM Plex Mono',monospace">
                {result ? (result.ok ? `→ ${String(result.stdout||"").slice(0,8)}` : "✕") : t.lang}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

// ---- φ-Wall Gauge ----
function PhiWallGauge({ cost = 1.0, tier = "ALLOW", trust = 1.0 }) {
  const T_ALLOW      = window.GeoSeal.TIER_ALLOW;
  const T_QUARANTINE = window.GeoSeal.TIER_QUARANTINE;
  const T_ESCALATE   = window.GeoSeal.TIER_ESCALATE;
  const MAX = T_ESCALATE * 1.15;

  const pct = Math.min(1, cost / MAX);
  const tierColor = {
    ALLOW:      "oklch(0.72 0.13 155)",
    QUARANTINE: "oklch(0.78 0.14 75)",
    ESCALATE:   "oklch(0.70 0.16 45)",
    DENY:       "oklch(0.64 0.18 25)",
  }[tier];

  const stops = [
    { at: T_ALLOW / MAX,      label: "ALLOW" },
    { at: T_QUARANTINE / MAX, label: "QUAR" },
    { at: T_ESCALATE / MAX,   label: "ESC"  },
  ];

  return (
    <div className="gauge-wrap">
      <div className="panel-head">
        <span className="panel-tag">φ-WALL</span>
        <span className="panel-tier" style={{color:tierColor, borderColor:tierColor}}>{tier}</span>
      </div>
      <div className="gauge-track">
        <div className="gauge-fill" style={{width:`${pct*100}%`, background:tierColor}} />
        {stops.map(s => (
          <div key={s.label} className="gauge-stop" style={{left:`${s.at*100}%`}}>
            <div className="gauge-stop-tick"/>
            <div className="gauge-stop-label">{s.label}</div>
          </div>
        ))}
      </div>
      <div className="gauge-readouts">
        <div><span className="rl-k">cost</span><span className="rl-v">{cost.toFixed(4)}</span></div>
        <div><span className="rl-k">trust</span><span className="rl-v">{(trust*100).toFixed(1)}%</span></div>
        <div><span className="rl-k">H(d,R)</span><span className="rl-v">φ^d/(1+e⁻ᴿ)</span></div>
      </div>
    </div>
  );
}

// ---- Seal Ledger ----
function SealLedger({ entries, onSelect, selectedId, onExport, onClear }) {
  return (
    <div className="ledger-wrap">
      <div className="panel-head">
        <span className="panel-tag">LEDGER</span>
        <span className="panel-meta">.scbe/geoseal_calls.jsonl · {entries.length}</span>
        <span className="panel-actions">
          <button type="button" className="panel-btn"
            disabled={!entries.length}
            title="Download ledger as JSONL"
            onClick={onExport}>export</button>
          <button type="button" className="panel-btn"
            disabled={!entries.length}
            title="Clear ledger (export first to keep records)"
            onClick={onClear}>clear</button>
        </span>
      </div>
      <div className="ledger-list">
        {entries.length === 0 && (
          <div className="ledger-empty">— no records yet —<br/>run a swarm to write to the ledger</div>
        )}
        {entries.map(e => {
          const tongueData = window.GeoSeal.TONGUE_BY_CODE[e.tongue];
          return (
            <div key={e.id}
                 className={`ledger-row ${selectedId===e.id?"sel":""}`}
                 onClick={() => onSelect && onSelect(e.id)}>
              <div className="lr-line1">
                <span className="lr-time">{e.time}</span>
                <span className="lr-op">{e.op}</span>
                <span className="lr-tongue" style={{color: tongueData?.color}}>
                  {e.tongue}{e.tongues && e.tongues.length>1 ? `+${e.tongues.length-1}` : ""}
                </span>
                <span className={`lr-tier tier-${e.tier}`}>{e.tier}</span>
              </div>
              <div className="lr-line2">
                <span className="lr-seal">{e.seal.slice(0,24)}…</span>
                <span className="lr-quorum">{e.quorum_ok ? "✓ quorum" : (e.tongues?.length>1 ? "—" : "")}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

window.PhiRosette  = PhiRosette;
window.PhiWallGauge = PhiWallGauge;
window.SealLedger  = SealLedger;
