'use strict';

const crypto = require('node:crypto');

const ROLE_ALIASES = [
  ['observe', /\b(scan|sense|read|observe|listen|watch|inspect|find|identify)\b/i],
  ['measure', /\b(measure|sample|check|score|compare|audit|count|estimate)\b/i],
  ['gate', /\b(if|gate|route|guard|approve|deny|qualify|filter|triage)\b/i],
  ['move', /\b(move|send|transfer|push|book|schedule|dispatch|handoff)\b/i],
  ['compute', /\b(compute|plan|classify|infer|generate|calculate|analyze|build)\b/i],
  ['transmit', /\b(text|sms|email|call|notify|message|webhook|report)\b/i],
  ['repair', /\b(fix|repair|stabilize|correct|patch|clean|improve)\b/i],
  ['report', /\b(report|export|log|summary|dashboard|receipt|deliver)\b/i],
];

const ROLE_FRAME = {
  observe: { phase: 0.1, valence: 2, stability: 0.9 },
  measure: { phase: 0.15, valence: 2, stability: 0.88 },
  gate: { phase: 0.3, valence: 3, stability: 0.72 },
  move: { phase: 0.45, valence: 2, stability: 0.55 },
  compute: { phase: 0.55, valence: 4, stability: 0.62 },
  transmit: { phase: 0.7, valence: 2, stability: 0.48 },
  repair: { phase: 0.82, valence: 3, stability: 0.78 },
  report: { phase: 0.92, valence: 1, stability: 0.92 },
};

const CHEMISTRY_PRIMITIVES = [
  ['measure_state', 'Establish the pre-change state before mutation.'],
  ['stabilize_fragment', 'Reduce ambiguity and stabilize the active fragment.'],
  ['bind_operation', 'Bind command slots into an executable workflow unit.'],
  ['verify_reversibility', 'Confirm the result can be reconstructed from the receipt.'],
  ['export_receipt', 'Emit customer-facing output and machine-readable JSON.'],
];

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
  return crypto.createHash('sha256').update(value).digest('hex');
}

function words(input) {
  return String(input || '')
    .split(/[^A-Za-z0-9$#@._-]+/)
    .map((token) => token.trim())
    .filter((token) => token.length > 2)
    .slice(0, 24);
}

function roleFor(token) {
  const match = ROLE_ALIASES.find(([, pattern]) => pattern.test(token));
  return match ? match[0] : 'compute';
}

function semanticAtoms(tokens) {
  const selected = [];
  const seen = new Set();
  for (const token of tokens) {
    const role = roleFor(token);
    const key = `${role}:${token.toLowerCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const frame = ROLE_FRAME[role];
    selected.push({
      atom_id: sha(key).slice(0, 12),
      token,
      role,
      phase: frame.phase,
      valence: frame.valence,
      stability: frame.stability,
    });
    if (selected.length >= 10) break;
  }
  return selected;
}

function chemistryStack(input, mode, atoms) {
  const commandKey = mode === 'chemistry' ? 'material-command' : 'workflow-command';
  return CHEMISTRY_PRIMITIVES.map(([primitive, intent], index) => ({
    command_id: `chemcmd:${String(index).padStart(3, '0')}`,
    command_key: commandKey,
    primitive,
    intent,
    reversible: true,
    atom_inputs: atoms.slice(0, 4).map((atom) => atom.atom_id),
    receipt_hint: sha(`${primitive}|${input}`).slice(0, 16),
  }));
}

function risks(input, atoms) {
  const text = String(input || '').toLowerCase();
  const flags = [];
  if (text.includes('secret') || text.includes('password') || text.includes('token')) {
    flags.push('Remove secrets before running customer workflows.');
  }
  if (text.includes('payment') || text.includes('refund') || text.includes('bank')) {
    flags.push('Add human approval before money movement.');
  }
  if (atoms.some((atom) => atom.role === 'transmit')) {
    flags.push('Confirm message copy and destination before sending.');
  }
  return flags.length ? flags : ['No obvious blocker in this input. Keep a receipt for the output.'];
}

function nextActions(mode) {
  if (mode === 'chemistry') {
    return [
      'Convert the stack into a recipe-style command sheet.',
      'Attach simulator fields only when the backend has the required chemistry package.',
      'Offer a paid cleaned report export.',
    ];
  }
  if (mode === 'software') {
    return [
      'Turn atoms into an issue checklist.',
      'Add repository upload or GitHub URL intake.',
      'Offer a paid patch plan or implementation sprint.',
    ];
  }
  return [
    'Turn the output into a customer workflow map.',
    'Add intake fields and weekly reporting.',
    'Offer setup as a paid service.',
  ];
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') {
    return res.status(405).json({ ok: false, error: 'POST required' });
  }

  try {
    const body = await readBody(req);
    const input = String(body.input || '').trim();
    const mode = String(body.mode || 'business').trim().toLowerCase();
    const customer = String(body.customer || 'user').trim();
    if (!input) return res.status(400).json({ ok: false, error: 'input is required' });
    if (input.length > 4000) return res.status(400).json({ ok: false, error: 'input is too long' });

    const tokenList = words(input);
    const atoms = semanticAtoms(tokenList);
    const stack = chemistryStack(input, mode, atoms);
    const result = {
      ok: true,
      schema_version: 'aethermoore-atomic-output-v1',
      receipt_id: `atomlab_${sha(`${mode}|${customer}|${input}`).slice(0, 16)}`,
      mode,
      customer,
      summary: `Mapped ${tokenList.length} input tokens into ${atoms.length} semantic atoms and ${stack.length} command steps for ${customer}.`,
      semantic_atoms: atoms,
      chemistry_stack: stack,
      risk_flags: risks(input, atoms),
      next_actions: nextActions(mode),
      sellable_output: {
        product: mode === 'chemistry' ? 'Chemistry Command Stack' : 'Atomic Output Lab',
        recommended_price: mode === 'business' ? '$99 setup or $399/month operation' : '$29 report or $199 setup',
        delivery: 'Polished result page plus exportable JSON receipt.',
      },
    };

    return res.status(200).json(result);
  } catch (error) {
    return res.status(500).json({ ok: false, error: error && error.message ? error.message : String(error) });
  }
};
