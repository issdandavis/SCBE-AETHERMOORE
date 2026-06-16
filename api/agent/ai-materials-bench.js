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

// Rough hobbyist-scale costs so the bench can COST a build, not just describe it.
// Ranges in USD, not supplier quotes. Magnet wire is priced per metre by conductor.
const WIRE_COST_PER_M = {
  copper: 0.12, silver: 1.1, gold: 9, aluminum: 0.09, tungsten: 0.45, nichrome: 0.3, iron: 0.1,
};
const PART_COSTS = {
  tube: { label: 'Borosilicate or quartz tube', low: 8, high: 26 },
  carbon: { label: 'Graphene / CNT / pyrolytic-graphite film', low: 11, high: 32 },
  ferrite: { label: 'Split ferrite sleeve or soft-magnetic segments', low: 5, high: 18 },
  insulation: { label: 'Polyimide (Kapton) tape', low: 6, high: 12 },
  hookup: { label: 'Leads, lugs, current-limited supply hookup', low: 7, high: 20 },
};

function round2(n) { return Math.round(n * 100) / 100; }
function round3(n) { return Math.round(n * 1000) / 1000; }

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

// A costed parts list derived from the computed wire length + the chosen conductor.
function billOfMaterials(calc, conductor) {
  const wireLen = calc.estimates.wire_length_m;
  const perM = WIRE_COST_PER_M[conductor.name] || 0.12;
  const items = [
    {
      part: `${conductor.name} enameled magnet wire (~${wireLen} m + winding margin)`,
      qty: '1 spool',
      est_usd_low: round2(Math.max(9, wireLen * perM)),
      est_usd_high: round2(Math.max(15, wireLen * perM * 1.9)),
    },
    { part: `${PART_COSTS.tube.label} (~${calc.inputs.length_mm} mm)`, qty: '1', est_usd_low: PART_COSTS.tube.low, est_usd_high: PART_COSTS.tube.high },
    { part: PART_COSTS.carbon.label, qty: '1 sheet/wrap', est_usd_low: PART_COSTS.carbon.low, est_usd_high: PART_COSTS.carbon.high },
    { part: PART_COSTS.ferrite.label, qty: '1 set', est_usd_low: PART_COSTS.ferrite.low, est_usd_high: PART_COSTS.ferrite.high },
    { part: PART_COSTS.insulation.label, qty: '1 roll', est_usd_low: PART_COSTS.insulation.low, est_usd_high: PART_COSTS.insulation.high },
    { part: PART_COSTS.hookup.label, qty: '1 set', est_usd_low: PART_COSTS.hookup.low, est_usd_high: PART_COSTS.hookup.high },
  ];
  const low = round2(items.reduce((sum, item) => sum + item.est_usd_low, 0));
  const high = round2(items.reduce((sum, item) => sum + item.est_usd_high, 0));
  return {
    currency: 'USD',
    items,
    estimated_total_low: low,
    estimated_total_high: high,
    note: 'Rough hobbyist-scale estimates, not supplier quotes. Cost varies with grade, supplier, and quantity. A current-limited bench supply is assumed already on hand.',
  };
}

// Derive a real operating envelope: voltage at the set current, and the max
// continuous current that keeps coil dissipation inside a bench-thermal budget.
function safetyEnvelope(calc) {
  const resistanceOhm = calc.estimates.coil_resistance_ohm;
  const currentA = calc.inputs.current_a;
  const powerBudgetW = 5;
  const maxCurrentA = resistanceOhm > 0 ? round3(Math.sqrt(powerBudgetW / resistanceOhm)) : null;
  const voltageV = round3(currentA * resistanceOhm);
  const guidance = [
    'Always drive from a current-limited bench supply; set the limit before connecting the coil.',
    `At ${currentA} A the coil dissipates ~${calc.estimates.coil_power_w} W and needs ~${voltageV} V across it.`,
  ];
  if (maxCurrentA !== null) {
    guidance.push(`Keep continuous current at or below ~${maxCurrentA} A to stay within a ${powerBudgetW} W bench-thermal budget; pulse/duty-cycle above that.`);
  }
  if (calc.inputs.frequency_hz > 100000) {
    guidance.push('At this drive frequency, watch skin effect and parasitic heating; the DC resistance understates AC losses.');
  }
  return {
    coil_voltage_v: voltageV,
    coil_power_w: calc.estimates.coil_power_w,
    power_budget_w: powerBudgetW,
    within_power_budget: calc.estimates.coil_power_w <= powerBudgetW,
    max_continuous_current_a: maxCurrentA,
    guidance,
  };
}

// Concrete measurement checkpoints with target values pulled from the physics.
function testPlan(calc) {
  const e = calc.estimates;
  const steps = [
    { step: 'Measure coil DC resistance with a multimeter before applying power.', target: `~${e.coil_resistance_ohm} ohm (allow +/-15% for winding and lead variance)` },
    { step: 'Connect a current-limited supply and ramp current slowly from zero.', target: `Hold the limit at or below ${calc.inputs.current_a} A` },
    { step: 'Measure axial magnetic field at the coil center with a Hall/gauss probe.', target: `~${e.solenoid_field_mt} mT at ${calc.inputs.current_a} A (ideal-solenoid estimate; real coils read lower)` },
    { step: 'Run energized for a timed interval and log coil temperature.', target: `~${e.coil_power_w} W dissipation; stop if temperature rise exceeds ~40 C` },
  ];
  if (e.optical_na_estimate > 0) {
    steps.push({ step: 'Couple light through the core and check guiding/leakage.', target: `Numerical aperture ~${e.optical_na_estimate} from n_core/n_clad` });
  }
  return steps;
}

// Assemble everything into one self-contained Markdown deliverable (the paid artifact).
function buildReport(ctx) {
  const { concept, receiptId, stamp, stack, calc, bom, safety, plan, riskFlags } = ctx;
  const e = calc.estimates;
  const lines = [];
  lines.push('# AI Materials Bench - Concept Report');
  lines.push('');
  lines.push('**Product:** AetherMoore AI Materials Bench  ');
  lines.push(`**Receipt:** \`${receiptId}\`  `);
  lines.push(`**Date:** ${stamp}  `);
  lines.push(`**Conductor:** ${calc.conductor} (rho = ${calc.conductor_resistivity_ohm_m} ohm-m)`);
  lines.push('');
  lines.push('## Concept');
  lines.push(concept);
  lines.push('');
  lines.push('## Inputs');
  Object.entries(calc.inputs).forEach(([k, v]) => lines.push(`- ${k}: ${v}`));
  if (calc.assumed.length) {
    lines.push('');
    lines.push('### Assumed / clamped');
    calc.assumed.forEach((a) => lines.push(`- ${a}`));
  }
  lines.push('');
  lines.push('## Material stack');
  stack.forEach((layer) => lines.push(`- **${layer.layer}** - ${layer.material} (${layer.role})`));
  lines.push('');
  lines.push('## Estimated physics');
  lines.push(`- Solenoid field: ${e.solenoid_field_mt} mT`);
  lines.push(`- Coil resistance: ${e.coil_resistance_ohm} ohm`);
  lines.push(`- Coil power: ${e.coil_power_w} W`);
  lines.push(`- Wire length: ${e.wire_length_m} m`);
  lines.push(`- Skin depth: ${e.skin_depth_mm === null ? 'n/a (DC)' : e.skin_depth_mm + ' mm'}`);
  lines.push(`- Optical NA: ${e.optical_na_estimate}`);
  lines.push('');
  lines.push('## Bill of materials (rough estimate)');
  lines.push('| Part | Qty | Est. USD |');
  lines.push('| --- | --- | --- |');
  bom.items.forEach((i) => lines.push(`| ${i.part} | ${i.qty} | $${i.est_usd_low} - $${i.est_usd_high} |`));
  lines.push(`| **Total** |  | **$${bom.estimated_total_low} - $${bom.estimated_total_high}** |`);
  lines.push('');
  lines.push(`_${bom.note}_`);
  lines.push('');
  lines.push('## Safety envelope');
  lines.push(`- Coil voltage at set current: ~${safety.coil_voltage_v} V`);
  lines.push(`- Power budget: ${safety.power_budget_w} W (${safety.within_power_budget ? 'within budget' : 'OVER budget - reduce current/turns'})`);
  if (safety.max_continuous_current_a !== null) lines.push(`- Max continuous current: ~${safety.max_continuous_current_a} A`);
  safety.guidance.forEach((g) => lines.push(`- ${g}`));
  lines.push('');
  lines.push('## Test plan');
  plan.forEach((p, idx) => lines.push(`${idx + 1}. ${p.step}\n   _Target:_ ${p.target}`));
  lines.push('');
  lines.push('## Risk flags');
  riskFlags.forEach((f) => lines.push(`- ${f}`));
  lines.push('');
  lines.push('---');
  lines.push('_Generated by AetherMoore AI Materials Bench. First-pass engineering estimates for bench prototyping - validate with current-limited low-voltage tests before committing to a design._');
  return lines.join('\n');
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
    const receiptId = `matbench_${sha(JSON.stringify({ concept, inputs: calc.inputs })).slice(0, 16)}`;
    const stamp = new Date().toISOString().slice(0, 10);
    const stack = materialsFor(concept, conductor);
    const bom = billOfMaterials(calc, conductor);
    const safety = safetyEnvelope(calc);
    const plan = testPlan(calc);
    const riskFlags = flags(calc);
    const result = {
      ok: true,
      schema_version: 'aethermoore_ai_materials_bench_v1',
      product: 'AI Materials Bench',
      receipt_id: receiptId,
      concept,
      architecture: {
        name: 'magneto-optic composite tube sleeve',
        stack,
        purpose: 'model a glass/fiber tube with conductive carbon skin, coil winding, magnetic flux shaping, and optical lane.',
      },
      math: calc,
      bill_of_materials: bom,
      safety,
      test_plan: plan,
      risk_flags: riskFlags,
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
      report_markdown: buildReport({ concept, receiptId, stamp, stack, calc, bom, safety, plan, riskFlags }),
      sellable_output: {
        offer: 'Downloadable concept report: material stack, costed bill of materials, field/heat/optical estimates, a measurement test plan, a safety envelope, and a signed receipt.',
        deliverable: 'report_markdown (export to .md / print to PDF)',
        starter_price: '$49 concept report or $199 prototype worksheet pack',
      },
    };
    return res.status(200).json(result);
  } catch (error) {
    return res.status(500).json({ ok: false, error: error && error.message ? error.message : String(error) });
  }
};
