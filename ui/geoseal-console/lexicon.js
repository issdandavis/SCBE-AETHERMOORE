// GeoSeal lexicon — subset of the 64-op Sacred Tongue lexicon
// Each op has emit templates per tongue and a chi (risk) score.

const PHI = (1 + Math.sqrt(5)) / 2;

const TONGUES = [
  { code: "KO", name: "Kor'aelin",     lang: "python",     phi: 1.000, phase: 0,                color: "oklch(0.82 0.12 75)"  }, // amber
  { code: "AV", name: "Avali",         lang: "typescript", phi: 1.618, phase: Math.PI / 3,      color: "oklch(0.78 0.13 45)"  }, // copper
  { code: "RU", name: "Runethic",      lang: "rust",       phi: 2.618, phase: 2*Math.PI / 3,    color: "oklch(0.72 0.14 25)"  }, // rust-red
  { code: "CA", name: "Cassisivadan",  lang: "c",          phi: 4.236, phase: Math.PI,          color: "oklch(0.70 0.13 340)" }, // mauve
  { code: "UM", name: "Umbroth",       lang: "julia",      phi: 6.854, phase: 4*Math.PI / 3,    color: "oklch(0.72 0.13 270)" }, // violet
  { code: "DR", name: "Draumric",      lang: "haskell",    phi: 11.090, phase: 5*Math.PI / 3,   color: "oklch(0.74 0.13 200)" }, // teal
];

const TONGUE_BY_CODE = Object.fromEntries(TONGUES.map(t => [t.code, t]));

// 24 ops grouped into bands. Each op has emit templates per tongue.
const LEXICON = [
  // --- ARITH band ---
  { id: 0x01, name: "add",   band: "ARITH",   chi: 0.05, args: ["a","b"], emit: {
    KO: (a,b)=>`${a} + ${b}`,
    AV: (a,b)=>`${a} + ${b}`,
    RU: (a,b)=>`${a} + ${b}`,
    CA: (a,b)=>`(${a}) + (${b})`,
    UM: (a,b)=>`${a} + ${b}`,
    DR: (a,b)=>`(${a}) + (${b})`,
  }},
  { id: 0x02, name: "sub",   band: "ARITH",   chi: 0.05, args: ["a","b"], emit: {
    KO: (a,b)=>`${a} - ${b}`, AV:(a,b)=>`${a} - ${b}`, RU:(a,b)=>`${a} - ${b}`,
    CA:(a,b)=>`(${a}) - (${b})`, UM:(a,b)=>`${a} - ${b}`, DR:(a,b)=>`(${a}) - (${b})`,
  }},
  { id: 0x03, name: "mul",   band: "ARITH",   chi: 0.06, args: ["a","b"], emit: {
    KO:(a,b)=>`${a} * ${b}`, AV:(a,b)=>`${a} * ${b}`, RU:(a,b)=>`${a} * ${b}`,
    CA:(a,b)=>`(${a}) * (${b})`, UM:(a,b)=>`${a} * ${b}`, DR:(a,b)=>`(${a}) * (${b})`,
  }},
  { id: 0x04, name: "div",   band: "ARITH",   chi: 0.18, args: ["a","b"], emit: {
    KO:(a,b)=>`${a} / ${b}`, AV:(a,b)=>`${a} / ${b}`, RU:(a,b)=>`${a} as f64 / ${b} as f64`,
    CA:(a,b)=>`((double)${a}) / ((double)${b})`, UM:(a,b)=>`${a} / ${b}`, DR:(a,b)=>`fromIntegral (${a}) / fromIntegral (${b})`,
  }},
  { id: 0x05, name: "mod",   band: "ARITH",   chi: 0.10, args: ["a","b"], emit: {
    KO:(a,b)=>`${a} % ${b}`, AV:(a,b)=>`${a} % ${b}`, RU:(a,b)=>`${a} % ${b}`,
    CA:(a,b)=>`(${a}) % (${b})`, UM:(a,b)=>`mod(${a}, ${b})`, DR:(a,b)=>`(${a}) \`mod\` (${b})`,
  }},
  { id: 0x06, name: "pow",   band: "ARITH",   chi: 0.22, args: ["a","b"], emit: {
    KO:(a,b)=>`${a} ** ${b}`, AV:(a,b)=>`${a} ** ${b}`, RU:(a,b)=>`(${a} as f64).powi(${b})`,
    CA:(a,b)=>`pow(${a}, ${b})`, UM:(a,b)=>`${a} ^ ${b}`, DR:(a,b)=>`(${a}) ** (${b})`,
  }},

  // --- LOGIC band ---
  { id: 0x10, name: "and",   band: "LOGIC",   chi: 0.12, args: ["a","b"], emit: {
    KO:(a,b)=>`${a} and ${b}`, AV:(a,b)=>`${a} && ${b}`, RU:(a,b)=>`${a} && ${b}`,
    CA:(a,b)=>`(${a}) && (${b})`, UM:(a,b)=>`${a} && ${b}`, DR:(a,b)=>`(${a}) && (${b})`,
  }},
  { id: 0x11, name: "or",    band: "LOGIC",   chi: 0.12, args: ["a","b"], emit: {
    KO:(a,b)=>`${a} or ${b}`, AV:(a,b)=>`${a} || ${b}`, RU:(a,b)=>`${a} || ${b}`,
    CA:(a,b)=>`(${a}) || (${b})`, UM:(a,b)=>`${a} || ${b}`, DR:(a,b)=>`(${a}) || (${b})`,
  }},
  { id: 0x12, name: "xor",   band: "LOGIC",   chi: 0.18, args: ["a","b"], emit: {
    KO:(a,b)=>`${a} ^ ${b}`, AV:(a,b)=>`${a} ^ ${b}`, RU:(a,b)=>`${a} ^ ${b}`,
    CA:(a,b)=>`(${a}) ^ (${b})`, UM:(a,b)=>`xor(${a}, ${b})`, DR:(a,b)=>`xor (${a}) (${b})`,
  }},
  { id: 0x13, name: "not",   band: "LOGIC",   chi: 0.10, args: ["a"], emit: {
    KO:(a)=>`not ${a}`, AV:(a)=>`!${a}`, RU:(a)=>`!${a}`,
    CA:(a)=>`!(${a})`, UM:(a)=>`!${a}`, DR:(a)=>`not (${a})`,
  }},

  // --- COMPARE band ---
  { id: 0x20, name: "eq",    band: "COMPARE", chi: 0.08, args: ["a","b"], emit: {
    KO:(a,b)=>`${a} == ${b}`, AV:(a,b)=>`${a} === ${b}`, RU:(a,b)=>`${a} == ${b}`,
    CA:(a,b)=>`(${a}) == (${b})`, UM:(a,b)=>`${a} == ${b}`, DR:(a,b)=>`(${a}) == (${b})`,
  }},
  { id: 0x21, name: "lt",    band: "COMPARE", chi: 0.08, args: ["a","b"], emit: {
    KO:(a,b)=>`${a} < ${b}`, AV:(a,b)=>`${a} < ${b}`, RU:(a,b)=>`${a} < ${b}`,
    CA:(a,b)=>`(${a}) < (${b})`, UM:(a,b)=>`${a} < ${b}`, DR:(a,b)=>`(${a}) < (${b})`,
  }},
  { id: 0x22, name: "gt",    band: "COMPARE", chi: 0.08, args: ["a","b"], emit: {
    KO:(a,b)=>`${a} > ${b}`, AV:(a,b)=>`${a} > ${b}`, RU:(a,b)=>`${a} > ${b}`,
    CA:(a,b)=>`(${a}) > (${b})`, UM:(a,b)=>`${a} > ${b}`, DR:(a,b)=>`(${a}) > (${b})`,
  }},

  // --- HASH band (higher risk) ---
  { id: 0x30, name: "sha256", band: "HASH",   chi: 0.45, args: ["x"], emit: {
    KO:(x)=>`hashlib.sha256(${x}.encode()).hexdigest()`,
    AV:(x)=>`crypto.createHash("sha256").update(${x}).digest("hex")`,
    RU:(x)=>`format!("{:x}", Sha256::digest(${x}.as_bytes()))`,
    CA:(x)=>`sha256_hex(${x})`,
    UM:(x)=>`bytes2hex(sha256(${x}))`,
    DR:(x)=>`showHex (sha256 ${x})`,
  }},
  { id: 0x31, name: "seal",   band: "HASH",   chi: 0.55, args: ["op","tongue","code"], emit: {
    KO:(o,t,c)=>`geoseal.compute(${o}, ${t}, ${c})`,
    AV:(o,t,c)=>`geoseal.compute(${o}, ${t}, ${c})`,
    RU:(o,t,c)=>`geoseal::compute(${o}, ${t}, ${c})`,
    CA:(o,t,c)=>`geoseal_compute(${o}, ${t}, ${c})`,
    UM:(o,t,c)=>`geoseal_compute(${o}, ${t}, ${c})`,
    DR:(o,t,c)=>`geosealCompute ${o} ${t} ${c}`,
  }},

  // --- IO band ---
  { id: 0x40, name: "print",  band: "IO",     chi: 0.20, args: ["x"], emit: {
    KO:(x)=>`print(${x})`, AV:(x)=>`console.log(${x})`, RU:(x)=>`println!("{}", ${x})`,
    CA:(x)=>`printf("%d\\n", ${x})`, UM:(x)=>`println(${x})`, DR:(x)=>`print ${x}`,
  }},
  { id: 0x41, name: "read",   band: "IO",     chi: 0.35, args: ["path"], emit: {
    KO:(p)=>`open(${p}).read()`, AV:(p)=>`fs.readFileSync(${p}, "utf-8")`,
    RU:(p)=>`std::fs::read_to_string(${p})?`, CA:(p)=>`fread_all(${p})`,
    UM:(p)=>`read(${p}, String)`, DR:(p)=>`readFile ${p}`,
  }},

  // --- FLOW band ---
  { id: 0x50, name: "if",     band: "FLOW",   chi: 0.25, args: ["cond","then","else"], emit: {
    KO:(c,t,e)=>`(${t}) if ${c} else (${e})`, AV:(c,t,e)=>`${c} ? (${t}) : (${e})`,
    RU:(c,t,e)=>`if ${c} { ${t} } else { ${e} }`, CA:(c,t,e)=>`(${c}) ? (${t}) : (${e})`,
    UM:(c,t,e)=>`${c} ? (${t}) : (${e})`, DR:(c,t,e)=>`if ${c} then (${t}) else (${e})`,
  }},
  { id: 0x51, name: "map",    band: "FLOW",   chi: 0.30, args: ["fn","xs"], emit: {
    KO:(f,xs)=>`[${f}(x) for x in ${xs}]`, AV:(f,xs)=>`${xs}.map(${f})`,
    RU:(f,xs)=>`${xs}.iter().map(${f}).collect::<Vec<_>>()`, CA:(f,xs)=>`map_arr(${f}, ${xs})`,
    UM:(f,xs)=>`map(${f}, ${xs})`, DR:(f,xs)=>`map ${f} ${xs}`,
  }},

  // --- HARMONIC band (highest risk) ---
  { id: 0x60, name: "phi_wall", band: "HARMONIC", chi: 0.78, args: ["chi","tongue"], emit: {
    KO:(c,t)=>`phi_wall_cost(${c}, ${t})`, AV:(c,t)=>`phiWallCost(${c}, ${t})`,
    RU:(c,t)=>`phi_wall_cost(${c}, ${t})`, CA:(c,t)=>`phi_wall_cost(${c}, ${t})`,
    UM:(c,t)=>`phi_wall_cost(${c}, ${t})`, DR:(c,t)=>`phiWallCost ${c} ${t}`,
  }},
  { id: 0x61, name: "harmonize",band: "HARMONIC", chi: 0.85, args: ["sig","ref"], emit: {
    KO:(s,r)=>`harmonize(${s}, ${r})`, AV:(s,r)=>`harmonize(${s}, ${r})`,
    RU:(s,r)=>`harmonize(${s}, ${r})`, CA:(s,r)=>`harmonize(${s}, ${r})`,
    UM:(s,r)=>`harmonize(${s}, ${r})`, DR:(s,r)=>`harmonize ${s} ${r}`,
  }},
  { id: 0x62, name: "spiral",   band: "HARMONIC", chi: 0.72, args: ["depth"], emit: {
    KO:(d)=>`phi_spiral(${d})`, AV:(d)=>`phiSpiral(${d})`, RU:(d)=>`phi_spiral(${d})`,
    CA:(d)=>`phi_spiral(${d})`, UM:(d)=>`phi_spiral(${d})`, DR:(d)=>`phiSpiral ${d}`,
  }},
];

const LEXICON_BY_NAME = Object.fromEntries(LEXICON.map(e => [e.name, e]));

// φ-wall governance
function phiWallCost(chi, tongueCode) {
  const w = TONGUE_BY_CODE[tongueCode]?.phi ?? 1.0;
  const d = (chi * w) / 11.090;
  const R = 5.0;
  return (PHI ** d) / (1 + Math.exp(-R));
}

const TIER_ALLOW      = PHI ** 0.5; // 1.272
const TIER_QUARANTINE = PHI ** 1.0; // 1.618
const TIER_ESCALATE   = PHI ** 1.5; // 2.058

function phiWallTier(cost) {
  if (cost < TIER_ALLOW)      return "ALLOW";
  if (cost < TIER_QUARANTINE) return "QUARANTINE";
  if (cost < TIER_ESCALATE)   return "ESCALATE";
  return "DENY";
}

function phiTrustScore(cost) {
  return Math.min(1, Math.max(0, 1 - (cost - 1) / (TIER_ESCALATE - 1)));
}

// SHA-256 (sync, via SubtleCrypto would be async — use a tiny synchronous hash for the demo)
// We use a deterministic but lightweight hash so the UI can render seals instantly.
function fnv1aHex(s) {
  let h = 0xcbf29ce484222325n;
  const p = 0x100000001b3n;
  for (let i = 0; i < s.length; i++) {
    h ^= BigInt(s.charCodeAt(i));
    h = (h * p) & 0xffffffffffffffffn;
  }
  // expand to 64 hex chars by hashing in 4 rotations for visual richness
  let out = "";
  for (let r = 0; r < 4; r++) {
    let x = h ^ (BigInt(r) * 0x9e3779b97f4a7c15n);
    x = (x ^ (x >> 33n)) * 0xff51afd7ed558ccdn & 0xffffffffffffffffn;
    x = (x ^ (x >> 33n)) * 0xc4ceb9fe1a85ec53n & 0xffffffffffffffffn;
    x = x ^ (x >> 33n);
    out += x.toString(16).padStart(16, "0");
  }
  return out.slice(0, 64);
}

function computeSeal(op, tongue, code, payload, phiCost, tier) {
  const tongueData = TONGUE_BY_CODE[tongue];
  const phase = tongueData?.phase ?? 0;
  const blob = `${op}|${tongue}|${code}|${payload||""}|${phase.toFixed(12)}|${phiCost.toFixed(8)}|${tier}`;
  return fnv1aHex(blob);
}

window.GeoSeal = {
  PHI, TONGUES, TONGUE_BY_CODE, LEXICON, LEXICON_BY_NAME,
  phiWallCost, phiWallTier, phiTrustScore,
  TIER_ALLOW, TIER_QUARANTINE, TIER_ESCALATE,
  computeSeal, fnv1aHex,
};
