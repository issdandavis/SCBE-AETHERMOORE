'use strict';

const crypto = require('node:crypto');

const MU0 = 4 * Math.PI * 1e-7;
const COPPER_RHO = 1.724e-8;

// Resistivity (ohm-m, ~20C) + density (kg/m^3) for known conductors, so the
// NAMED material actually drives resistance/power/skin-depth — not just a label.
const CONDUCTORS = {
  copper: { name: 'copper', rho: 1.724e-8, density: 8960 },
  silver: { name: 'silver', rho: 1.59e-8, density: 10490 },
  gold: { name: 'gold', rho: 2.44e-8, density: 19300 },
  aluminum: { name: 'aluminum', rho: 2.82e-8, density: 2700 },
  aluminium: { name: 'aluminum', rho: 2.82e-8, density: 2700 },
  tungsten: { name: 'tungsten', rho: 5.6e-8, density: 19250 },
  nichrome: { name: 'nichrome', rho: 1.1e-6, density: 8400 },
  iron: { name: 'iron', rho: 9.71e-8, density: 7874 },
};

function detectConductor(concept, body) {
  const explicit = String((body && body.conductor) || '').trim().toLowerCase();
  if (explicit && CONDUCTORS[explicit]) return CONDUCTORS[explicit];
  const lower = String(concept || '').toLowerCase();
  for (const key of Object.keys(CONDUCTORS)) {
    if (lower.includes(key)) return CONDUCTORS[key];
  }
  return CONDUCTORS.copper;
}

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

function num(value, fallback, min, max) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.max(min, Math.min(max, parsed));
}

// Like num(), but records when a value was missing (defaulted) or out-of-range
// (clamped), so the bench can tell the user exactly which variables it assumed.
function numA(body, key, fallback, min, max, assumed) {
  const raw = body ? body[key] : undefined;
  const parsed = Number(raw);
  if (raw === undefined || raw === null || raw === '' || !Number.isFinite(parsed)) {
    assumed.push(`${key} = ${fallback} (assumed default)`);
    return fallback;
  }
  const clamped = Math.max(min, Math.min(max, parsed));
  if (clamped !== parsed) assumed.push(`${key} = ${clamped} (clamped from ${parsed})`);
  return clamped;
}

function materialsFor(text, conductor) {
  const lower = String(text || '').toLowerCase();
  const wire = `enameled ${(conductor && conductor.name) || 'copper'} magnet wire`;
  const stack = [
    { layer: 'core', material: lower.includes('quartz') ? 'quartz tube' : 'borosilicate or quartz glass tube', role: 'optical/mechanical path' },
    { layer: 'carbon skin', material: 'commercial graphene film, CNT film, carbon veil, or pyrolytic graphite sheet', role: 'conductive coupling layer' },
    { layer: 'coil', material: wire, role: 'field generation and signal winding' },
    { layer: 'flux guide', material: 'split ferrite sleeve or soft magnetic segments', role: 'shape magnetic flux around the tube' },
    { layer: 'insulation', material: 'polyimide tape or low-outgassing dielectric wrap', role: 'separate conductive layers' },
  ];
  if (lower.includes('space') || lower.includes('vacuum')) {
    stack.push({ layer: 'space screen', material: 'low-outgassing adhesive and coupon-tested coatings', role: 'vacuum/thermal compatibility' });
  }
  return stack;
}

function compute(body, conductor) {
  const assumed = [];
  const lengthMm = numA(body, 'length_mm', 120, 10, 2000, assumed);
  const radiusMm = numA(body, 'radius_mm', 5, 0.5, 100, assumed);
  const turns = Math.round(numA(body, 'turns', 180, 1, 5000, assumed));
  const currentA = numA(body, 'current_a', 0.35, 0.001, 20, assumed);
  const wireDiameterMm = numA(body, 'wire_diameter_mm', 0.2, 0.03, 5, assumed);
  const frequencyHz = numA(body, 'frequency_hz', 1000, 0, 5e6, assumed);
  const muRelative = numA(body, 'mu_relative', 1, 1, 5000, assumed);
  const nCore = numA(body, 'n_core', 1.46, 1, 4, assumed);
  const nClad = numA(body, 'n_clad', 1.44, 1, 4, assumed);
  const rho = conductor.rho;
  const lengthM = lengthMm / 1000;
  const radiusM = radiusMm / 1000;
  const wireDiameterM = wireDiameterMm / 1000;
  const circumference = 2 * Math.PI * radiusM;
  const wireLengthM = Math.max(circumference * turns, lengthM);
  const wireArea = Math.PI * Math.pow(wireDiameterM / 2, 2);
  const resistanceOhm = rho * wireLengthM / wireArea;
  const powerW = currentA * currentA * resistanceOhm;
  const bTesla = MU0 * muRelative * turns * currentA / lengthM;
  const skinDepthM = frequencyHz > 0 ? Math.sqrt((2 * rho) / (2 * Math.PI * frequencyHz * MU0)) : null;
  const opticalNA = Math.sqrt(Math.max(0, nCore * nCore - nClad * nClad));
  return {
    conductor: conductor.name,
    conductor_resistivity_ohm_m: rho,
    inputs: {
      length_mm: lengthMm, radius_mm: radiusMm, turns, current_a: currentA,
      wire_diameter_mm: wireDiameterMm, frequency_hz: frequencyHz, mu_relative: muRelative,
      n_core: nCore, n_clad: nClad, conductor: conductor.name,
    },
    assumed,
    estimates: {
      solenoid_field_t: Number(bTesla.toPrecision(5)),
      solenoid_field_mt: Number((bTesla * 1000).toPrecision(5)),
      wire_length_m: Number(wireLengthM.toPrecision(5)),
      coil_resistance_ohm: Number(resistanceOhm.toPrecision(5)),
      coil_power_w: Number(powerW.toPrecision(5)),
      skin_depth_mm: skinDepthM === null ? null : Number((skinDepthM * 1000).toPrecision(5)),
      optical_na_estimate: Number(opticalNA.toPrecision(5)),
    },
  };
}

function flags(calc) {
  const out = [];
  if (calc.estimates.coil_power_w > 200) {
    out.push('Non-physical for a bench tube: coil power exceeds ~200 W. Treat these inputs as out of range, not a real design point.');
  } else if (calc.estimates.coil_power_w > 5) {
    out.push('Thermal risk: coil power is high for a small tube. Reduce current, turns, or duty cycle.');
  }
  if (calc.estimates.solenoid_field_mt > 100) out.push('Magnetic field is high enough to require fixture, sensor, and heating review.');
  if (calc.inputs.frequency_hz > 100000) out.push('High-frequency drive: check skin depth, parasitic capacitance, shielding, and measurement bandwidth.');
  if (calc.assumed && calc.assumed.length) {
    out.push(`Assumed/clamped ${calc.assumed.length} input(s) — see math.assumed (e.g. ${calc.assumed[0]}).`);
  }
  if (!out.length) out.push('First-pass estimates are within a bench-testable range; validate with low-voltage current limiting.');
  return out;
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ ok: false, error: 'POST required' });

  try {
    const body = await readBody(req);
    const concept = String(body.concept || 'glass tube with carbon layer, copper coil, and ferrite flux guide').trim();
    const conductor = detectConductor(concept, body);
    const calc = compute(body, conductor);
    const result = {
      ok: true,
      schema_version: 'aethermoore_ai_materials_bench_v1',
      product: 'AI Materials Bench',
      receipt_id: `matbench_${sha(JSON.stringify({ concept, inputs: calc.inputs })).slice(0, 16)}`,
      concept,
      architecture: {
        name: 'magneto-optic composite tube sleeve',
        stack: materialsFor(concept, conductor),
        purpose: 'model a glass/fiber tube with conductive carbon skin, coil winding, magnetic flux shaping, and optical lane.',
      },
      math: calc,
      risk_flags: flags(calc),
      visual_stage: {
        panels: ['cross-section', 'field lines', 'thermal lane', 'optical lane', 'receipt'],
        draw_hints: ['tube core', 'carbon sleeve', 'copper winding', 'ferrite segments', 'light path'],
      },
      next_build: [
        'Make a coupon-scale drawing before buying parts.',
        'Use purchased films/wires/tubes with datasheets for the first prototype.',
        'Measure coil resistance before energizing.',
        'Start with current-limited low-voltage tests and log field/heat/optical readings.',
      ],
      sellable_output: {
        offer: 'Visual material-stack model with field, heat, optical estimates, risk flags, and receipt.',
        starter_price: '$49 concept report or $199 prototype worksheet pack',
      },
    };
    return res.status(200).json(result);
  } catch (error) {
    return res.status(500).json({ ok: false, error: error && error.message ? error.message : String(error) });
  }
};
