import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Calculator,
  Variable,
  Sparkles,
  ChevronRight,
  Trash2,
  Copy,
  Check,
  FunctionSquare,
  Play,
  Download,
  Lightbulb,
  X,
  Atom,
  FlaskConical,
  Binary,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react';

// ═══════════════════════════════════════════════════════════════
//  CHEMISTRY DATA
// ═══════════════════════════════════════════════════════════════

interface Element {
  symbol: string;
  name: string;
  number: number;
  mass: number;
  category: string;
  electrons: number[];
}

const PERIODIC_TABLE: Record<string, Element> = {
  H: {
    symbol: 'H',
    name: 'Hydrogen',
    number: 1,
    mass: 1.008,
    category: 'nonmetal',
    electrons: [1],
  },
  He: { symbol: 'He', name: 'Helium', number: 2, mass: 4.0026, category: 'noble', electrons: [2] },
  Li: {
    symbol: 'Li',
    name: 'Lithium',
    number: 3,
    mass: 6.94,
    category: 'alkali',
    electrons: [2, 1],
  },
  Be: {
    symbol: 'Be',
    name: 'Beryllium',
    number: 4,
    mass: 9.0122,
    category: 'alkaline',
    electrons: [2, 2],
  },
  B: {
    symbol: 'B',
    name: 'Boron',
    number: 5,
    mass: 10.81,
    category: 'metalloid',
    electrons: [2, 3],
  },
  C: {
    symbol: 'C',
    name: 'Carbon',
    number: 6,
    mass: 12.011,
    category: 'nonmetal',
    electrons: [2, 4],
  },
  N: {
    symbol: 'N',
    name: 'Nitrogen',
    number: 7,
    mass: 14.007,
    category: 'nonmetal',
    electrons: [2, 5],
  },
  O: {
    symbol: 'O',
    name: 'Oxygen',
    number: 8,
    mass: 15.999,
    category: 'nonmetal',
    electrons: [2, 6],
  },
  F: {
    symbol: 'F',
    name: 'Fluorine',
    number: 9,
    mass: 18.998,
    category: 'halogen',
    electrons: [2, 7],
  },
  Ne: { symbol: 'Ne', name: 'Neon', number: 10, mass: 20.18, category: 'noble', electrons: [2, 8] },
  Na: {
    symbol: 'Na',
    name: 'Sodium',
    number: 11,
    mass: 22.99,
    category: 'alkali',
    electrons: [2, 8, 1],
  },
  Mg: {
    symbol: 'Mg',
    name: 'Magnesium',
    number: 12,
    mass: 24.305,
    category: 'alkaline',
    electrons: [2, 8, 2],
  },
  Al: {
    symbol: 'Al',
    name: 'Aluminium',
    number: 13,
    mass: 26.982,
    category: 'post-transition',
    electrons: [2, 8, 3],
  },
  Si: {
    symbol: 'Si',
    name: 'Silicon',
    number: 14,
    mass: 28.085,
    category: 'metalloid',
    electrons: [2, 8, 4],
  },
  P: {
    symbol: 'P',
    name: 'Phosphorus',
    number: 15,
    mass: 30.974,
    category: 'nonmetal',
    electrons: [2, 8, 5],
  },
  S: {
    symbol: 'S',
    name: 'Sulfur',
    number: 16,
    mass: 32.06,
    category: 'nonmetal',
    electrons: [2, 8, 6],
  },
  Cl: {
    symbol: 'Cl',
    name: 'Chlorine',
    number: 17,
    mass: 35.45,
    category: 'halogen',
    electrons: [2, 8, 7],
  },
  Ar: {
    symbol: 'Ar',
    name: 'Argon',
    number: 18,
    mass: 39.948,
    category: 'noble',
    electrons: [2, 8, 8],
  },
  K: {
    symbol: 'K',
    name: 'Potassium',
    number: 19,
    mass: 39.098,
    category: 'alkali',
    electrons: [2, 8, 8, 1],
  },
  Ca: {
    symbol: 'Ca',
    name: 'Calcium',
    number: 20,
    mass: 40.078,
    category: 'alkaline',
    electrons: [2, 8, 8, 2],
  },
  Sc: {
    symbol: 'Sc',
    name: 'Scandium',
    number: 21,
    mass: 44.956,
    category: 'transition',
    electrons: [2, 8, 9, 2],
  },
  Ti: {
    symbol: 'Ti',
    name: 'Titanium',
    number: 22,
    mass: 47.867,
    category: 'transition',
    electrons: [2, 8, 10, 2],
  },
  V: {
    symbol: 'V',
    name: 'Vanadium',
    number: 23,
    mass: 50.942,
    category: 'transition',
    electrons: [2, 8, 11, 2],
  },
  Cr: {
    symbol: 'Cr',
    name: 'Chromium',
    number: 24,
    mass: 51.996,
    category: 'transition',
    electrons: [2, 8, 13, 1],
  },
  Mn: {
    symbol: 'Mn',
    name: 'Manganese',
    number: 25,
    mass: 54.938,
    category: 'transition',
    electrons: [2, 8, 13, 2],
  },
  Fe: {
    symbol: 'Fe',
    name: 'Iron',
    number: 26,
    mass: 55.845,
    category: 'transition',
    electrons: [2, 8, 14, 2],
  },
  Co: {
    symbol: 'Co',
    name: 'Cobalt',
    number: 27,
    mass: 58.933,
    category: 'transition',
    electrons: [2, 8, 15, 2],
  },
  Ni: {
    symbol: 'Ni',
    name: 'Nickel',
    number: 28,
    mass: 58.693,
    category: 'transition',
    electrons: [2, 8, 16, 2],
  },
  Cu: {
    symbol: 'Cu',
    name: 'Copper',
    number: 29,
    mass: 63.546,
    category: 'transition',
    electrons: [2, 8, 18, 1],
  },
  Zn: {
    symbol: 'Zn',
    name: 'Zinc',
    number: 30,
    mass: 65.38,
    category: 'transition',
    electrons: [2, 8, 18, 2],
  },
  Ga: {
    symbol: 'Ga',
    name: 'Gallium',
    number: 31,
    mass: 69.723,
    category: 'post-transition',
    electrons: [2, 8, 18, 3],
  },
  Ge: {
    symbol: 'Ge',
    name: 'Germanium',
    number: 32,
    mass: 72.63,
    category: 'metalloid',
    electrons: [2, 8, 18, 4],
  },
  As: {
    symbol: 'As',
    name: 'Arsenic',
    number: 33,
    mass: 74.922,
    category: 'metalloid',
    electrons: [2, 8, 18, 5],
  },
  Se: {
    symbol: 'Se',
    name: 'Selenium',
    number: 34,
    mass: 78.96,
    category: 'nonmetal',
    electrons: [2, 8, 18, 6],
  },
  Br: {
    symbol: 'Br',
    name: 'Bromine',
    number: 35,
    mass: 79.904,
    category: 'halogen',
    electrons: [2, 8, 18, 7],
  },
  Kr: {
    symbol: 'Kr',
    name: 'Krypton',
    number: 36,
    mass: 83.798,
    category: 'noble',
    electrons: [2, 8, 18, 8],
  },
  Rb: {
    symbol: 'Rb',
    name: 'Rubidium',
    number: 37,
    mass: 85.468,
    category: 'alkali',
    electrons: [2, 8, 18, 8, 1],
  },
  Sr: {
    symbol: 'Sr',
    name: 'Strontium',
    number: 38,
    mass: 87.62,
    category: 'alkaline',
    electrons: [2, 8, 18, 8, 2],
  },
  Ag: {
    symbol: 'Ag',
    name: 'Silver',
    number: 47,
    mass: 107.87,
    category: 'transition',
    electrons: [2, 8, 18, 18, 1],
  },
  Au: {
    symbol: 'Au',
    name: 'Gold',
    number: 79,
    mass: 196.97,
    category: 'transition',
    electrons: [2, 8, 18, 32, 18, 1],
  },
  Hg: {
    symbol: 'Hg',
    name: 'Mercury',
    number: 80,
    mass: 200.59,
    category: 'transition',
    electrons: [2, 8, 18, 32, 18, 2],
  },
  Pb: {
    symbol: 'Pb',
    name: 'Lead',
    number: 82,
    mass: 207.2,
    category: 'post-transition',
    electrons: [2, 8, 18, 32, 18, 4],
  },
  U: {
    symbol: 'U',
    name: 'Uranium',
    number: 92,
    mass: 238.03,
    category: 'actinide',
    electrons: [2, 8, 18, 32, 21, 9, 2],
  },
};

// Parse chemical formula and compute molar mass
// e.g. "H2O" -> 18.015, "C6H12O6" -> 180.156
function parseFormula(formula: string): {
  mass: number;
  breakdown: { symbol: string; count: number; mass: number }[];
  error?: string;
} {
  const breakdown: { symbol: string; count: number; mass: number }[] = [];
  let totalMass = 0;
  // Tokenize: elements (upper + optional lower) followed by optional count
  const regex = /([A-Z][a-z]?)(\d*)|(\()|(\))(\d*)/g;
  const stack: { mult: number; items: typeof breakdown }[] = [{ mult: 1, items: [] }];
  let m: RegExpExecArray | null;

  while ((m = regex.exec(formula)) !== null) {
    if (m[1]) {
      // Element
      const sym = m[1];
      const count = m[2] ? parseInt(m[2]) : 1;
      const el = PERIODIC_TABLE[sym];
      if (!el) return { mass: 0, breakdown: [], error: `Unknown element: ${sym}` };
      const mass = el.mass * count;
      totalMass += mass;
      breakdown.push({ symbol: sym, count, mass });
    } else if (m[3]) {
      // Open paren
      stack.push({ mult: 1, items: [] });
    } else if (m[4]) {
      // Close paren with multiplier
      const mult = m[5] ? parseInt(m[5]) : 1;
      const group = stack.pop()!;
      group.mult = mult;
      // Apply multiplier to group's mass contribution
      for (const item of group.items) {
        item.count *= mult;
        item.mass *= mult;
        totalMass += (item.mass * (mult - 1)) / mult; // adjust
      }
      if (stack.length === 0) return { mass: 0, breakdown: [], error: 'Mismatched parentheses' };
    }
  }

  // Re-parse properly with parentheses support
  try {
    const result = parseFormulaProper(formula);
    return result;
  } catch (e: any) {
    return { mass: 0, breakdown: [], error: e.message };
  }
}

function parseFormulaProper(formula: string): {
  mass: number;
  breakdown: { symbol: string; count: number; mass: number }[];
} {
  const breakdown: { symbol: string; count: number; mass: number }[] = [];
  let i = 0;

  function parseGroup(endChar?: string): number {
    let groupMass = 0;
    while (i < formula.length) {
      const c = formula[i];
      if (endChar && c === endChar) {
        i++;
        break;
      }

      if (c === '(') {
        i++;
        const inner = parseGroup(')');
        const mult = parseNum();
        groupMass += inner * mult;
      } else if (/[A-Z]/.test(c)) {
        i++;
        let sym = c;
        if (i < formula.length && /[a-z]/.test(formula[i])) {
          sym += formula[i];
          i++;
        }
        const el = PERIODIC_TABLE[sym];
        if (!el) throw new Error(`Unknown element: ${sym}`);
        const count = parseNum();
        groupMass += el.mass * count;
        const existing = breakdown.find((b) => b.symbol === sym);
        if (existing) {
          existing.count += count;
          existing.mass = el.mass * existing.count;
        } else breakdown.push({ symbol: sym, count, mass: el.mass * count });
      } else {
        i++;
      }
    }
    return groupMass;
  }

  function parseNum(): number {
    let numStr = '';
    while (i < formula.length && /\d/.test(formula[i])) {
      numStr += formula[i];
      i++;
    }
    return numStr ? parseInt(numStr) : 1;
  }

  const mass = parseGroup();
  return { mass, breakdown };
}

// ═══════════════════════════════════════════════════════════════
//  MATH ENGINE
// ═══════════════════════════════════════════════════════════════

interface VarScope {
  [name: string]: number;
}

let TRIG_MODE: 'rad' | 'deg' = 'rad';

function toRad(v: number): number {
  return TRIG_MODE === 'deg' ? (v * Math.PI) / 180 : v;
}
function fromRad(v: number): number {
  return TRIG_MODE === 'deg' ? (v * 180) / Math.PI : v;
}

const CONSTANTS: Record<string, number> = {
  pi: Math.PI,
  e: Math.E,
  tau: Math.PI * 2,
  phi: 1.618033988749895,
  ln2: Math.LN2,
  ln10: Math.LN10,
  sqrt2: Math.SQRT2,
  sqrt1_2: Math.SQRT1_2,
  inf: Infinity,
  // Chemistry constants
  Na: 6.02214076e23, // Avogadro
  R: 8.314462618, // Gas constant J/(mol·K)
  k: 1.380649e-23, // Boltzmann
  c: 299792458, // Speed of light m/s
  h: 6.62607015e-34, // Planck
  G: 6.6743e-11, // Gravitational
  F: 96485.33212, // Faraday
};

const FUNCTIONS: Record<string, (args: number[]) => number> = {
  // Trig (respects deg/rad mode)
  sin: ([a]) => Math.sin(toRad(a)),
  cos: ([a]) => Math.cos(toRad(a)),
  tan: ([a]) => Math.tan(toRad(a)),
  asin: ([a]) => fromRad(Math.asin(a)),
  acos: ([a]) => fromRad(Math.acos(a)),
  atan: ([a]) => fromRad(Math.atan(a)),
  // Reciprocal trig
  sec: ([a]) => 1 / Math.cos(toRad(a)),
  csc: ([a]) => 1 / Math.sin(toRad(a)),
  cot: ([a]) => 1 / Math.tan(toRad(a)),
  asec: ([a]) => fromRad(Math.acos(1 / a)),
  acsc: ([a]) => fromRad(Math.asin(1 / a)),
  acot: ([a]) => fromRad(Math.atan(1 / a)),
  // Hyperbolic
  sinh: ([a]) => Math.sinh(a),
  cosh: ([a]) => Math.cosh(a),
  tanh: ([a]) => Math.tanh(a),
  asinh: ([a]) => Math.asinh(a),
  acosh: ([a]) => Math.acosh(a),
  atanh: ([a]) => Math.atanh(a),
  // Log
  log: ([a]) => Math.log10(a),
  ln: ([a]) => Math.log(a),
  log2: ([a]) => Math.log2(a),
  logb: ([a, b]) => Math.log(a) / Math.log(b),
  // Roots / power
  sqrt: ([a]) => Math.sqrt(a),
  cbrt: ([a]) => Math.cbrt(a),
  // Rounding
  abs: ([a]) => Math.abs(a),
  floor: ([a]) => Math.floor(a),
  ceil: ([a]) => Math.ceil(a),
  round: ([a]) => Math.round(a),
  trunc: ([a]) => Math.trunc(a),
  sign: ([a]) => Math.sign(a),
  // Exp
  exp: ([a]) => Math.exp(a),
  expm1: ([a]) => Math.expm1(a),
  // Conversion
  deg: ([a]) => (a * 180) / Math.PI,
  rad: ([a]) => (a * Math.PI) / 180,
  dms: ([a]) => {
    const d = Math.floor(a);
    const mf = (a - d) * 60;
    const m = Math.floor(mf);
    const s = (mf - m) * 60;
    return d + m / 100 + s / 10000;
  },
  // Aggregates
  min: (args) => Math.min(...args),
  max: (args) => Math.max(...args),
  sum: (args) => args.reduce((s, v) => s + v, 0),
  avg: (args) => args.reduce((s, v) => s + v, 0) / args.length,
  prod: (args) => args.reduce((s, v) => s * v, 1),
  // Combinatorics
  fact: ([a]) => {
    let r = 1;
    for (let i = 2; i <= Math.floor(a); i++) r *= i;
    return r;
  },
  ncr: ([n, r]) => {
    const f = FUNCTIONS.fact;
    return f([n]) / (f([r]) * f([n - r]));
  },
  npr: ([n, r]) => {
    const f = FUNCTIONS.fact;
    return f([n]) / f([n - r]);
  },
  // Number theory
  gcd: ([a, b]) => {
    let x = Math.abs(Math.floor(a)),
      y = Math.abs(Math.floor(b));
    while (y) {
      const t = y;
      y = x % y;
      x = t;
    }
    return x;
  },
  lcm: ([a, b]) => {
    const g = FUNCTIONS.gcd([a, b]);
    return g ? Math.abs(a * b) / g : 0;
  },
  mod: ([a, b]) => ((a % b) + b) % b,
  // Random
  rand: ([min = 0, max = 1]) => min + Math.random() * (max - min),
  randint: ([min, max]) => Math.floor(min + Math.random() * (max - min + 1)),
  // Utility
  hypot: (args) => Math.hypot(...args),
  clamp: ([v, mn, mx]) => Math.min(mx, Math.max(mn, v)),
  lerp: ([a, b, t]) => a + (b - a) * t,
  map: ([v, a1, a2, b1, b2]) => b1 + ((v - a1) * (b2 - b1)) / (a2 - a1),
  // Chemistry
  mol: ([mass, molarMass]) => mass / molarMass,
  atoms: ([moles]) => moles * CONSTANTS.Na,
  mass_from_mol: ([moles, molarMass]) => moles * molarMass,
  ideal_gas_P: ([n, V, T]) => (n * CONSTANTS.R * T) / V,
  ideal_gas_n: ([P, V, T]) => (P * V) / (CONSTANTS.R * T),
  ideal_gas_V: ([n, P, T]) => (n * CONSTANTS.R * T) / P,
  celsius_to_kelvin: ([C]) => C + 273.15,
  kelvin_to_celsius: ([K]) => K - 273.15,
  fahrenheit_to_celsius: ([F]) => ((F - 32) * 5) / 9,
  celsius_to_fahrenheit: ([C]) => (C * 9) / 5 + 32,
};

type Token =
  | { type: 'num'; value: number }
  | { type: 'var'; name: string }
  | { type: 'op'; op: string }
  | { type: 'fn'; name: string }
  | { type: 'lparen' }
  | { type: 'rparen' }
  | { type: 'comma' }
  | { type: 'assign'; name: string };

function isOpToken(t: Token): t is Token & { type: 'op'; op: string } {
  return t.type === 'op';
}
function isLparenToken(t: Token): t is Token & { type: 'lparen' } {
  return t.type === 'lparen';
}
function isFnToken(t: Token): t is Token & { type: 'fn'; name: string } {
  return t.type === 'fn';
}

function tokenize(input: string): Token[] {
  const tokens: Token[] = [];
  let i = 0;
  const s = input.trim();
  while (i < s.length) {
    const c = s[i];
    if (/\s/.test(c)) {
      i++;
      continue;
    }
    if (/[a-zA-Z_]/.test(c)) {
      let name = '';
      while (i < s.length && /[a-zA-Z0-9_]/.test(s[i])) name += s[i++];
      const rest = s.slice(i).trimStart();
      if (rest.startsWith('=') && !rest.startsWith('==')) {
        tokens.push({ type: 'assign', name });
        i = s.indexOf('=', i) + 1;
        continue;
      }
      if (name in FUNCTIONS) tokens.push({ type: 'fn', name });
      else tokens.push({ type: 'var', name });
      continue;
    }
    if (/\d/.test(c) || (c === '.' && /\d/.test(s[i + 1] || ''))) {
      let num = '';
      while (
        i < s.length &&
        (/\d/.test(s[i]) ||
          s[i] === '.' ||
          s[i] === 'e' ||
          s[i] === 'E' ||
          s[i] === '+' ||
          s[i] === '-')
      ) {
        if ((s[i] === '+' || s[i] === '-') && num.length > 0 && !/[eE]/.test(num[num.length - 1]))
          break;
        num += s[i++];
      }
      tokens.push({ type: 'num', value: parseFloat(num) });
      continue;
    }
    if (c === '(') {
      tokens.push({ type: 'lparen' });
      i++;
      continue;
    }
    if (c === ')') {
      tokens.push({ type: 'rparen' });
      i++;
      continue;
    }
    if (c === ',') {
      tokens.push({ type: 'comma' });
      i++;
      continue;
    }
    if (c === '*' && s[i + 1] === '*') {
      tokens.push({ type: 'op', op: '^' });
      i += 2;
      continue;
    }
    if (c === '/' && s[i + 1] === '/') {
      tokens.push({ type: 'op', op: '//' });
      i += 2;
      continue;
    }
    if (c === '<' && s[i + 1] === '<') {
      tokens.push({ type: 'op', op: '<<' });
      i += 2;
      continue;
    }
    if (c === '>' && s[i + 1] === '>') {
      tokens.push({ type: 'op', op: '>>' });
      i += 2;
      continue;
    }
    if (c === '!') {
      tokens.push({ type: 'op', op: '!' });
      i++;
      continue;
    }
    if (['+', '-', '*', '/', '%', '^', '<', '>'].includes(c)) {
      tokens.push({ type: 'op', op: c });
      i++;
      continue;
    }
    throw new Error(`Unexpected character: "${c}" at position ${i}`);
  }
  return tokens;
}

function parse(tokens: Token[]): { expr: string; assignTo?: string } {
  if (tokens.length === 0) throw new Error('Empty expression');
  if (tokens[0].type === 'assign') {
    return { expr: tokensToString(tokens.slice(1)), assignTo: tokens[0].name };
  }
  return { expr: tokensToString(tokens) };
}

function tokensToString(tokens: Token[]): string {
  return tokens
    .map((t) => {
      if (t.type === 'num') return String(t.value);
      if (t.type === 'var') return t.name;
      if (t.type === 'op') return t.op;
      if (t.type === 'fn') return t.name;
      if (t.type === 'lparen') return '(';
      if (t.type === 'rparen') return ')';
      if (t.type === 'comma') return ',';
      return '';
    })
    .join(' ');
}

function evaluate(expr: string, vars: VarScope): number {
  return evalTokens(tokenize(expr), vars);
}

function evalTokens(tokens: Token[], vars: VarScope): number {
  const output: Token[] = [];
  const ops: Token[] = [];
  const prec = (op: string) => {
    const p: Record<string, number> = {
      '=': 1,
      '<<': 2,
      '>>': 2,
      '<': 3,
      '>': 3,
      '+': 4,
      '-': 4,
      '*': 5,
      '/': 5,
      '//': 5,
      '%': 5,
      '^': 6,
      '!': 7,
    };
    return p[op] || 0;
  };
  const rightAssoc = (op: string) => op === '^' || op === '!';

  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    if (t.type === 'num') output.push(t);
    else if (t.type === 'var') {
      const lc = t.name.toLowerCase();
      if (lc in CONSTANTS) output.push({ type: 'num', value: CONSTANTS[lc] });
      else if (t.name in vars) output.push({ type: 'num', value: vars[t.name] });
      else throw new Error(`Unknown variable: "${t.name}". Use "${t.name} = value" to define it.`);
    } else if (t.type === 'fn') ops.push(t);
    else if (t.type === 'comma') {
      while (ops.length > 0 && !isLparenToken(ops[ops.length - 1])) output.push(ops.pop()!);
    } else if (t.type === 'op') {
      const top = ops[ops.length - 1];
      if (
        top &&
        isOpToken(top) &&
        ((rightAssoc(t.op) && prec(top.op) > prec(t.op)) ||
          (!rightAssoc(t.op) && prec(top.op) >= prec(t.op)))
      ) {
        output.push(ops.pop()!);
      }
      ops.push(t);
    } else if (t.type === 'lparen') ops.push(t);
    else if (t.type === 'rparen') {
      while (ops.length > 0 && !isLparenToken(ops[ops.length - 1])) output.push(ops.pop()!);
      if (ops.length === 0) throw new Error('Mismatched parentheses');
      ops.pop();
      const after = ops[ops.length - 1];
      if (after && isFnToken(after)) output.push(ops.pop()!);
    }
  }
  while (ops.length > 0) {
    const op = ops.pop()!;
    if (op.type === 'lparen' || op.type === 'rparen') throw new Error('Mismatched parentheses');
    output.push(op);
  }

  const stack: number[] = [];
  for (const t of output) {
    if (t.type === 'num') stack.push(t.value);
    else if (t.type === 'op') {
      if (t.op === '!') {
        const a = stack.pop()!;
        stack.push(FUNCTIONS.fact([a]));
      } else if (t.op === '%') {
        // Percentage: unary postfix (n%) or binary (a % b = a * b / 100)
        if (stack.length >= 2) {
          const b = stack.pop()!;
          const a = stack.pop()!;
          stack.push((a * b) / 100);
        } else if (stack.length === 1) {
          stack.push(stack.pop()! / 100);
        } else {
          throw new Error('Invalid percentage expression');
        }
      } else {
        const b = stack.pop()!;
        const a = stack.pop()!;
        switch (t.op) {
          case '+':
            stack.push(a + b);
            break;
          case '-':
            stack.push(a - b);
            break;
          case '*':
            stack.push(a * b);
            break;
          case '/':
            if (b === 0) throw new Error('Division by zero');
            stack.push(a / b);
            break;
          case '//':
            if (b === 0) throw new Error('Division by zero');
            stack.push(Math.floor(a / b));
            break;
          case '^':
            stack.push(Math.pow(a, b));
            break;
          case '<<':
            stack.push(Math.floor(a) << Math.floor(b));
            break;
          case '>>':
            stack.push(Math.floor(a) >> Math.floor(b));
            break;
          case '<':
            stack.push(a < b ? 1 : 0);
            break;
          case '>':
            stack.push(a > b ? 1 : 0);
            break;
          default:
            throw new Error(`Unknown operator: ${t.op}`);
        }
      }
    } else if (t.type === 'fn') {
      const fn = FUNCTIONS[t.name];
      if (!fn) throw new Error(`Unknown function: ${t.name}`);
      let argCount = 1;
      if (['min', 'max', 'sum', 'avg', 'prod', 'hypot'].includes(t.name))
        argCount = Math.max(2, Math.min(stack.length, 5));
      if (
        ['gcd', 'lcm', 'ncr', 'npr', 'rand', 'randint', 'mod', 'clamp', 'lerp', 'logb'].includes(
          t.name
        )
      )
        argCount = 2;
      if (['clamp', 'lerp'].includes(t.name)) argCount = 3;
      if (t.name === 'map') argCount = 5;
      if (
        [
          'sin',
          'cos',
          'tan',
          'asin',
          'acos',
          'atan',
          'sec',
          'csc',
          'cot',
          'asec',
          'acsc',
          'acot',
          'sinh',
          'cosh',
          'tanh',
          'asinh',
          'acosh',
          'atanh',
          'log',
          'ln',
          'log2',
          'sqrt',
          'cbrt',
          'abs',
          'floor',
          'ceil',
          'round',
          'trunc',
          'sign',
          'exp',
          'expm1',
          'deg',
          'rad',
          'dms',
          'fact',
          'exp',
        ].includes(t.name)
      )
        argCount = 1;
      if (
        [
          'mol',
          'atoms',
          'mass_from_mol',
          'celsius_to_kelvin',
          'kelvin_to_celsius',
          'fahrenheit_to_celsius',
          'celsius_to_fahrenheit',
          'ideal_gas_P',
          'ideal_gas_n',
          'ideal_gas_V',
        ].includes(t.name)
      )
        argCount = t.name.startsWith('ideal_gas')
          ? t.name === 'ideal_gas_P'
            ? 3
            : t.name === 'ideal_gas_n'
              ? 3
              : 3
          : 2;
      const args: number[] = [];
      for (let i = 0; i < argCount && stack.length > 0; i++) args.unshift(stack.pop()!);
      stack.push(fn(args));
    }
  }
  if (stack.length !== 1) throw new Error('Invalid expression');
  return stack[0];
}

// ═══════════════════════════════════════════════════════════════
//  AI ASSISTANT
// ═══════════════════════════════════════════════════════════════

interface AIResponse {
  type: string;
  content: string;
  steps?: string[];
}

const AI_PATTERNS: { pattern: RegExp; handler: (query: string, expr: string) => AIResponse }[] = [
  {
    pattern: /(?:derivative|derive|diff)\s+(?:of\s+)?(.+)/i,
    handler: (_query, expr) => {
      const e = expr.trim().toLowerCase();
      const rules: [RegExp, string | ((m: RegExpMatchArray) => string)][] = [
        [/^(\d+)$/, '0 (constant)'],
        [/^x$/, '1'],
        [/^(\d+)\s*\*?\s*x$/, (m) => `${m[1]}`],
        [
          /^(\d+)\s*\*?\s*x\^(\d+)$/,
          (m) => `${parseInt(m[1]) * parseInt(m[2])} * x^${parseInt(m[2]) - 1}`,
        ],
        [/sin\(x\)/, 'cos(x)'],
        [/cos\(x\)/, '-sin(x)'],
        [/tan\(x\)/, 'sec²(x)'],
        [/ln\(x\)/, '1/x'],
        [/e\^x/, 'e^x'],
        [/sqrt\(x\)/, '1/(2*sqrt(x))'],
      ];
      for (const [re, result] of rules) {
        const m = e.match(re);
        if (m) {
          const res = typeof result === 'string' ? result : result(m);
          return {
            type: 'derive',
            content: `d/dx(${expr}) = ${res}`,
            steps: [`Function: ${expr}`, 'Apply rule', `Result: ${res}`],
          };
        }
      }
      return {
        type: 'derive',
        content: `Derivative of ${expr}: try forms like x^n, sin(x), cos(x), e^x, ln(x)`,
      };
    },
  },
  {
    pattern: /(?:solve|find)\s+(?:for\s+)?(\w+)\s*:?\s*(.+)/i,
    handler: (query, _expr) => {
      const match = query.match(/(?:solve|find)\s+(?:for\s+)?(\w+)\s*:?\s*(.+)/i);
      if (!match) return { type: 'error', content: 'Could not parse' };
      const [, variable, eq] = match;
      const clean = eq.replace(/=/g, '-(') + ')';
      try {
        const y0 = evaluate(clean, { [variable]: 0 });
        const y1 = evaluate(clean, { [variable]: 1 });
        const a = y1 - y0,
          b = y0;
        if (Math.abs(a) < 1e-10)
          return { type: 'solve', content: `No solution (${variable} coeff = 0)` };
        return {
          type: 'solve',
          content: `${variable} = ${formatNum(-b / a)}`,
          steps: [
            `Eq: ${eq}`,
            `${a.toFixed(4)}${variable} + ${b.toFixed(4)} = 0`,
            `${variable} = ${formatNum(-b / a)}`,
          ],
        };
      } catch {
        return { type: 'solve', content: `Could not solve "${eq}"` };
      }
    },
  },
  {
    pattern: /(?:molar mass|mm|formula mass)\s+(?:of\s+)?(.+)/i,
    handler: (_query, expr) => {
      const formula = expr.trim().replace(/\s/g, '');
      try {
        const { mass, breakdown } = parseFormulaProper(formula);
        const parts = breakdown
          .map((b) => `${b.symbol}${b.count > 1 ? b.count : ''} = ${b.mass.toFixed(3)}`)
          .join(', ');
        return {
          type: 'chemistry',
          content: `M(${formula}) = ${mass.toFixed(3)} g/mol`,
          steps: [`Formula: ${formula}`, `Elements: ${parts}`, `Total: ${mass.toFixed(3)} g/mol`],
        };
      } catch (e: any) {
        return { type: 'chemistry', content: `Error: ${e.message}` };
      }
    },
  },
  {
    pattern: /(?:how many moles|moles of)\s+(.+?)\s+(?:in|from)\s+(.+)/i,
    handler: (query, _expr) => {
      const m = query.match(/(?:how many moles|moles of)\s+(.+?)\s+(?:in|from)\s+(.+)/i);
      if (!m) return { type: 'chemistry', content: 'Usage: moles of H2O in 36g' };
      const [, formula, massStr] = m;
      try {
        const { mass } = parseFormulaProper(formula.trim().replace(/\s/g, ''));
        const grams = parseFloat(massStr);
        const moles = grams / mass;
        return {
          type: 'chemistry',
          content: `${moles.toFixed(4)} mol of ${formula.trim()}`,
          steps: [
            `M(${formula.trim()}) = ${mass.toFixed(3)} g/mol`,
            `n = ${grams}g / ${mass.toFixed(3)} g/mol`,
            `n = ${moles.toFixed(4)} mol`,
          ],
        };
      } catch (e: any) {
        return { type: 'chemistry', content: `Error: ${e.message}` };
      }
    },
  },
  {
    pattern: /(?:simplify|reduce)\s+(.+)/i,
    handler: (_query, expr) => ({
      type: 'explain',
      content: `To simplify "${expr}", apply algebraic rules step by step.`,
      steps: [`Expr: ${expr}`, 'Evaluate', 'Check for common factors'],
    }),
  },
  {
    pattern: /(?:explain|how|what is|calculate|compute|evaluate)\s+(.+)/i,
    handler: (_query, expr) => ({
      type: 'explain',
      content: `Calculate "${expr}" in the calculator.`,
      steps: [`Parse: ${expr}`, 'Identify ops', 'Evaluate by precedence'],
    }),
  },
];

function askAI(query: string): AIResponse {
  for (const { pattern, handler } of AI_PATTERNS) {
    const m = query.match(pattern);
    if (m) return handler(query, m[1] || '');
  }
  return {
    type: 'general',
    content: `I can help with:\n• Math: "derivative of x^3"\n• Solve: "solve x: 2x+5=15"\n• Chemistry: "molar mass of C6H12O6"\n• Moles: "moles of H2O in 36g"`,
  };
}

function formatNum(n: number): string {
  if (!isFinite(n)) return n > 0 ? '∞' : n < 0 ? '-∞' : 'NaN';
  if (Math.abs(n) < 0.000001 || Math.abs(n) > 1e12) return n.toExponential(6);
  return parseFloat(n.toPrecision(12)).toString();
}

// ═══════════════════════════════════════════════════════════════
//  STORAGE
// ═══════════════════════════════════════════════════════════════

const SK = 'linuxos_calcpro';
const SV = 'linuxos_calcpro_vars';
const SA = 'linuxos_calcpro_ai';
const ST = 'linuxos_calcpro_trig';

interface CalcHistoryItem {
  id: string;
  expr: string;
  result: string;
  assignTo?: string;
  timestamp: number;
  error?: string;
}

// ═══════════════════════════════════════════════════════════════
//  COMPONENT
// ═══════════════════════════════════════════════════════════════

export default function CalculatorPro() {
  const [input, setInput] = useState('');
  const [trigMode, setTrigMode] = useState<'rad' | 'deg'>(() => {
    try {
      return (localStorage.getItem(ST) as 'rad' | 'deg') || 'rad';
    } catch {
      return 'rad';
    }
  });
  const [history, setHistory] = useState<CalcHistoryItem[]>(() => {
    try {
      const s = localStorage.getItem(SK);
      return s ? JSON.parse(s) : [];
    } catch {
      return [];
    }
  });
  const [vars, setVars] = useState<VarScope>(() => {
    try {
      const s = localStorage.getItem(SV);
      return s ? JSON.parse(s) : {};
    } catch {
      return {};
    }
  });
  const [aiQuery, setAiQuery] = useState('');
  const [aiHistory, setAiHistory] = useState<
    { query: string; response: AIResponse; timestamp: number }[]
  >(() => {
    try {
      const s = localStorage.getItem(SA);
      return s ? JSON.parse(s) : [];
    } catch {
      return [];
    }
  });
  const [showVars, setShowVars] = useState(true);
  const [showAI, setShowAI] = useState(true);
  const [showChem, setShowChem] = useState(false);
  const [chemFormula, setChemFormula] = useState('');
  const [chemResult, setChemResult] = useState<{
    mass: number;
    breakdown: { symbol: string; count: number; mass: number }[];
  } | null>(null);
  const [chemError, setChemError] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [selectedElement, setSelectedElement] = useState<Element | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    localStorage.setItem(SK, JSON.stringify(history));
  }, [history]);
  useEffect(() => {
    localStorage.setItem(SV, JSON.stringify(vars));
  }, [vars]);
  useEffect(() => {
    localStorage.setItem(SA, JSON.stringify(aiHistory));
  }, [aiHistory]);
  useEffect(() => {
    localStorage.setItem(ST, trigMode);
    TRIG_MODE = trigMode;
  }, [trigMode]);

  const calculate = useCallback(
    (expression?: string) => {
      const expr = expression ?? input;
      if (!expr.trim()) return;
      try {
        const parsed = parse(tokenize(expr));
        const result = evaluate(parsed.expr, vars);
        const formatted = formatNum(result);
        const item: CalcHistoryItem = {
          id: Date.now().toString(),
          expr: expr.trim(),
          result: formatted,
          assignTo: parsed.assignTo,
          timestamp: Date.now(),
        };
        if (parsed.assignTo) setVars((prev) => ({ ...prev, [parsed.assignTo!]: result }));
        setHistory((prev) => [item, ...prev].slice(0, 200));
        setInput('');
      } catch (e: any) {
        setHistory((prev) =>
          [
            {
              id: Date.now().toString(),
              expr: expr.trim(),
              result: '',
              error: e.message,
              timestamp: Date.now(),
            },
            ...prev,
          ].slice(0, 200)
        );
      }
    },
    [input, vars]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') calculate();
    if (e.key === 'ArrowUp') {
      const items = history.filter((h) => !h.error);
      if (items.length > 0) setInput(items[0].expr);
    }
  };

  const askAIHelper = () => {
    if (!aiQuery.trim()) return;
    const response = askAI(aiQuery);
    setAiHistory((prev) =>
      [{ query: aiQuery, response, timestamp: Date.now() }, ...prev].slice(0, 50)
    );
    setAiQuery('');
  };

  const insertToInput = (text: string) => {
    setInput((prev) => {
      const needsSpace = prev.length > 0 && !prev.endsWith(' ');
      return prev + (needsSpace ? ' ' : '') + text;
    });
    inputRef.current?.focus();
  };

  const copyResult = (item: CalcHistoryItem) => {
    navigator.clipboard.writeText(item.result);
    setCopiedId(item.id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  const exportSession = () => {
    const blob = new Blob(
      [JSON.stringify({ history, vars, exported: new Date().toISOString() }, null, 2)],
      { type: 'application/json' }
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `calc-session-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearAll = () => {
    setHistory([]);
    setVars({});
  };
  const deleteVar = (name: string) =>
    setVars((prev) => {
      const v = { ...prev };
      delete v[name];
      return v;
    });

  const calcChem = () => {
    if (!chemFormula.trim()) return;
    try {
      const r = parseFormulaProper(chemFormula.trim().replace(/\s/g, ''));
      setChemResult(r);
      setChemError('');
    } catch (e: any) {
      setChemResult(null);
      setChemError(e.message);
    }
  };

  const suggestions = useMemo(() => {
    if (!input.trim()) return [] as string[];
    const all = [...Object.keys(FUNCTIONS), ...Object.keys(CONSTANTS), ...Object.keys(vars)];
    const lastWord =
      input
        .trim()
        .split(/[\s+\-*/()^%]+/)
        .pop() || '';
    if (lastWord.length < 1) return [];
    return all
      .filter(
        (n) =>
          n.toLowerCase().startsWith(lastWord.toLowerCase()) &&
          n.toLowerCase() !== lastWord.toLowerCase()
      )
      .slice(0, 5);
  }, [input, vars]);

  const categoryColors: Record<string, string> = {
    nonmetal: 'text-green-300',
    noble: 'text-cyan-300',
    alkali: 'text-red-300',
    alkaline: 'text-orange-300',
    metalloid: 'text-yellow-300',
    halogen: 'text-emerald-300',
    transition: 'text-blue-300',
    'post-transition': 'text-purple-300',
    actinide: 'text-pink-300',
  };

  return (
    <div className="w-full h-full flex bg-[#0d1926] text-blue-100/80">
      {/* MAIN PANEL */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2 px-3 py-2 border-b border-blue-500/10">
          <Calculator size={16} className="text-blue-400" />
          <h2 className="text-sm text-blue-200 font-semibold">AI Calculator</h2>
          <div className="flex-1" />
          {/* Trig mode toggle */}
          <button
            onClick={() => setTrigMode((p) => (p === 'rad' ? 'deg' : 'rad'))}
            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] bg-blue-500/10 hover:bg-blue-500/20 transition-colors"
            title="Toggle deg/rad"
          >
            {trigMode === 'rad' ? (
              <>
                <Binary size={10} /> RAD
              </>
            ) : (
              <>
                <ToggleRight size={10} /> DEG
              </>
            )}
          </button>
          <button
            onClick={() => setShowVars(!showVars)}
            className={`px-2 py-1 rounded-lg text-[10px] transition-colors flex items-center gap-1 ${showVars ? 'bg-blue-500/20 text-blue-200' : 'text-blue-300/30 hover:text-blue-200'}`}
          >
            <Variable size={10} /> Vars
          </button>
          <button
            onClick={() => setShowChem(!showChem)}
            className={`px-2 py-1 rounded-lg text-[10px] transition-colors flex items-center gap-1 ${showChem ? 'bg-green-500/20 text-green-200' : 'text-blue-300/30 hover:text-blue-200'}`}
          >
            <FlaskConical size={10} /> Chem
          </button>
          <button
            onClick={() => setShowAI(!showAI)}
            className={`px-2 py-1 rounded-lg text-[10px] transition-colors flex items-center gap-1 ${showAI ? 'bg-purple-500/20 text-purple-200' : 'text-blue-300/30 hover:text-blue-200'}`}
          >
            <Sparkles size={10} /> AI
          </button>
          <button
            onClick={exportSession}
            className="p-1 rounded hover:bg-blue-500/20 text-blue-300/40 transition-colors"
            title="Export"
          >
            <Download size={12} />
          </button>
          <button
            onClick={clearAll}
            className="p-1 rounded hover:bg-red-500/20 text-blue-300/40 hover:text-red-400 transition-colors"
            title="Clear"
          >
            <Trash2 size={12} />
          </button>
        </div>

        {/* CHEMISTRY PANEL */}
        {showChem && (
          <div className="border-b border-blue-500/10 bg-[#0a1420] p-3 max-h-48 overflow-y-auto">
            <div className="flex items-center gap-2 mb-2">
              <FlaskConical size={14} className="text-green-400" />
              <span className="text-xs text-green-200 font-semibold">Chemistry Tools</span>
            </div>
            <div className="flex gap-2 mb-2">
              <input
                value={chemFormula}
                onChange={(e) => setChemFormula(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && calcChem()}
                placeholder="Enter formula: H2O, C6H12O6, Ca(NO3)2..."
                className="flex-1 bg-[#162032] border border-green-500/15 rounded-lg px-2 py-1 text-xs outline-none focus:border-green-500/30 font-mono"
              />
              <button
                onClick={calcChem}
                className="px-2 py-1 rounded-lg bg-green-500/15 text-green-300 text-xs hover:bg-green-500/25 transition-colors"
              >
                <Atom size={12} />
              </button>
            </div>
            {chemError && <div className="text-[10px] text-red-400/70 mb-1">{chemError}</div>}
            {chemResult && (
              <div className="flex gap-3 mb-2">
                <div className="text-xs">
                  <span className="text-green-300/50">M = </span>
                  <span className="text-green-200 font-mono font-semibold">
                    {chemResult.mass.toFixed(3)}
                  </span>
                  <span className="text-green-300/30"> g/mol</span>
                </div>
                <div className="flex gap-1 flex-wrap">
                  {chemResult.breakdown.map((b) => (
                    <button
                      key={b.symbol}
                      onClick={() => setSelectedElement(PERIODIC_TABLE[b.symbol] || null)}
                      className="text-[10px] px-1.5 py-0.5 rounded bg-green-500/10 text-green-300/60 hover:bg-green-500/20 transition-colors"
                    >
                      {b.symbol}
                      {b.count > 1 ? b.count : ''}: {b.mass.toFixed(2)}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {/* Element lookup */}
            <div className="flex gap-1 flex-wrap">
              {Object.values(PERIODIC_TABLE).map((el) => (
                <button
                  key={el.symbol}
                  onClick={() => {
                    setSelectedElement(el);
                    insertToInput(el.symbol);
                  }}
                  className={`w-8 h-8 rounded text-[10px] font-mono font-semibold bg-[#162032] border border-blue-500/10 hover:border-blue-500/30 transition-all ${categoryColors[el.category] || 'text-blue-300'}`}
                  title={`${el.name} (${el.mass})`}
                >
                  {el.symbol}
                </button>
              ))}
            </div>
            {selectedElement && (
              <div className="mt-2 p-2 rounded-lg bg-[#162032] border border-blue-500/10 text-[10px]">
                <span className="text-blue-200 font-semibold">{selectedElement.name}</span>
                <span className="text-blue-300/30 ml-2">#{selectedElement.number}</span>
                <span className="text-blue-300/30 ml-2">{selectedElement.mass} u</span>
                <span className="text-blue-300/30 ml-2">
                  shells: {selectedElement.electrons.join(',')}
                </span>
              </div>
            )}
          </div>
        )}

        {/* HISTORY */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1">
          {history.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-blue-400/20 gap-3">
              <FunctionSquare size={48} />
              <div className="text-xs text-center max-w-[300px] space-y-0.5">
                <p>sin(45) · sec(30) · cosh(1.5)</p>
                <p>x = 5 · x^2 + sqrt(16)</p>
                <p>ncr(52,5) · gcd(48,18)</p>
                <p>mol(18, H2O) · ideal_gas_P(1, 22.4, 273)</p>
              </div>
            </div>
          )}
          {history.map((item) => (
            <div
              key={item.id}
              onClick={() => insertToInput(item.result)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-blue-500/5 transition-all cursor-pointer group"
            >
              <ChevronRight
                size={12}
                className={`flex-shrink-0 ${item.error ? 'text-red-400' : 'text-blue-400/30'}`}
              />
              <div className="flex-1 min-w-0">
                <div className="text-xs font-mono text-blue-200/60 truncate">
                  {item.assignTo && (
                    <span className="text-yellow-400/60 mr-1">{item.assignTo} =</span>
                  )}
                  {item.expr}
                </div>
                {item.error ? (
                  <div className="text-[10px] text-red-400/60">{item.error}</div>
                ) : (
                  <div className="text-sm font-mono text-blue-100">{item.result}</div>
                )}
              </div>
              {!item.error && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    copyResult(item);
                  }}
                  className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-blue-500/20 text-blue-300/30 hover:text-blue-300 transition-all"
                >
                  {copiedId === item.id ? (
                    <Check size={10} className="text-green-400" />
                  ) : (
                    <Copy size={10} />
                  )}
                </button>
              )}
            </div>
          ))}
        </div>

        {/* VARIABLES BAR */}
        {showVars && Object.keys(vars).length > 0 && (
          <div className="border-t border-blue-500/10 px-3 py-2 flex gap-2 flex-wrap max-h-20 overflow-y-auto">
            {Object.entries(vars).map(([name, val]) => (
              <button
                key={name}
                onClick={() => insertToInput(name)}
                className="flex items-center gap-1 px-2 py-0.5 rounded bg-blue-500/10 hover:bg-blue-500/20 transition-colors group"
              >
                <span className="text-[10px] text-blue-200/60 font-mono">
                  {name} = {formatNum(val)}
                </span>
                <X
                  size={8}
                  className="text-blue-400/20 hover:text-red-400"
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteVar(name);
                  }}
                />
              </button>
            ))}
          </div>
        )}

        {/* INPUT */}
        <div className="border-t border-blue-500/10 p-3">
          {suggestions.length > 0 && (
            <div className="flex gap-1 mb-1 flex-wrap">
              {suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setInput(input.replace(/[^\s]*$/, '') + s);
                    inputRef.current?.focus();
                  }}
                  className="px-1.5 py-0.5 rounded bg-blue-500/10 text-[10px] text-blue-300/50 hover:text-blue-200 hover:bg-blue-500/20 transition-colors font-mono"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Expression (${trigMode.toUpperCase()})...`}
              className="flex-1 bg-[#162032] border border-blue-500/15 rounded-xl px-3 py-2 text-xs font-mono outline-none focus:border-blue-500/30 transition-colors"
            />
            <button
              onClick={() => calculate()}
              className="px-3 py-2 rounded-xl bg-blue-500/20 text-blue-200 hover:bg-blue-500/30 transition-colors"
            >
              <Play size={14} />
            </button>
          </div>
          {/* Quick buttons */}
          <div className="flex gap-1 mt-2 flex-wrap">
            {[
              'sin(',
              'cos(',
              'tan(',
              'asin(',
              'sec(',
              'csc(',
              'sqrt(',
              'log(',
              'ln(',
              'π',
              'e',
              '^',
              'fact(',
              'ncr(',
              'rand(',
              'deg(',
              'rad(',
              'mol(',
              'ideal_gas_P(',
            ].map((fn) => (
              <button
                key={fn}
                onClick={() => insertToInput(fn)}
                className="px-1.5 py-0.5 rounded bg-[#162032] hover:bg-blue-500/10 text-[10px] text-blue-300/40 hover:text-blue-200 transition-colors font-mono"
              >
                {fn}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* AI PANEL */}
      {showAI && (
        <div className="w-64 border-l border-blue-500/10 flex flex-col bg-[#0a1420]">
          <div className="flex items-center gap-2 px-3 py-2 border-b border-blue-500/10">
            <Sparkles size={14} className="text-purple-400" />
            <span className="text-xs text-purple-200 font-semibold">AI Assistant</span>
            <div className="flex-1" />
            <button
              onClick={() => setAiHistory([])}
              className="p-0.5 rounded hover:bg-red-500/20 text-blue-300/20 hover:text-red-400"
            >
              <Trash2 size={10} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {aiHistory.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-blue-400/15 gap-2 text-center p-4">
                <Lightbulb size={32} />
                <p className="text-[10px]">Ask me anything!</p>
                <div className="text-[9px] text-blue-400/10 space-y-0.5">
                  <p>&quot;derivative of x^3&quot;</p>
                  <p>&quot;solve x: 3x+7=22&quot;</p>
                  <p>&quot;molar mass of C6H12O6&quot;</p>
                  <p>&quot;moles of H2O in 36g&quot;</p>
                </div>
              </div>
            )}
            {aiHistory.map((item, i) => (
              <div key={i} className="space-y-1">
                <div className="text-[10px] text-blue-300/30 bg-blue-500/5 rounded-lg px-2 py-1">
                  {item.query}
                </div>
                <div className="bg-purple-500/5 rounded-lg p-2 border border-purple-500/5">
                  <div className="text-[11px] text-blue-200/70 whitespace-pre-wrap">
                    {item.response.content}
                  </div>
                  {item.response.steps && (
                    <div className="mt-1 space-y-0.5">
                      {item.response.steps.map((step, si) => (
                        <div
                          key={si}
                          className="flex items-start gap-1 text-[10px] text-blue-300/40"
                        >
                          <span className="text-purple-400/30 mt-0.5">{si + 1}.</span>
                          <span className="font-mono">{step}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="border-t border-blue-500/10 p-2">
            <div className="flex gap-1">
              <input
                value={aiQuery}
                onChange={(e) => setAiQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && askAIHelper()}
                placeholder="Ask AI..."
                className="flex-1 bg-[#162032] border border-purple-500/15 rounded-lg px-2 py-1.5 text-[10px] outline-none focus:border-purple-500/30"
              />
              <button
                onClick={askAIHelper}
                className="p-1.5 rounded-lg bg-purple-500/15 text-purple-300 hover:bg-purple-500/25 transition-colors"
              >
                <Sparkles size={12} />
              </button>
            </div>
            <div className="flex gap-1 mt-1 flex-wrap">
              {[
                'derivative of x^2',
                'solve x: 3x+7=22',
                'molar mass of C6H12O6',
                'moles of H2O in 36g',
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => setAiQuery(q)}
                  className="px-1.5 py-0.5 rounded bg-[#162032] text-[9px] text-blue-300/30 hover:text-blue-200/60 transition-colors truncate max-w-[80px]"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
