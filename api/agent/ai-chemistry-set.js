'use strict';

const crypto = require('node:crypto');

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

function readBody(req, maxBytes = 12000) {
  if (req.body && typeof req.body === 'object') return Promise.resolve(req.body);
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', (chunk) => {
      raw += chunk;
      if (raw.length > maxBytes) {
        reject(new Error('request body too large'));
        req.destroy();
      }
    });
    req.on('end', () => {
      if (!raw.trim()) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch (error) {
        reject(error);
      }
    });
    req.on('error', reject);
  });
}

function sha(value) {
  return crypto.createHash('sha256').update(String(value)).digest('hex');
}

function gcd(a, b) {
  let x = Math.abs(Number(a));
  let y = Math.abs(Number(b));
  while (y) [x, y] = [y, x % y];
  return x || 1;
}

function lcm(a, b) {
  return Math.abs(Number(a * b)) / gcd(a, b);
}

function fraction(n, d = 1) {
  if (d === 0) throw new Error('division by zero');
  let num = Number(n);
  let den = Number(d);
  if (den < 0) {
    num = -num;
    den = -den;
  }
  const g = gcd(num, den);
  return { n: num / g, d: den / g };
}

function fadd(a, b) { return fraction(a.n * b.d + b.n * a.d, a.d * b.d); }
function fsub(a, b) { return fraction(a.n * b.d - b.n * a.d, a.d * b.d); }
function fmul(a, b) { return fraction(a.n * b.n, a.d * b.d); }
function fdiv(a, b) { return fraction(a.n * b.d, a.d * b.n); }
function fiszero(a) { return a.n === 0; }

function parseFormula(formula) {
  const counts = {};
  const input = String(formula || '').trim();
  if (!/^[A-Z][A-Za-z0-9()]*$/.test(input)) throw new Error(`unsupported formula: ${input}`);
  const stack = [counts];
  let i = 0;
  while (i < input.length) {
    const char = input[i];
    if (char === '(') {
      stack.push({});
      i += 1;
      continue;
    }
    if (char === ')') {
      i += 1;
      const multMatch = input.slice(i).match(/^\d+/);
      const mult = multMatch ? Number(multMatch[0]) : 1;
      if (multMatch) i += multMatch[0].length;
      const group = stack.pop();
      if (!group || stack.length === 0) throw new Error(`unbalanced formula: ${input}`);
      const target = stack[stack.length - 1];
      for (const [el, count] of Object.entries(group)) target[el] = (target[el] || 0) + count * mult;
      continue;
    }
    const match = input.slice(i).match(/^([A-Z][a-z]?)(\d*)/);
    if (!match) throw new Error(`unsupported formula: ${input}`);
    const [, element, rawCount] = match;
    const count = rawCount ? Number(rawCount) : 1;
    const target = stack[stack.length - 1];
    target[element] = (target[element] || 0) + count;
    i += match[0].length;
  }
  if (stack.length !== 1) throw new Error(`unbalanced formula: ${input}`);
  return counts;
}

function parseEquation(text) {
  const match = String(text || '').match(/(.+?)(?:->|=>|=)(.+)/);
  if (!match) return null;
  const side = (value) => value.split('+').map((part) => part.trim().replace(/^\d+\s*/, '')).filter(Boolean);
  const reactants = side(match[1]);
  const products = side(match[2]);
  if (!reactants.length || !products.length) return null;
  return { reactants, products };
}

function rref(matrix) {
  const rows = matrix.map((row) => row.map((value) => fraction(value.n, value.d)));
  const pivots = [];
  let lead = 0;
  for (let r = 0; r < rows.length && lead < rows[0].length; r += 1) {
    let i = r;
    while (i < rows.length && fiszero(rows[i][lead])) i += 1;
    if (i === rows.length) {
      lead += 1;
      r -= 1;
      continue;
    }
    [rows[i], rows[r]] = [rows[r], rows[i]];
    const lv = rows[r][lead];
    rows[r] = rows[r].map((value) => fdiv(value, lv));
    for (let j = 0; j < rows.length; j += 1) {
      if (j === r) continue;
      const factor = rows[j][lead];
      if (!fiszero(factor)) rows[j] = rows[j].map((value, col) => fsub(value, fmul(factor, rows[r][col])));
    }
    pivots.push(lead);
    lead += 1;
  }
  return { rows, pivots };
}

function balanceEquation(reactants, products) {
  const species = reactants.concat(products);
  const signs = species.map((_, index) => (index < reactants.length ? 1 : -1));
  const compositions = species.map(parseFormula);
  const elements = Array.from(new Set(compositions.flatMap((comp) => Object.keys(comp)))).sort();
  const matrix = elements.map((element) => species.map((_, col) => fraction((compositions[col][element] || 0) * signs[col])));
  const { rows, pivots } = rref(matrix);
  const freeCols = species.map((_, index) => index).filter((index) => !pivots.includes(index));
  if (freeCols.length !== 1) throw new Error('equation needs one independent balance; split sub-reactions or add species');
  const free = freeCols[0];
  const solution = species.map(() => fraction(0));
  solution[free] = fraction(1);
  for (let r = 0; r < pivots.length; r += 1) solution[pivots[r]] = fmul(fraction(-1), rows[r][free]);
  let den = 1;
  for (const value of solution) den = lcm(den, value.d);
  let ints = solution.map((value) => value.n * (den / value.d));
  if (ints.some((value) => value === 0)) throw new Error('zero coefficient balance rejected');
  if (ints.some((value) => value < 0)) ints = ints.map((value) => -value);
  const divisor = ints.reduce((acc, value) => gcd(acc, value), Math.abs(ints[0]));
  ints = ints.map((value) => value / divisor);
  if (ints.some((value) => value <= 0)) throw new Error('positive balance not found');
  return ints;
}

function formatEquation(coeffs, reactants, products) {
  const fmt = (coeff, formula) => (coeff === 1 ? formula : `${coeff}${formula}`);
  const left = reactants.map((formula, index) => fmt(coeffs[index], formula)).join(' + ');
  const right = products.map((formula, index) => fmt(coeffs[index + reactants.length], formula)).join(' + ');
  return `${left} -> ${right}`;
}

function hazardNotes(input) {
  const lower = String(input || '').toLowerCase();
  const notes = [];
  if (/\b(cl2|chlorine|cyanide|hcn|phosgene|sarin|weapon|explosive|toxic gas)\b/.test(lower)) {
    notes.push('Hazard boundary: keep this in analysis/safety mode; do not provide synthesis instructions.');
  }
  if (/\bmake|synthesize|cook|weaponize|dose\b/.test(lower)) {
    notes.push('Assistant mode should redirect from procedural synthesis to safe explanation, balancing, or risk screening.');
  }
  return notes.length ? notes : ['Educational/math mode. No procedural synthesis requested.'];
}

function assistantText(input, balanced) {
  if (balanced) {
    return [
      'I balanced the equation by conserving atoms on both sides.',
      'Use the stage view to show reactants, coefficients, products, and the conservation receipt.',
      'For deeper chemistry, route the same equation into the Python reaction packet engine.'
    ];
  }
  return [
    'I can act as the lab assistant: ask for an equation, explain atoms, or prepare a safe practice card.',
    'Try: C3H8 + O2 -> CO2 + H2O',
    'The saleable output is a visual lesson plus a machine-readable receipt.'
  ];
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ ok: false, error: 'POST required' });

  try {
    const body = await readBody(req);
    const input = String(body.input || '').trim();
    const level = String(body.level || 'learner').toLowerCase();
    if (!input) return res.status(400).json({ ok: false, error: 'input is required' });
    if (input.length > 2000) return res.status(400).json({ ok: false, error: 'input is too long' });

    const equation = parseEquation(input);
    let balance = null;
    let mathError = null;
    if (equation) {
      try {
        const coeffs = balanceEquation(equation.reactants, equation.products);
        balance = {
          reactants: equation.reactants,
          products: equation.products,
          coefficients: coeffs,
          balanced_equation: formatEquation(coeffs, equation.reactants, equation.products),
          math: 'exact rational nullspace over the element conservation matrix',
        };
      } catch (error) {
        mathError = error && error.message ? error.message : String(error);
      }
    }

    const result = {
      ok: true,
      schema_version: 'aethermoore_ai_chemistry_set_v1',
      receipt_id: `chemset_${sha(`${level}|${input}`).slice(0, 16)}`,
      product: 'AI Chemistry Set',
      level,
      input,
      assistant: assistantText(input, Boolean(balance)),
      visual_stage: {
        scene: 'medieval-inspired alchemy workbench with modern AI assistant panel',
        panels: ['bench', 'flasks', 'equation slate', 'assistant', 'receipt'],
        style_boundary: 'inspired by historical alchemy labs and tactile RPG workbenches; not a clone of any game UI',
      },
      balance,
      math_error: mathError,
      hazard_notes: hazardNotes(input),
      deep_math_lane: {
        repo_modules: ['python/scbe/reaction_balance.py', 'python/scbe/reaction_language.py', 'python/scbe/reaction_harness.py'],
        cli_hint: equation ? `python scripts/reaction_cli.py balance --reactants ${equation.reactants.join(',')} --products ${equation.products.join(',')}` : 'python scripts/reaction_cli.py ask "balance propane combustion"',
      },
      sellable_output: {
        offer: 'Interactive AI chemistry lesson, visual balanced equation, safety notes, and JSON receipt.',
        starter_price: '$19 lesson export or $99 classroom/lab pack',
        subscription: '$29-$99/month for saved lessons, assistant rooms, and printable packs',
      },
    };
    return res.status(200).json(result);
  } catch (error) {
    return res.status(500).json({ ok: false, error: error && error.message ? error.message : String(error) });
  }
};
