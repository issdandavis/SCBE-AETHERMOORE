// JS mirror of python/scbe/tongue_roles.py — the REAL SCBE semantic schema.
// The game compiles two tongues into a program with these exact roles, so the
// spell crafting is doing real SCBE tongue-language work, not toy logic.
export const TONGUE_ROLE = {
  KO: { name: "Kor'aelin",    role: "Control Flow",  keyword: "loop",  glyph: "ᚲ", color: "#ef4444" },
  AV: { name: "Avali",        role: "Input/Output",  keyword: "sense", glyph: "ᚨ", color: "#22d3ee" },
  RU: { name: "Runethic",     role: "Scope/Context", keyword: "area",  glyph: "ᚱ", color: "#34d399" },
  CA: { name: "Cassisivadan", role: "Math/Logic",    keyword: "calc",  glyph: "ᚳ", color: "#fbbf24" },
  UM: { name: "Umbroth",      role: "Security",      keyword: "ward",  glyph: "ᚢ", color: "#a78bfa" },
  DR: { name: "Draumric",     role: "Transforms",    keyword: "morph", glyph: "ᛞ", color: "#f472b6" },
};

// outer(inner()) — same as tongue_roles.compile_pair() in Python.
export function compilePair(outer, inner) {
  const o = TONGUE_ROLE[outer], i = TONGUE_ROLE[inner];
  if (!o || !i) return null;
  return {
    outer, inner,
    program: `${o.keyword}(${i.keyword}())`,
    semantics: `${o.role} of ${i.role}`,
    glyphs: o.glyph + i.glyph,
  };
}
