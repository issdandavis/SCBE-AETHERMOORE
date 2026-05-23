import { createHash } from 'crypto';
import type { TongueCode } from './ss1.js';

export type SemanticDomain =
  | 'natural'
  | 'code'
  | 'workflow'
  | 'physical'
  | 'chemical'
  | 'governance';

export type SemanticRelationKind =
  | 'enables'
  | 'blocked_by'
  | 'accelerated_by'
  | 'transforms_into'
  | 'analogous_to'
  | 'contains'
  | 'guards'
  | 'inhibits'
  | 'self_references';

export interface SemanticNucleus {
  meaning: string;
  invariants: string[];
}

export interface SemanticOrbital {
  domain: SemanticDomain;
  role: string;
  terms: string[];
  stability: number;
}

export interface SemanticBond {
  kind: SemanticRelationKind;
  target: string;
  domain: SemanticDomain;
  evidence: string;
}

export interface SemanticIsotope {
  domain: SemanticDomain;
  id: string;
  examples: string[];
}

export interface SemanticCodeRelations {
  patterns: string[];
  blockers: string[];
  accelerators: string[];
  analogies: string[];
}

export interface AtomicProxy {
  symbol: string;
  role: string;
  valence: number;
  stableCore: boolean;
}

export interface SemanticAtom {
  schemaVersion: 'scbe-semantic-atom-v1';
  semanticId: string;
  bucketId: string;
  surfaceForms: string[];
  tongues: TongueCode[];
  nucleus: SemanticNucleus;
  orbitals: SemanticOrbital[];
  bonds: SemanticBond[];
  isotopes: SemanticIsotope[];
  codeRelations: SemanticCodeRelations;
  atomicProxy: AtomicProxy;
  lineage: {
    preseeded: boolean;
    version: string;
    refinements: string[];
  };
}

export interface SemanticToken {
  schemaVersion: 'scbe-semantic-token-v1';
  surface: string;
  normalizedSurface: string;
  semanticId: string;
  bucketId: string;
  tongue: TongueCode;
  span: [number, number];
  atom: SemanticAtom;
  embedding: number[];
  relationTree: {
    near: string[];
    far: string[];
    blockers: string[];
    selfReference: boolean;
  };
}

export interface SemanticLedgerEntry {
  schemaVersion: 'scbe-semantic-token-ledger-v1';
  originalInput: string;
  normalizedInput: string;
  tokenCount: number;
  tokens: Array<{
    surface: string;
    semanticId: string;
    bucketId: string;
    span: [number, number];
  }>;
  inputHash: string;
}

export type SemanticWorkflowChannel =
  | 'pipe'
  | 'funnel'
  | 'dot_to_dot'
  | 'websocket'
  | 'agent_handoff'
  | 'bifurcation'
  | 'merge';

export interface SemanticWorkflowNode {
  id: string;
  tokenIndex: number;
  semanticId: string;
  bucketId: string;
  label: string;
  domains: SemanticDomain[];
}

export interface SemanticWorkflowEdge {
  from: string;
  to: string;
  channel: SemanticWorkflowChannel;
  relation: string;
  reversible: boolean;
  stateRule: string;
}

export interface SemanticWorkflowThread {
  schemaVersion: 'scbe-semantic-workflow-thread-v1';
  threadId: string;
  originalInput: string;
  tongue: TongueCode;
  nodes: SemanticWorkflowNode[];
  edges: SemanticWorkflowEdge[];
  braidedDomains: SemanticDomain[];
  stateRules: string[];
  receipt: {
    inputHash: string;
    tokenCount: number;
    edgeCount: number;
  };
}

const DOMAIN_INDEX: Record<SemanticDomain, number> = {
  natural: 0,
  code: 1,
  workflow: 2,
  physical: 3,
  chemical: 4,
  governance: 5,
};

const RELATION_INDEX: Record<SemanticRelationKind, number> = {
  enables: 0,
  blocked_by: 1,
  accelerated_by: 2,
  transforms_into: 3,
  analogous_to: 4,
  contains: 5,
  guards: 6,
  inhibits: 7,
  self_references: 8,
};

const TONGUE_INDEX: Record<TongueCode, number> = {
  KO: 0,
  AV: 1,
  RU: 2,
  CA: 3,
  UM: 4,
  DR: 5,
};

export const SEMANTIC_ATOMS: Record<string, SemanticAtom> = {
  FLOW: {
    schemaVersion: 'scbe-semantic-atom-v1',
    semanticId: 'FLOW',
    bucketId: 'CORE:MOTION:DIRECTED_CONTINUITY',
    surfaceForms: [
      'flow',
      'flows',
      'stream',
      'pipeline',
      'control flow',
      'data flow',
      'event stream',
    ],
    tongues: ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'],
    nucleus: {
      meaning: 'Directed movement through a medium, path, process, or system.',
      invariants: ['direction', 'continuity', 'path', 'state_transition'],
    },
    orbitals: [
      {
        domain: 'natural',
        role: 'material-motion',
        terms: ['river', 'current', 'waterfall'],
        stability: 0.92,
      },
      {
        domain: 'code',
        role: 'execution-motion',
        terms: ['control flow', 'data flow', 'event stream'],
        stability: 0.96,
      },
      {
        domain: 'workflow',
        role: 'task-motion',
        terms: ['handoff', 'pipeline', 'approval chain'],
        stability: 0.9,
      },
    ],
    bonds: [
      {
        kind: 'enables',
        target: 'TRANSPORT',
        domain: 'workflow',
        evidence: 'flow carries state from one node to another',
      },
      {
        kind: 'blocked_by',
        target: 'BLOCK',
        domain: 'code',
        evidence: 'an exception or failed precondition interrupts flow',
      },
      {
        kind: 'accelerated_by',
        target: 'CHANNEL',
        domain: 'natural',
        evidence: 'a channel or slope increases directed movement',
      },
      {
        kind: 'analogous_to',
        target: 'PIPELINE',
        domain: 'code',
        evidence: 'input-function-output forms a directed path',
      },
    ],
    isotopes: [
      {
        domain: 'natural',
        id: 'FLOW:NATURAL:WATER',
        examples: ['water in a river', 'air current'],
      },
      {
        domain: 'code',
        id: 'FLOW:CODE:CONTROL',
        examples: ['if branch', 'return path', 'event handler'],
      },
      {
        domain: 'workflow',
        id: 'FLOW:WORKFLOW:TASK',
        examples: ['task dependency chain', 'approval handoff'],
      },
    ],
    codeRelations: {
      patterns: [
        'input -> function -> output',
        'event -> handler -> effect',
        'task -> dependency -> completion',
      ],
      blockers: ['exception', 'deadlock', 'type error', 'missing dependency'],
      accelerators: ['cache', 'parallelism', 'batching', 'index'],
      analogies: ['water:river :: data:pipeline', 'pressure:flow :: queue_demand:event_processing'],
    },
    atomicProxy: { symbol: 'O', role: 'carrier', valence: 2, stableCore: true },
    lineage: {
      preseeded: true,
      version: '2026-05-23',
      refinements: ['initial atom-like semantic tokenizer layer'],
    },
  },
  WATER: {
    schemaVersion: 'scbe-semantic-atom-v1',
    semanticId: 'WATER',
    bucketId: 'CORE:MATERIAL:FLOWING_SOLVENT',
    surfaceForms: ['water', 'river', 'rain', 'steam', 'ice', 'liquid'],
    tongues: ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'],
    nucleus: {
      meaning: 'Fluid material that flows, carries, dissolves, cools, erodes, and changes phase.',
      invariants: ['fluidity', 'cohesion', 'phase_change', 'solvent_behavior'],
    },
    orbitals: [
      {
        domain: 'physical',
        role: 'phase-material',
        terms: ['liquid', 'ice', 'steam'],
        stability: 0.95,
      },
      {
        domain: 'chemical',
        role: 'compound',
        terms: ['H2O', 'solvent', 'polar molecule'],
        stability: 0.98,
      },
      {
        domain: 'code',
        role: 'stream-metaphor',
        terms: ['stream', 'buffer', 'pipe', 'event bus'],
        stability: 0.86,
      },
    ],
    bonds: [
      {
        kind: 'enables',
        target: 'FLOW',
        domain: 'natural',
        evidence: 'liquid water commonly instantiates visible flow',
      },
      {
        kind: 'transforms_into',
        target: 'ICE',
        domain: 'physical',
        evidence: 'phase change under freezing conditions',
      },
      {
        kind: 'transforms_into',
        target: 'STEAM',
        domain: 'physical',
        evidence: 'phase change under heating conditions',
      },
      {
        kind: 'analogous_to',
        target: 'BUFFER',
        domain: 'code',
        evidence: 'both carry state through a bounded channel',
      },
    ],
    isotopes: [
      { domain: 'physical', id: 'WATER:PHYSICAL:LIQUID', examples: ['river', 'rain', 'container'] },
      { domain: 'chemical', id: 'WATER:CHEMICAL:H2O', examples: ['solvent', 'reaction product'] },
      { domain: 'code', id: 'WATER:CODE:STREAM', examples: ['byte stream', 'event stream'] },
    ],
    codeRelations: {
      patterns: ['stream -> buffer -> consumer', 'source -> pipe -> sink'],
      blockers: ['closed pipe', 'backpressure', 'overflow', 'invalid encoding'],
      accelerators: ['larger buffer', 'streaming parser', 'pressure/throughput increase'],
      analogies: [
        'filter:water :: validator:input_stream',
        'leak:container :: memory_leak:runtime_boundary',
      ],
    },
    atomicProxy: { symbol: 'H2O', role: 'fluid-carrier', valence: 2, stableCore: true },
    lineage: {
      preseeded: true,
      version: '2026-05-23',
      refinements: ['initial atom-like semantic tokenizer layer'],
    },
  },
  BLOCK: {
    schemaVersion: 'scbe-semantic-atom-v1',
    semanticId: 'BLOCK',
    bucketId: 'CORE:CONSTRAINT:OBSTRUCTION',
    surfaceForms: [
      'block',
      'blocks',
      'blocked',
      'barrier',
      'dam',
      'error',
      'exception',
      'deny',
      'failed test',
    ],
    tongues: ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'],
    nucleus: {
      meaning:
        'Obstruction, constraint, or interruption that prevents a flow or transition from completing.',
      invariants: ['obstruction', 'interruption', 'constraint', 'resistance'],
    },
    orbitals: [
      {
        domain: 'natural',
        role: 'physical-obstruction',
        terms: ['dam', 'clog', 'barrier'],
        stability: 0.9,
      },
      {
        domain: 'code',
        role: 'execution-obstruction',
        terms: ['exception', 'type error', 'deadlock'],
        stability: 0.97,
      },
      {
        domain: 'governance',
        role: 'policy-obstruction',
        terms: ['deny', 'failed gate', 'missing approval'],
        stability: 0.96,
      },
    ],
    bonds: [
      {
        kind: 'blocked_by',
        target: 'FLOW',
        domain: 'workflow',
        evidence: 'a block is defined by the flow it interrupts',
      },
      {
        kind: 'guards',
        target: 'BOUNDARY',
        domain: 'governance',
        evidence: 'policy blocks protect boundary conditions',
      },
      {
        kind: 'inhibits',
        target: 'DISPATCH',
        domain: 'code',
        evidence: 'failed tests or policy denial prevent execution',
      },
    ],
    isotopes: [
      { domain: 'natural', id: 'BLOCK:NATURAL:DAM', examples: ['dam', 'clog', 'wall'] },
      {
        domain: 'code',
        id: 'BLOCK:CODE:ERROR',
        examples: ['syntax error', 'type error', 'exception'],
      },
      {
        domain: 'governance',
        id: 'BLOCK:GOVERNANCE:DENY',
        examples: ['policy denial', 'missing approval'],
      },
    ],
    codeRelations: {
      patterns: [
        'condition -> reject -> halt',
        'test -> failure -> no merge',
        'policy -> denial -> no dispatch',
      ],
      blockers: ['syntax error', 'type error', 'failed test', 'missing secret', 'policy denial'],
      accelerators: ['clear diagnostic', 'repair suggestion', 'known recovery path'],
      analogies: ['dam:river :: type_error:pipeline', 'failed_test:merge :: wall:path'],
    },
    atomicProxy: { symbol: 'Fe', role: 'boundary', valence: 2, stableCore: true },
    lineage: {
      preseeded: true,
      version: '2026-05-23',
      refinements: ['initial atom-like semantic tokenizer layer'],
    },
  },
};

function normalizeText(value: string): string {
  return value.toLowerCase().replace(/\s+/g, ' ').trim();
}

function hashText(value: string): string {
  return createHash('sha256').update(value, 'utf8').digest('hex');
}

function stableUnitHash(value: string): number {
  const hex = hashText(value).slice(0, 8);
  return parseInt(hex, 16) / 0xffffffff;
}

export function getSemanticAtom(semanticId: string): SemanticAtom | undefined {
  return SEMANTIC_ATOMS[semanticId.toUpperCase()];
}

export function buildRelationTree(atom: SemanticAtom): SemanticToken['relationTree'] {
  const near = new Set<string>();
  const blockers = new Set<string>();
  for (const bond of atom.bonds) {
    if (bond.kind === 'blocked_by' || bond.kind === 'inhibits') {
      blockers.add(bond.target);
    } else {
      near.add(bond.target);
    }
  }
  for (const orbital of atom.orbitals) {
    for (const term of orbital.terms.slice(0, 3)) {
      near.add(term);
    }
  }

  return {
    near: [...near].sort(),
    far:
      atom.semanticId === 'FLOW'
        ? ['stasis', 'isolation']
        : atom.semanticId === 'BLOCK'
          ? ['continuity']
          : ['dryness'],
    blockers: [...blockers].sort(),
    selfReference: atom.bonds.some((bond) => bond.kind === 'self_references'),
  };
}

export function embedSemanticAtom(
  atom: SemanticAtom,
  tongue: TongueCode = atom.tongues[0]
): number[] {
  const domainMass = atom.orbitals.reduce(
    (acc, orbital) => acc + DOMAIN_INDEX[orbital.domain] * orbital.stability,
    0
  );
  const relationMass = atom.bonds.reduce(
    (acc, bond) => acc + RELATION_INDEX[bond.kind] + DOMAIN_INDEX[bond.domain],
    0
  );
  const invariantMass = atom.nucleus.invariants.length;
  const codeMass = atom.codeRelations.patterns.length + atom.codeRelations.blockers.length;
  return [
    stableUnitHash(atom.semanticId),
    stableUnitHash(atom.bucketId),
    atom.atomicProxy.valence / 8,
    atom.atomicProxy.stableCore ? 1 : 0,
    invariantMass / 8,
    atom.orbitals.length / 8,
    atom.bonds.length / 16,
    atom.isotopes.length / 8,
    domainMass / Math.max(atom.orbitals.length * 5, 1),
    relationMass / Math.max(atom.bonds.length * 14, 1),
    codeMass / 16,
    TONGUE_INDEX[tongue] / 5,
  ];
}

export function tokenizeSemanticAtoms(input: string, tongue: TongueCode = 'KO'): SemanticToken[] {
  const normalized = normalizeText(input);
  const matches: SemanticToken[] = [];

  for (const atom of Object.values(SEMANTIC_ATOMS)) {
    const forms = [...atom.surfaceForms].sort((a, b) => b.length - a.length);
    for (const form of forms) {
      const normalizedForm = normalizeText(form);
      const pattern = new RegExp(
        `(^|\\b)${normalizedForm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}(\\b|$)`,
        'g'
      );
      let match: RegExpExecArray | null;
      while ((match = pattern.exec(normalized)) !== null) {
        const start = match.index + match[1].length;
        const end = start + normalizedForm.length;
        matches.push({
          schemaVersion: 'scbe-semantic-token-v1',
          surface: input.slice(start, end) || normalizedForm,
          normalizedSurface: normalizedForm,
          semanticId: atom.semanticId,
          bucketId: atom.bucketId,
          tongue,
          span: [start, end],
          atom,
          embedding: embedSemanticAtom(atom, tongue),
          relationTree: buildRelationTree(atom),
        });
      }
    }
  }

  const ordered = matches.sort(
    (a, b) => a.span[0] - b.span[0] || b.normalizedSurface.length - a.normalizedSurface.length
  );
  const accepted: SemanticToken[] = [];
  for (const candidate of ordered) {
    const overlaps = accepted.some(
      (token) => candidate.span[0] < token.span[1] && token.span[0] < candidate.span[1]
    );
    if (!overlaps) {
      accepted.push(candidate);
    }
  }
  return accepted;
}

export function buildSemanticLedgerEntry(
  input: string,
  tokens = tokenizeSemanticAtoms(input)
): SemanticLedgerEntry {
  return {
    schemaVersion: 'scbe-semantic-token-ledger-v1',
    originalInput: input,
    normalizedInput: normalizeText(input),
    tokenCount: tokens.length,
    tokens: tokens.map((token) => ({
      surface: token.surface,
      semanticId: token.semanticId,
      bucketId: token.bucketId,
      span: token.span,
    })),
    inputHash: hashText(input),
  };
}

function nodeIdFor(token: SemanticToken, index: number): string {
  return `${token.semanticId.toLowerCase()}-${index}-${token.span[0]}-${token.span[1]}`;
}

function domainsFor(atom: SemanticAtom): SemanticDomain[] {
  return [...new Set(atom.orbitals.map((orbital) => orbital.domain))].sort();
}

function inferWorkflowChannel(from: SemanticToken, to: SemanticToken): SemanticWorkflowChannel {
  if (from.semanticId === 'WATER' && to.semanticId === 'FLOW') {
    return 'pipe';
  }
  if (from.semanticId === 'FLOW' && to.semanticId === 'BLOCK') {
    return 'bifurcation';
  }
  if (from.semanticId === 'BLOCK' && to.semanticId === 'FLOW') {
    return 'merge';
  }
  if (
    from.atom.orbitals.some((orbital) => orbital.domain === 'code') &&
    to.atom.orbitals.some((orbital) => orbital.domain === 'workflow')
  ) {
    return 'agent_handoff';
  }
  if (
    from.atom.orbitals.some((orbital) => orbital.domain === 'workflow') ||
    to.atom.orbitals.some((orbital) => orbital.domain === 'workflow')
  ) {
    return 'websocket';
  }
  if (to.semanticId === 'BLOCK') {
    return 'funnel';
  }
  return 'dot_to_dot';
}

function stateRuleFor(channel: SemanticWorkflowChannel): string {
  switch (channel) {
    case 'pipe':
      return 'preserve payload identity while moving state through a bounded channel';
    case 'funnel':
      return 'many inputs converge into one narrower validation or dispatch point';
    case 'dot_to_dot':
      return 'advance only to the next explicit node in the relation chain';
    case 'websocket':
      return 'keep bidirectional session state synchronized across handoff boundary';
    case 'agent_handoff':
      return 'transfer authority with explicit source, target, task, and receipt';
    case 'bifurcation':
      return 'split flow under a rule and ledger which lanes continue, halt, or exit';
    case 'merge':
      return 'realign split lanes only when state rules agree on shared invariants';
  }
}

function relationFor(from: SemanticToken, to: SemanticToken): string {
  const direct = from.atom.bonds.find((bond) => bond.target === to.semanticId);
  if (direct) {
    return direct.kind;
  }
  const inverse = to.atom.bonds.find((bond) => bond.target === from.semanticId);
  return inverse ? `inverse:${inverse.kind}` : 'sequence';
}

export function buildSemanticWorkflowThread(
  input: string,
  tongue: TongueCode = 'KO'
): SemanticWorkflowThread {
  const tokens = tokenizeSemanticAtoms(input, tongue);
  const nodes = tokens.map((token, index) => ({
    id: nodeIdFor(token, index),
    tokenIndex: index,
    semanticId: token.semanticId,
    bucketId: token.bucketId,
    label: token.normalizedSurface,
    domains: domainsFor(token.atom),
  }));
  const edges: SemanticWorkflowEdge[] = [];

  for (let index = 0; index < tokens.length - 1; index += 1) {
    const from = tokens[index];
    const to = tokens[index + 1];
    const channel = inferWorkflowChannel(from, to);
    edges.push({
      from: nodes[index].id,
      to: nodes[index + 1].id,
      channel,
      relation: relationFor(from, to),
      reversible: channel === 'websocket' || channel === 'merge',
      stateRule: stateRuleFor(channel),
    });
  }

  const braidedDomains = [...new Set(nodes.flatMap((node) => node.domains))].sort();
  const stateRules = [...new Set(edges.map((edge) => edge.stateRule))];
  const inputHash = hashText(input);

  return {
    schemaVersion: 'scbe-semantic-workflow-thread-v1',
    threadId: hashText(`${tongue}:${input}`).slice(0, 16),
    originalInput: input,
    tongue,
    nodes,
    edges,
    braidedDomains,
    stateRules,
    receipt: {
      inputHash,
      tokenCount: tokens.length,
      edgeCount: edges.length,
    },
  };
}
