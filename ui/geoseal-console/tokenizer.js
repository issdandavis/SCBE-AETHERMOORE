// Bijective Sacred Tongue tokenizer — authentic prefix/suffix tables from src/crypto/sacred_tongues.py.
// Each byte b maps to `${prefixes[(b>>4)&0xF]}'${suffixes[b&0xF]}` per tongue. 256 unique tokens, perfectly invertible.

const TONGUE_SPECS = {
  KO: {
    name: "Kor'aelin", domain: "nonce/flow/intent", hz: 440.00,
    prefixes: ["kor","ael","syl","myr","lyn","aer","oth","sera","vael","ny","ash","fae","zir","cael","quil","sora"],
    suffixes: ["a","e","i","o","u","ae","sh","th","el","ar","an","en","un","ir","oth","esh"],
  },
  AV: {
    name: "Avali", domain: "aad/header/metadata", hz: 523.25,
    prefixes: ["saina","talan","vessa","maren","oriel","serin","nurel","lirea","kiva","lumen","calma","ponte","verin","nava","sela","tide"],
    suffixes: ["a","e","i","o","u","y","la","re","na","sa","to","mi","ve","ri","en","ul"],
  },
  RU: {
    name: "Runethic", domain: "salt/binding", hz: 329.63,
    prefixes: ["khar","drath","bront","vael","ur","mem","krak","tharn","groth","basalt","rune","sear","oath","gnarl","rift","iron"],
    suffixes: ["ak","eth","ik","ul","or","ar","um","on","ir","esh","nul","vek","dra","kh","va","th"],
  },
  CA: {
    name: "Cassisivadan", domain: "ciphertext/bitcraft", hz: 659.25,
    prefixes: ["bip","bop","klik","loopa","ifta","thena","elsa","spira","rythm","quirk","fizz","gear","pop","zip","mix","chass"],
    suffixes: ["a","e","i","o","u","y","ta","na","sa","ra","lo","mi","ki","zi","qwa","sh"],
  },
  UM: {
    name: "Umbroth", domain: "redaction/veil", hz: 293.66,
    prefixes: ["veil","zhur","nar","shul","math","hollow","hush","thorn","dusk","echo","ink","wisp","bind","ache","null","shade"],
    suffixes: ["a","e","i","o","u","ae","sh","th","ak","ul","or","ir","en","on","vek","nul"],
  },
  DR: {
    name: "Draumric", domain: "tag/structure", hz: 392.00,
    prefixes: ["anvil","tharn","mek","grond","draum","ektal","temper","forge","stone","steam","oath","seal","frame","pillar","rivet","ember"],
    suffixes: ["a","e","i","o","u","ae","rak","mek","tharn","grond","vek","ul","or","ar","en","on"],
  },
};

// RWP v3.0 canonical section→tongue map
const SECTION_TONGUES = {
  aad: "AV", salt: "RU", nonce: "KO", ct: "CA", tag: "DR", redact: "UM",
};

function buildTables() {
  const b2t = {}, t2b = {};
  for (const code of Object.keys(TONGUE_SPECS)) {
    const s = TONGUE_SPECS[code];
    const arr = new Array(256);
    const inv = {};
    for (let b = 0; b < 256; b++) {
      const hi = (b >> 4) & 0xF, lo = b & 0xF;
      const tok = `${s.prefixes[hi]}'${s.suffixes[lo]}`;
      arr[b] = tok;
      inv[tok] = b;
    }
    b2t[code] = arr; t2b[code] = inv;
  }
  return { b2t, t2b };
}

const { b2t: BYTE_TO_TOKEN, t2b: TOKEN_TO_BYTE } = buildTables();

function encodeBytes(tongue, bytes) {
  const t = BYTE_TO_TOKEN[tongue];
  if (!t) throw new Error(`unknown tongue: ${tongue}`);
  const out = new Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) out[i] = t[bytes[i]];
  return out;
}
function decodeTokens(tongue, tokens) {
  const t = TOKEN_TO_BYTE[tongue];
  if (!t) throw new Error(`unknown tongue: ${tongue}`);
  const out = new Uint8Array(tokens.length);
  for (let i = 0; i < tokens.length; i++) {
    if (!(tokens[i] in t)) throw new Error(`invalid token "${tokens[i]}" for ${tongue}`);
    out[i] = t[tokens[i]];
  }
  return out;
}
function strToBytes(s) { return new TextEncoder().encode(s); }
function bytesToStr(b) { return new TextDecoder().decode(b); }
function bytesToHex(b) { return Array.from(b).map(x=>x.toString(16).padStart(2,"0")).join(""); }

// Cross-tongue translate: decode through one, re-encode through the other (preserves byte stream).
function xlateTokens(fromTongue, toTongue, tokens) {
  const bytes = decodeTokens(fromTongue, tokens);
  return encodeBytes(toTongue, bytes);
}

// Verify roundtrip property — used by `tokenizer-verify` command
function verifyBijection(tongue) {
  for (let b = 0; b < 256; b++) {
    const tok = BYTE_TO_TOKEN[tongue][b];
    if (TOKEN_TO_BYTE[tongue][tok] !== b) return { ok: false, badByte: b };
  }
  return { ok: true, count: 256 };
}

window.SacredTokenizer = {
  TONGUE_SPECS, SECTION_TONGUES,
  encodeBytes, decodeTokens, xlateTokens,
  strToBytes, bytesToStr, bytesToHex,
  verifyBijection,
};
