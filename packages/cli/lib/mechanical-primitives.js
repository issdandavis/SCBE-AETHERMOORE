'use strict';

const CODING_PRIMITIVES = Object.freeze([
  {
    id: 'data',
    label: 'DATA',
    glyph: '+ − ×',
    role: 'values and operations',
    expression: 'join + take − weave × over leaves 0–9',
    runtime: ['read_file', 'list_files', 'search_text', 'workspace_info', 'git_status', 'git_diff'],
    milestone: { state: 'reported-verified', label: '98.6%', note: 'Number-realm execution milestone' },
  },
  {
    id: 'bind',
    label: 'BIND',
    glyph: 'let x',
    role: 'named state and reuse',
    expression: 'let x = a ; f(x)',
    runtime: ['sessions', 'custom commands', 'write_file', 'edit_file', 'create_directory'],
    milestone: { state: 'reported-verified', label: '/ calc 100%', note: 'Named-state milestone' },
  },
  {
    id: 'branch',
    label: 'BRANCH',
    glyph: 'if · yes/no',
    role: 'select one governed path',
    expression: 'if v then a else b',
    runtime: ['provider routing', 'permission decisions', 'tool refusal'],
    milestone: { state: 'next-free-node', label: 'free node', note: 'Substrate verification remains open' },
  },
  {
    id: 'loop',
    label: 'LOOP',
    glyph: '◯ repeat',
    role: 'iterate with carried state',
    expression: 'while v: body',
    runtime: ['iterative model/tool rounds', 'resume', 'compact'],
    milestone: { state: 'next-free-node', label: 'free node', note: 'Substrate verification remains open' },
  },
]);

const COMPOSITIONS = Object.freeze([
  { form: 'a ; b', name: 'SEQUENCE', meaning: 'do a, then b; the tape moves right' },
  { form: 'let x = a ; f(x)', name: 'BIND', meaning: 'store an intermediate and reuse it' },
  { form: 'if v then a else b', name: 'BRANCH', meaning: 'select from a yes/no signal' },
  { form: 'while v: body', name: 'LOOP', meaning: 'repeat over carried state' },
]);

const TONGUE_LANES = Object.freeze([
  { id: 'KO', tongue: "Kor'aelin", surface: 'Python', phi: 1.0 },
  { id: 'AV', tongue: 'Avali', surface: 'JavaScript', phi: 1.62 },
  { id: 'RU', tongue: 'Runethic', surface: 'Rust', phi: 2.62 },
  { id: 'CA', tongue: 'Cassisivadan', surface: 'Math', phi: 4.24 },
  { id: 'UM', tongue: 'Umbroth', surface: 'Haskell', phi: 6.85 },
  { id: 'DR', tongue: 'Draumric', surface: 'Markdown', phi: 11.09 },
]);

const J_SPACE_WAFER = Object.freeze({
  name: 'j-space wafer',
  subtitle: 'the fold heals',
  opcode_cells: 64,
  disk: 'Poincaré disk',
  sheet: '−x₀² + x₁² + x₂² = −1',
  reported_distance_error: 3.997e-15,
  views: ['disk', 'sheet', 'spin bands'],
  realm_direction: 'realm 0 is the inward nest; realm 3 meets the outer bevel where d_H diverges',
  control: { id: 'nest', label: 'Nest cost', direction: 'inward' },
  provenance:
    'Geometry labels and numeric milestone are project-owner supplied interface data; this CLI does not recompute the proof.',
});

function mechanicalModel() {
  return {
    schema_version: 'scbe_mechanical_interface_v1',
    primitives: CODING_PRIMITIVES,
    compositions: COMPOSITIONS,
    tongue_lanes: TONGUE_LANES,
    wafer: J_SPACE_WAFER,
  };
}

function formatPrimitives() {
  const width = Math.max(...CODING_PRIMITIVES.map((item) => item.label.length));
  return [
    'Coding primitives · one substrate',
    ...CODING_PRIMITIVES.map(
      (item) =>
        `  ${item.label.padEnd(width)}  ${item.glyph.padEnd(12)} ${item.role} · ${item.milestone.label}`
    ),
    '',
    '  a ; b                 sequence',
    '  let x = a ; f(x)      bind / memory',
    '  if v then a else b    branch / select',
    '  while v: body         loop / carried state',
    '',
    `Tongue lanes  ${TONGUE_LANES.map((lane) => `${lane.id}/${lane.surface} φ${lane.phi.toFixed(2)}`).join('  ')}`,
    'Milestone labels are project-reported; /status reports this runtime’s live behavior.',
  ].join('\n');
}

function formatWafer() {
  return [
    `${J_SPACE_WAFER.name} · ${J_SPACE_WAFER.subtitle}`,
    `${J_SPACE_WAFER.opcode_cells} opcode cells · ${J_SPACE_WAFER.disk}`,
    `sheet  ${J_SPACE_WAFER.sheet}`,
    `reported fold error  ${J_SPACE_WAFER.reported_distance_error.toExponential(3)}`,
    `views  ${J_SPACE_WAFER.views.join(' · ')}`,
    `realms ${J_SPACE_WAFER.realm_direction}`,
    `${J_SPACE_WAFER.control.id}  ${J_SPACE_WAFER.control.label} · ${J_SPACE_WAFER.control.direction}`,
  ].join('\n');
}

module.exports = {
  CODING_PRIMITIVES,
  COMPOSITIONS,
  TONGUE_LANES,
  J_SPACE_WAFER,
  mechanicalModel,
  formatPrimitives,
  formatWafer,
};
