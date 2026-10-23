#!/usr/bin/env node

import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import vm from 'node:vm';
import {
  CONCEPT_RELATIONS,
  appendReasoningArtifact,
  createConceptFieldGraph,
  createReasoningArtifactGraph,
  hashReasoningValue,
  planConceptRoute,
  verifyConceptFieldGraph,
  verifyConceptRoute,
  verifyReasoningArtifactGraph,
} from '../dist/index.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(here, '..');
const defaultSource = String.raw`C:\dev\tongue-compiler\artifacts\essay_sentence_lattice_20261023`;
const defaultOutput = path.join(
  packageRoot,
  'docs',
  'benchmarks',
  'nested_concept_fields_20261023'
);

function parseArguments(argv) {
  const values = { source: defaultSource, output: defaultOutput, verifyOnly: false };
  for (let index = 0; index < argv.length; index += 1) {
    const value = argv[index];
    if (value === '--source') values.source = path.resolve(argv[++index]);
    else if (value === '--output') values.output = path.resolve(argv[++index]);
    else if (value === '--verify') values.verifyOnly = true;
    else if (value === '--help') {
      console.log(
        'node scripts/build_nested_concept_fields.mjs [--source DIR] [--output DIR] [--verify]'
      );
      process.exit(0);
    } else throw new Error(`unknown argument: ${value}`);
  }
  return values;
}

function sha256Bytes(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function sha256File(filePath) {
  return sha256Bytes(fs.readFileSync(filePath));
}

function writeJson(filePath, value) {
  fs.writeFileSync(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function readJsonLines(filePath) {
  return fs
    .readFileSync(filePath, 'utf8')
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

function slug(value) {
  const result = value
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
  return result || 'unnamed';
}

function uniqueSorted(values) {
  return [...new Set(values)].sort();
}

function tokenize(value) {
  return uniqueSorted(value.toLowerCase().match(/[a-z0-9]+/g) ?? []);
}

function jaccard(left, right) {
  const a = new Set(left);
  const b = new Set(right);
  const union = new Set([...a, ...b]);
  if (union.size === 0) return 0;
  let intersection = 0;
  for (const item of a) if (b.has(item)) intersection += 1;
  return intersection / union.size;
}

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function sampleSd(values) {
  if (values.length < 2) return 0;
  const center = mean(values);
  return Math.sqrt(
    values.reduce((sum, value) => sum + (value - center) ** 2, 0) / (values.length - 1)
  );
}

function mulberry32(seed) {
  let state = seed >>> 0;
  return () => {
    state += 0x6d2b79f5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffled(values, seed) {
  const output = [...values];
  const random = mulberry32(seed);
  for (let index = output.length - 1; index > 0; index -= 1) {
    const other = Math.floor(random() * (index + 1));
    [output[index], output[other]] = [output[other], output[index]];
  }
  return output;
}

function buildCodec(tongueDocument) {
  const tables = tongueDocument.tables;
  const inverses = {};
  for (const [tongue, table] of Object.entries(tables)) {
    if (!Array.isArray(table) || table.length !== 256 || new Set(table).size !== 256) {
      throw new Error(`tongue ${tongue} is not a 256-entry bijection`);
    }
    inverses[tongue] = new Map(table.map((token, byte) => [token, byte]));
  }
  return {
    encode(tongue, canonical) {
      const table = tables[tongue];
      if (!table) throw new Error(`unknown tongue: ${tongue}`);
      return Array.from(canonical, (byte) => table[byte]);
    },
    decode(tongue, tokens) {
      const inverse = inverses[tongue];
      if (!inverse) throw new Error(`unknown tongue: ${tongue}`);
      return Uint8Array.from(
        tokens.map((token) => {
          const byte = inverse.get(token);
          if (byte === undefined) throw new Error(`unknown ${tongue} token: ${token}`);
          return byte;
        })
      );
    },
  };
}

const relationDescriptions = {
  supports: 'evidence supports a claim',
  contradicts: 'a counterposition challenges a claim',
  requires: 'a claim requires this evidence or prerequisite',
  explains: 'an explanation interprets evidence or a claim',
  enables: 'this step makes the next step possible',
  returns_to: 'a conclusion returns to an earlier anchor',
  elaborates: 'a later sentence develops an earlier idea',
  transitions: 'the source text proceeds to the next sentence',
  same_source: 'two records share a source grouping',
};

const themeRules = [
  {
    id: 'identity',
    label: 'Identity and agency',
    terms: [
      'identity',
      'myself',
      'parts of me',
      'the man i became',
      'i choose',
      'i chose',
      'i am the one',
    ],
  },
  {
    id: 'judgment',
    label: 'Judgment and outside views',
    terms: ['judge', 'label', 'assume', 'outside', 'neighbors', 'others see', 'they see'],
  },
  {
    id: 'memory',
    label: 'Memory and loss',
    terms: ['memory', 'memories', 'remember', 'past', 'photos', 'dead', 'grandpa', 'grandfather'],
  },
  {
    id: 'boundary',
    label: 'Boundaries and access',
    terms: [
      'fence',
      'threshold',
      'porch',
      'private property',
      'inside',
      'window',
      'enter',
      'let inside',
    ],
  },
  {
    id: 'hospitality',
    label: 'Hospitality and invitation',
    terms: ['invite', 'blankets', 'pillows', 'sleeping bag', 'comfort', 'welcomed'],
  },
  {
    id: 'organization',
    label: 'Sorting and organization',
    terms: ['sort', 'bins', 'jars', 'collection', 'piles', 'clutter', 'clean storage'],
  },
  {
    id: 'growth',
    label: 'Growth and change',
    terms: ['learn', 'grow', 'developing', 'pushed me forward', 'accomplished', 'became', 'future'],
  },
];

function loadInputs(sourceDirectory) {
  const files = {
    rows: path.join(sourceDirectory, 'SENTENCE_LATTICE.jsonl'),
    paragraphs: path.join(sourceDirectory, 'PARAGRAPH_FUNCTIONS.json'),
    tongues: path.join(sourceDirectory, 'TONGUE_TABLES.json'),
    result: path.join(sourceDirectory, 'RESULT.json'),
  };
  for (const filePath of Object.values(files)) {
    if (!fs.existsSync(filePath)) throw new Error(`missing source artifact: ${filePath}`);
  }
  const result = readJson(files.result);
  const rows = readJsonLines(files.rows);
  const paragraphs = readJson(files.paragraphs);
  const tongueDocument = readJson(files.tongues);
  if (rows.length !== result.sentences) throw new Error('sentence count differs from RESULT.json');
  for (const row of rows) {
    const actual = sha256Bytes(Buffer.from(row.source_text, 'utf8'));
    if (actual !== row.source_utf8_sha256)
      throw new Error(`source hash mismatch: ${row.sentence_id}`);
  }
  return {
    files,
    result,
    rows,
    paragraphs,
    tongueDocument,
    hashes: Object.fromEntries(
      Object.entries(files).map(([name, filePath]) => [name, sha256File(filePath)])
    ),
  };
}

function buildReasoningGraph(inputs, codec) {
  const tongues = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
  const roleNames = uniqueSorted(inputs.rows.map((row) => row.role.family));
  const roleIndex = new Map(roleNames.map((role, index) => [role, index]));
  let graph = createReasoningArtifactGraph('essay-sentence-reasoning-20261023', [
    'paragraph_index',
    'sentence_index',
    'paragraph_position',
    'slot_count',
    'utf8_bytes',
    'role_index',
  ]);
  let previous = null;
  for (const [index, row] of inputs.rows.entries()) {
    const paragraphIndex = Number(row.paragraph_id.slice(1));
    const localIndex = Number(row.sentence_id.split('.')[1]);
    const bytes = Buffer.from(row.source_text, 'utf8');
    const syntax = uniqueSorted([
      `paragraph:${row.paragraph_id}`,
      `role:${row.role.family}`,
      ...row.slots.map((slot) => `function:${slug(slot.function)}`),
    ]);
    graph = appendReasoningArtifact(
      graph,
      {
        id: row.sentence_id,
        parent_ids: previous ? [previous] : [],
        tongue: tongues[index % tongues.length],
        canonical_bytes: bytes,
        public_summary: `${row.sentence_id} · ${row.role.family} · ${row.map_job}`,
        state_transition: row.context_bucket.next_sentence_id
          ? `Preserve ${row.sentence_id}; source order continues to ${row.context_bucket.next_sentence_id}.`
          : `Preserve ${row.sentence_id}; this is the final source sentence.`,
        syntax_tokens: syntax,
        feature_values: [
          paragraphIndex,
          index + 1,
          localIndex,
          row.slots.length,
          bytes.length,
          roleIndex.get(row.role.family),
        ],
        policy: 'allow',
        evidence_hashes: [row.source_utf8_sha256],
        provenance_hashes: [inputs.result.source_sha256, inputs.hashes.rows],
      },
      codec
    );
    previous = row.sentence_id;
  }
  const verification = verifyReasoningArtifactGraph(graph, { codec });
  if (!verification.ok) throw new Error(`reasoning graph failed: ${verification.errors[0]}`);
  return { graph, verification };
}

function buildConceptGraph(inputs, reasoningGraph) {
  const bubbleMap = new Map();
  const addMembership = ({ id, label, row, authority, status, evidenceHashes }) => {
    const existing = bubbleMap.get(id) ?? {
      schema_version: 'scbe.concept_bubble.v1',
      id,
      label,
      parent_bubble_ids: [],
      memberships: [],
      provenance_hashes: [inputs.result.source_sha256, inputs.hashes.rows],
    };
    if (!existing.memberships.some((member) => member.artifact_id === row.sentence_id)) {
      existing.memberships.push({
        artifact_id: row.sentence_id,
        weight: status === 'hypothesis' ? 0.5 : 1,
        authority,
        status,
        evidence_hashes: uniqueSorted(evidenceHashes),
      });
    }
    bubbleMap.set(id, existing);
  };

  for (const row of inputs.rows) {
    addMembership({
      id: `role:${slug(row.role.family)}`,
      label: `Rhetorical role: ${row.role.family}`,
      row,
      authority: 'source-annotation',
      status: 'source',
      evidenceHashes: [row.source_utf8_sha256],
    });
    addMembership({
      id: `paragraph:${row.paragraph_id}`,
      label: `Source paragraph ${row.paragraph_id}`,
      row,
      authority: 'source-annotation',
      status: 'source',
      evidenceHashes: [row.source_utf8_sha256],
    });
    for (const slot of row.slots) {
      addMembership({
        id: `phrase-function:${slug(slot.function)}`,
        label: `Phrase function: ${slot.function}`,
        row,
        authority: 'source-annotation',
        status: 'source',
        evidenceHashes: [row.source_utf8_sha256, hashReasoningValue(slot)],
      });
    }
    const lowered = row.source_text.toLowerCase();
    for (const rule of themeRules) {
      const matches = rule.terms.filter((term) => lowered.includes(term));
      if (matches.length === 0) continue;
      addMembership({
        id: `theme:${rule.id}`,
        label: rule.label,
        row,
        authority: 'deterministic-rule',
        status: 'hypothesis',
        evidenceHashes: [
          row.source_utf8_sha256,
          hashReasoningValue({ rule: rule.id, terms: rule.terms, matches }),
        ],
      });
    }
  }

  const bubbles = [...bubbleMap.values()];
  const roleBubbleIds = bubbles
    .filter((item) => item.id.startsWith('role:'))
    .map((item) => item.id);
  const phraseBubbleIds = bubbles
    .filter((item) => item.id.startsWith('phrase-function:'))
    .map((item) => item.id);
  const themeBubbleIds = bubbles
    .filter((item) => item.id.startsWith('theme:'))
    .map((item) => item.id);
  const fields = [
    {
      schema_version: 'scbe.topic_field.v1',
      id: 'essay',
      label: 'Hoard of Thoughts',
      parent_field_id: null,
      bubble_ids: [],
      provenance_hashes: [inputs.result.source_sha256],
    },
    {
      schema_version: 'scbe.topic_field.v1',
      id: 'rhetoric',
      label: 'Source-authored rhetorical roles',
      parent_field_id: 'essay',
      bubble_ids: roleBubbleIds,
      provenance_hashes: [inputs.result.source_sha256],
    },
    {
      schema_version: 'scbe.topic_field.v1',
      id: 'phrase-functions',
      label: 'Source-authored phrase functions',
      parent_field_id: 'rhetoric',
      bubble_ids: phraseBubbleIds,
      provenance_hashes: [inputs.result.source_sha256],
    },
    {
      schema_version: 'scbe.topic_field.v1',
      id: 'paragraphs',
      label: 'Source paragraph regions',
      parent_field_id: 'essay',
      bubble_ids: [],
      provenance_hashes: [inputs.result.source_sha256],
    },
    ...inputs.paragraphs.map((paragraph) => ({
      schema_version: 'scbe.topic_field.v1',
      id: `field:${paragraph.paragraph_id}`,
      label: `${paragraph.paragraph_id}: ${paragraph.title}`,
      parent_field_id: 'paragraphs',
      bubble_ids: [`paragraph:${paragraph.paragraph_id}`],
      provenance_hashes: [paragraph.utf8_sha256, inputs.result.source_sha256],
    })),
    {
      schema_version: 'scbe.topic_field.v1',
      id: 'themes',
      label: 'Deterministic theme proposals',
      parent_field_id: 'essay',
      bubble_ids: themeBubbleIds,
      provenance_hashes: [hashReasoningValue(themeRules), inputs.result.source_sha256],
    },
  ];

  const edges = [];
  const edgeKeys = new Set();
  const rowMap = new Map(inputs.rows.map((row) => [row.sentence_id, row]));
  const addEdge = (from, to, relation, cost, rule) => {
    if (!from || !to || from === to) return;
    const key = `${from}|${to}|${relation}`;
    if (edgeKeys.has(key)) return;
    edgeKeys.add(key);
    const fromRow = rowMap.get(from);
    const toRow = rowMap.get(to);
    edges.push({
      schema_version: 'scbe.typed_concept_edge.v1',
      id: `edge:${String(edges.length + 1).padStart(4, '0')}`,
      from_artifact_id: from,
      to_artifact_id: to,
      relation,
      cost,
      authority: relation === 'transitions' ? 'source-annotation' : 'deterministic-rule',
      status: 'source',
      evidence_hashes: uniqueSorted([
        fromRow.source_utf8_sha256,
        toRow.source_utf8_sha256,
        hashReasoningValue({ rule, from, to, relation }),
      ]),
    });
  };

  for (const row of inputs.rows) {
    addEdge(
      row.sentence_id,
      row.context_bucket.next_sentence_id,
      'transitions',
      1,
      'source next_sentence_id'
    );
  }

  for (const paragraph of inputs.paragraphs) {
    const rows = paragraph.sentence_ids.map((id) => rowMap.get(id));
    const topics = rows.filter((row) => row.role.family === 'topic_sentence');
    const firstClaim = rows.find((row) => row.role.family === 'claim');
    if (topics.length && firstClaim) {
      addEdge(
        topics.at(-1).sentence_id,
        firstClaim.sentence_id,
        'enables',
        0.9,
        'last topic sentence enables first claim'
      );
    }
    let activeClaim = null;
    let latestEvidence = null;
    for (const row of rows) {
      if (row.role.family === 'claim') {
        activeClaim = row;
        latestEvidence = null;
      } else if (row.role.family === 'evidence_example' && activeClaim) {
        addEdge(
          activeClaim.sentence_id,
          row.sentence_id,
          'requires',
          1.1,
          'claim requires evidence'
        );
        addEdge(
          row.sentence_id,
          activeClaim.sentence_id,
          'supports',
          0.8,
          'evidence supports claim'
        );
        latestEvidence = row;
      } else if (row.role.family === 'explanation_significance' && activeClaim) {
        if (latestEvidence) {
          addEdge(
            latestEvidence.sentence_id,
            row.sentence_id,
            'enables',
            0.9,
            'evidence enables its explanation'
          );
        }
        addEdge(
          row.sentence_id,
          activeClaim.sentence_id,
          'explains',
          0.9,
          'explanation interprets claim'
        );
        addEdge(
          activeClaim.sentence_id,
          row.sentence_id,
          'elaborates',
          0.9,
          'claim expands into explanation'
        );
      }
    }
    const conclusion = rows.find((row) => row.role.family === 'paragraph_conclusion');
    if (conclusion && topics.length) {
      addEdge(
        conclusion.sentence_id,
        topics[0].sentence_id,
        'returns_to',
        0.7,
        'paragraph conclusion returns to topic'
      );
      addEdge(
        conclusion.sentence_id,
        'P1.19',
        'returns_to',
        0.7,
        'body conclusion returns to essay thesis'
      );
    }
  }

  for (const id of ['P1.16', 'P1.17', 'P1.18']) {
    addEdge(id, 'P1.19', 'contradicts', 1, 'outside position is answered by thesis');
    addEdge('P1.19', id, 'requires', 1.1, 'thesis engages an outside position');
  }
  addEdge('P5.01', 'P1.19', 'returns_to', 0.7, 'thesis revisit returns to original thesis');
  addEdge('P5.13', 'P1.19', 'returns_to', 0.7, 'final insight returns to original thesis');

  const graph = createConceptFieldGraph('essay-concept-fields-20261023', reasoningGraph, {
    bubbles,
    fields,
    edges,
  });
  const verification = verifyConceptFieldGraph(graph, reasoningGraph);
  if (!verification.ok) throw new Error(`concept graph failed: ${verification.errors[0]}`);
  return { graph, verification, themeRules };
}

function relationTasks(conceptGraph) {
  const outgoing = new Map();
  for (const edge of conceptGraph.edges) {
    const rows = outgoing.get(edge.from_artifact_id) ?? [];
    rows.push(edge);
    outgoing.set(edge.from_artifact_id, rows);
  }
  const tasks = [];
  for (const [source, edges] of [...outgoing.entries()].sort()) {
    const relations = uniqueSorted(edges.map((edge) => edge.relation));
    const targets = uniqueSorted(edges.map((edge) => edge.to_artifact_id));
    if (relations.length < 2 || targets.length < 2) continue;
    for (const relation of relations) {
      const desired = edges.filter((edge) => edge.relation === relation);
      desired.sort(
        (left, right) =>
          left.cost - right.cost ||
          left.to_artifact_id.localeCompare(right.to_artifact_id) ||
          left.id.localeCompare(right.id)
      );
      tasks.push({
        id: `relation-task:${String(tasks.length + 1).padStart(3, '0')}`,
        source_artifact_id: source,
        desired_relation: relation,
        candidate_artifact_ids: targets,
        expected_edge_id: desired[0].id,
        expected_artifact_id: desired[0].to_artifact_id,
      });
    }
  }
  return tasks;
}

function routeForTask(task, graph, reasoningGraph, typed) {
  const multipliers = {};
  if (typed) {
    for (const relation of CONCEPT_RELATIONS) multipliers[relation] = 4;
    multipliers[task.desired_relation] = 0.25;
  }
  return planConceptRoute(graph, reasoningGraph, {
    id: `${task.id}:${typed ? 'typed' : 'untyped'}`,
    public_goal: `Select the next public artifact whose relation ${relationDescriptions[task.desired_relation]}.`,
    start_artifact_ids: [task.source_artifact_id],
    target_artifact_ids: task.candidate_artifact_ids,
    relation_multipliers: multipliers,
    allow_bubble_hops: false,
    verified_only: true,
    max_hops: 1,
  });
}

function flatChoice(task, reasoningGraph) {
  const source = reasoningGraph.nodes[task.source_artifact_id];
  const query = tokenize(
    `${relationDescriptions[task.desired_relation]} ${source.public_summary} ${source.state_transition}`
  );
  return [...task.candidate_artifact_ids]
    .map((id) => {
      const node = reasoningGraph.nodes[id];
      return {
        id,
        score: jaccard(
          query,
          tokenize(
            `${node.public_summary} ${node.state_transition} ${node.syntax_tokens.join(' ')}`
          )
        ),
      };
    })
    .sort((left, right) => right.score - left.score || left.id.localeCompare(right.id))[0].id;
}

function evaluateControls(conceptGraph, reasoningGraph) {
  const tasks = relationTasks(conceptGraph);
  if (tasks.length < 20)
    throw new Error(`relation control is underpowered: only ${tasks.length} tasks`);
  let typedCorrect = 0;
  let untypedCorrect = 0;
  let flatCorrect = 0;
  const taskRows = [];
  for (const task of tasks) {
    const typed = routeForTask(task, conceptGraph, reasoningGraph, true);
    const replay = routeForTask(task, conceptGraph, reasoningGraph, true);
    if (typed.route_sha256 !== replay.route_sha256)
      throw new Error(`route replay drift: ${task.id}`);
    const untyped = routeForTask(task, conceptGraph, reasoningGraph, false);
    const flat = flatChoice(task, reasoningGraph);
    const typedChoice = typed.target_artifact_id;
    const untypedChoice = untyped.target_artifact_id;
    const typedEdge = typed.hops[0]?.edge_id ?? null;
    const untypedEdge = untyped.hops[0]?.edge_id ?? null;
    typedCorrect += Number(typedEdge === task.expected_edge_id);
    untypedCorrect += Number(untypedEdge === task.expected_edge_id);
    flatCorrect += Number(flat === task.expected_artifact_id);
    taskRows.push({
      ...task,
      typed_choice: typedChoice,
      typed_edge_id: typedEdge,
      untyped_choice: untypedChoice,
      untyped_edge_id: untypedEdge,
      flat_choice: flat,
    });
  }

  const seeds = [1301, 1302, 1303, 1304, 1305, 1306, 1307, 1308];
  const originalLabels = conceptGraph.edges.map((edge) => edge.relation);
  const shuffledRuns = seeds.map((seed) => {
    const labels = shuffled(originalLabels, seed);
    const shuffledGraph = createConceptFieldGraph(`essay-concept-shuffle-${seed}`, reasoningGraph, {
      bubbles: conceptGraph.bubbles,
      fields: conceptGraph.fields,
      edges: conceptGraph.edges.map((edge, index) => ({ ...edge, relation: labels[index] })),
    });
    const correct = tasks.reduce((sum, task) => {
      const route = routeForTask(task, shuffledGraph, reasoningGraph, true);
      return sum + Number(route.hops[0]?.edge_id === task.expected_edge_id);
    }, 0);
    return { seed, correct, total: tasks.length, accuracy: correct / tasks.length };
  });

  const typedAccuracy = typedCorrect / tasks.length;
  const untypedAccuracy = untypedCorrect / tasks.length;
  const flatAccuracy = flatCorrect / tasks.length;
  const shuffledAccuracies = shuffledRuns.map((row) => row.accuracy);
  const shuffledMean = mean(shuffledAccuracies);
  const shuffledSd = sampleSd(shuffledAccuracies);
  const pooledSd = Math.sqrt((0 ** 2 + shuffledSd ** 2) / 2);
  const gate =
    typedAccuracy > flatAccuracy &&
    typedAccuracy > untypedAccuracy &&
    typedAccuracy - shuffledMean > 2 * pooledSd;
  return {
    schema: 'nested_concept_field_control_v1',
    scope: 'deterministic relation-routing conformance; not a model reasoning benchmark',
    task_count: tasks.length,
    typed: { correct: typedCorrect, total: tasks.length, accuracy: typedAccuracy },
    flat_lexical: { correct: flatCorrect, total: tasks.length, accuracy: flatAccuracy },
    untyped_equal_cost: {
      correct: untypedCorrect,
      total: tasks.length,
      accuracy: untypedAccuracy,
    },
    shuffled_relation_labels: {
      same_nodes_edges_and_relation_histogram: true,
      runs: shuffledRuns,
      mean_accuracy: shuffledMean,
      sample_sd: shuffledSd,
    },
    claim_rule: {
      rule: 'typed must beat flat, untyped, and shuffled mean by more than 2 pooled SD',
      typed_minus_shuffled_mean: typedAccuracy - shuffledMean,
      two_pooled_sd: 2 * pooledSd,
      passed: gate,
      interpretation: gate
        ? 'Typed relation labels control one-hop public routing as designed on this source-derived mechanism test.'
        : 'UNDERPOWERED OR NOT ESTABLISHED: typed routing did not clear every preregistered control.',
    },
    tasks: taskRows,
  };
}

function buildRouteDemos(conceptGraph, reasoningGraph) {
  const goals = [
    {
      id: 'evidence-to-explanation',
      public_goal: 'Follow source-backed support into the first explanation, preserving the route.',
      start_artifact_ids: ['P2.03'],
      target_artifact_ids: ['P2.06'],
      relation_multipliers: { transitions: 0.2, requires: 10, elaborates: 10 },
      allow_bubble_hops: false,
      verified_only: true,
    },
    {
      id: 'return-to-thesis',
      public_goal: 'Return from the Body 3 conclusion to the source thesis.',
      start_artifact_ids: ['P4.15'],
      target_artifact_ids: ['P1.19'],
      relation_multipliers: { returns_to: 0.25 },
      allow_bubble_hops: false,
      verified_only: true,
    },
    {
      id: 'strict-theme-refusal',
      public_goal:
        'Reach the proposed memory theme using source or externally verified membership only.',
      start_artifact_ids: ['P1.01'],
      target_bubble_ids: ['theme:memory'],
      allow_bubble_hops: true,
      verified_only: true,
      max_hops: 12,
    },
    {
      id: 'exploratory-theme-route',
      public_goal:
        'Explore the deterministic memory-theme proposal without upgrading it to verified evidence.',
      start_artifact_ids: ['P1.01'],
      target_bubble_ids: ['theme:memory'],
      allow_bubble_hops: false,
      verified_only: false,
      max_hops: 32,
    },
    {
      id: 'paragraph-hyperedge',
      public_goal: 'Use the source paragraph as an explicit overlapping concept bubble.',
      start_artifact_ids: ['P4.03'],
      target_artifact_ids: ['P4.14'],
      allow_bubble_hops: true,
      bubble_hop_cost: 0.25,
      verified_only: true,
    },
  ];
  return goals.map((goal) => {
    const route = planConceptRoute(conceptGraph, reasoningGraph, goal);
    const verification = verifyConceptRoute(route, conceptGraph, reasoningGraph);
    if (!verification.ok)
      throw new Error(`route demo failed: ${goal.id}: ${verification.errors[0]}`);
    return route;
  });
}

function runTamperChecks(conceptGraph, reasoningGraph) {
  const malformed = structuredClone(conceptGraph);
  malformed.bubbles[0].memberships[0].weight = 2;
  const { graph_sha256: _old, ...body } = malformed;
  malformed.graph_sha256 = hashReasoningValue(body);
  const malformedCheck = verifyConceptFieldGraph(malformed, reasoningGraph);

  const hashTamper = structuredClone(conceptGraph);
  hashTamper.edges[0].cost = 99;
  const hashCheck = verifyConceptFieldGraph(hashTamper, reasoningGraph);
  return {
    recomputed_hash_malformed_value_rejected:
      !malformedCheck.ok &&
      malformedCheck.errors.some((error) => error.includes('membership weight must be in (0, 1]')),
    direct_hash_tamper_rejected:
      !hashCheck.ok && hashCheck.errors.includes('concept field graph hash mismatch'),
    malformed_errors: malformedCheck.errors,
    hash_tamper_errors: hashCheck.errors,
  };
}

function htmlDocument(inputs, reasoningGraph, conceptGraph, routes, controls) {
  const payload = {
    rows: inputs.rows.map((row) => ({
      id: row.sentence_id,
      paragraph: row.paragraph_id,
      text: row.source_text,
      role: row.role.family,
      map_job: row.map_job,
      slots: row.slots.map((slot) => ({ function: slot.function, phrase: slot.phrase })),
      tongue: reasoningGraph.nodes[row.sentence_id].tongue,
      view_tokens: reasoningGraph.nodes[row.sentence_id].view_tokens,
    })),
    fields: conceptGraph.fields,
    bubbles: conceptGraph.bubbles,
    edges: conceptGraph.edges,
    routes: routes.map((route) => ({
      id: route.route_id,
      status: route.status,
      rejection_code: route.rejection_code,
      path: route.artifact_path,
      hops: route.hops,
    })),
    controls: {
      task_count: controls.task_count,
      typed: controls.typed.accuracy,
      flat: controls.flat_lexical.accuracy,
      untyped: controls.untyped_equal_cost.accuracy,
      shuffled: controls.shuffled_relation_labels.mean_accuracy,
      gate: controls.claim_rule.passed,
    },
  };
  const embedded = JSON.stringify(payload).replaceAll('<', '\\u003c');
  return `<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nested Concept Fields · Hoard of Thoughts</title>
<style>
:root{color-scheme:dark;--bg:#081018;--panel:#101c29;--ink:#e9f2fa;--muted:#9eb1c2;--line:#31506a;--source:#55d6be;--hyp:#f5b942;--accent:#75a7ff}*{box-sizing:border-box}body{margin:0;font:15px/1.45 system-ui,sans-serif;background:radial-gradient(circle at 20% 0,#16304a,var(--bg) 45%);color:var(--ink)}header{padding:18px 22px;border-bottom:1px solid var(--line);position:sticky;top:0;background:#081018ed;z-index:3}h1{font-size:22px;margin:0 0 4px}p{margin:5px 0;color:var(--muted)}main{display:grid;grid-template-columns:minmax(520px,2fr) minmax(300px,1fr);gap:12px;padding:12px}.panel{background:#101c29e8;border:1px solid var(--line);border-radius:12px;padding:12px;min-width:0}.controls{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}select,button{background:#0b1520;color:var(--ink);border:1px solid var(--line);border-radius:7px;padding:7px}svg{width:100%;height:720px;background:#07111b;border-radius:9px}.edge{stroke:#35506a;stroke-width:1;opacity:.36;fill:none}.edge.route{stroke:#f7d774;stroke-width:3;opacity:1}.node{stroke:#081018;stroke-width:2;cursor:pointer}.node.route{stroke:#fff;stroke-width:4}.label{fill:#b9c9d8;font-size:9px;pointer-events:none}.pill{display:inline-block;padding:3px 7px;margin:2px;border-radius:99px;background:#172a3b;color:#c9dae8}.source{color:var(--source)}.hyp{color:var(--hyp)}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#07111b;border-radius:8px;padding:10px;color:#cfe2f1}.metric{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.metric div{padding:7px;background:#07111b;border-radius:7px;text-align:center}.small{font-size:12px}@media(max-width:900px){main{grid-template-columns:1fr}svg{height:620px}}
</style></head><body><header><h1>Nested concept fields · public reasoning route</h1><p>84 preserved sentences, overlapping source roles, typed links, nested fields, and replayable receipts. Theme bubbles remain hypotheses.</p></header>
<main><section class="panel"><div class="metric" id="metrics"></div><div class="controls"><label>Field <select id="field"></select></label><label>Bubble <select id="bubble"></select></label><label>Route <select id="route"></select></label><button id="reset">Reset</button></div><svg id="graph" viewBox="0 0 900 720" aria-label="sentence graph"></svg></section><aside class="panel"><h2 id="title">Select a sentence</h2><p id="meta"></p><div id="tags"></div><pre id="text">Tap a node to inspect its source sentence, phrase functions, and exact tongue view.</pre><h3>Route receipt</h3><pre id="receipt">Select a route above.</pre></aside></main>
<script>const D=${embedded};const svg=document.querySelector('#graph'),field=document.querySelector('#field'),bubble=document.querySelector('#bubble'),route=document.querySelector('#route');const NS='http://www.w3.org/2000/svg';const rowById=new Map(D.rows.map(r=>[r.id,r]));const roleColors=['#55d6be','#75a7ff','#f5b942','#df77ff','#ff7f6e','#8bd450','#5fd4ff','#f08bb4'];const roles=[...new Set(D.rows.map(r=>r.role))].sort();const color=r=>roleColors[roles.indexOf(r)%roleColors.length];const pos=new Map();for(const r of D.rows){const p=Number(r.paragraph.slice(1)),n=Number(r.id.split('.')[1]);const count=D.rows.filter(x=>x.paragraph===r.paragraph).length;pos.set(r.id,{x:90+(p-1)*180,y:45+n*(630/(count+1))});}function el(name,attrs={}){const e=document.createElementNS(NS,name);for(const[k,v]of Object.entries(attrs))e.setAttribute(k,v);return e}function option(sel,value,label){const o=document.createElement('option');o.value=value;o.textContent=label;sel.append(o)}option(field,'','All fields');for(const f of D.fields)option(field,f.id,f.label);option(bubble,'','All bubbles');for(const b of D.bubbles)option(bubble,b.id,b.label);option(route,'','No route');for(const r of D.routes)option(route,r.id,r.id+' · '+r.status);document.querySelector('#metrics').innerHTML=[['typed',D.controls.typed],['flat',D.controls.flat],['untyped',D.controls.untyped],['shuffled',D.controls.shuffled]].map(([k,v])=>'<div><b>'+Math.round(v*100)+'%</b><br><span class="small">'+k+'</span></div>').join('');function selectedIds(){let ids=new Set(D.rows.map(r=>r.id));if(bubble.value){const b=D.bubbles.find(x=>x.id===bubble.value);ids=new Set(b?.memberships.map(m=>m.artifact_id)||[])}if(field.value){const descendants=new Set([field.value]);let change=true;while(change){change=false;for(const f of D.fields)if(f.parent_field_id&&descendants.has(f.parent_field_id)&&!descendants.has(f.id)){descendants.add(f.id);change=true}}const bids=new Set(D.fields.filter(f=>descendants.has(f.id)).flatMap(f=>f.bubble_ids));const fids=new Set(D.bubbles.filter(b=>bids.has(b.id)).flatMap(b=>b.memberships.map(m=>m.artifact_id)));ids=new Set([...ids].filter(id=>fids.has(id)))}return ids}function draw(){svg.textContent='';const ids=selectedIds(),rr=D.routes.find(r=>r.id===route.value),rp=new Set(rr?.path||[]),rh=new Set((rr?.hops||[]).map(h=>h.from_artifact_id+'|'+h.to_artifact_id));for(const e of D.edges){if(!ids.has(e.from_artifact_id)||!ids.has(e.to_artifact_id))continue;const a=pos.get(e.from_artifact_id),b=pos.get(e.to_artifact_id);const line=el('path',{d:'M'+a.x+','+a.y+' Q'+((a.x+b.x)/2)+','+(Math.min(a.y,b.y)-18)+' '+b.x+','+b.y,class:'edge '+(rh.has(e.from_artifact_id+'|'+e.to_artifact_id)?'route':'')});const t=el('title');t.textContent=e.relation;line.append(t);svg.append(line)}for(const r of D.rows){if(!ids.has(r.id))continue;const p=pos.get(r.id),c=el('circle',{cx:p.x,cy:p.y,r:rp.has(r.id)?10:7,fill:color(r.role),class:'node '+(rp.has(r.id)?'route':'')});c.onclick=()=>show(r.id);const t=el('title');t.textContent=r.id+' · '+r.role;c.append(t);svg.append(c);const lab=el('text',{x:p.x+10,y:p.y+3,class:'label'});lab.textContent=r.id;svg.append(lab)}}function show(id){const r=rowById.get(id),members=D.bubbles.filter(b=>b.memberships.some(m=>m.artifact_id===id));document.querySelector('#title').textContent=id+' · '+r.role;document.querySelector('#meta').textContent=r.map_job+' · '+r.tongue+' view · '+new TextEncoder().encode(r.text).length+' bytes';document.querySelector('#tags').innerHTML=members.map(b=>'<span class="pill '+(b.memberships.find(m=>m.artifact_id===id).status==='hypothesis'?'hyp':'source')+'">'+b.label+'</span>').join('');document.querySelector('#text').textContent=r.text+'\\n\\nPhrase functions:\\n'+r.slots.map(s=>'• '+s.function+': '+s.phrase).join('\\n')+'\\n\\nExact '+r.tongue+' tokens (first 24):\\n'+r.view_tokens.slice(0,24).join(' ')+(r.view_tokens.length>24?' …':'')}function showRoute(){const r=D.routes.find(x=>x.id===route.value);document.querySelector('#receipt').textContent=r?JSON.stringify(r,null,2):'Select a route above.';draw()}field.onchange=draw;bubble.onchange=draw;route.onchange=showRoute;document.querySelector('#reset').onclick=()=>{field.value='';bubble.value='';route.value='';draw()};draw();show(D.rows[0].id);</script></body></html>`;
}

function verifyInlineScript(html) {
  const match = /<script>([\s\S]*)<\/script>/.exec(html);
  if (!match) throw new Error('interactive HTML has no inline script');
  new vm.Script(match[1], { filename: 'concept_fields.inline.js' });
}

function markdownDocuments(inputs, sourceDirectory, conceptGraph, routes, controls, tamperChecks) {
  const routeLines = routes
    .map(
      (route) =>
        `- \`${route.route_id}\`: ${route.status}${route.rejection_code ? ` (${route.rejection_code})` : ''}; ${route.artifact_path.join(' → ') || 'no admitted path'}`
    )
    .join('\n');
  const readme = `# Nested concept fields — 23 October 2026

This packet binds Issac's 84-sentence **Hoard of Thoughts** sentence-function lattice to the public reasoning-artifact graph. It implements overlapping concept bubbles, nested topic fields, typed directed relations, deterministic goal-conditioned routing, and hash-chained route receipts.

It does **not** expose private chain of thought. The recorded steps are source sentences, public summaries, declared relations, and deterministic state transitions.

## Result

- Source sentences: **${inputs.rows.length}**
- Reasoning artifacts: **${inputs.rows.length}**
- Concept bubbles: **${conceptGraph.bubbles.length}**
- Nested topic fields: **${conceptGraph.fields.length}**
- Typed edges: **${conceptGraph.edges.length}**
- Mechanism tasks: **${controls.task_count}**
- Typed route accuracy: **${(controls.typed.accuracy * 100).toFixed(1)}%**
- Flat lexical baseline: **${(controls.flat_lexical.accuracy * 100).toFixed(1)}%**
- Untyped equal-cost baseline: **${(controls.untyped_equal_cost.accuracy * 100).toFixed(1)}%**
- Shuffled-label mean: **${(controls.shuffled_relation_labels.mean_accuracy * 100).toFixed(1)}% ± ${(controls.shuffled_relation_labels.sample_sd * 100).toFixed(1)}%** across ${controls.shuffled_relation_labels.runs.length} seeds
- Preregistered claim rule: **${controls.claim_rule.passed ? 'PASS' : 'UNDERPOWERED / NOT ESTABLISHED'}**

The passed claim is narrow: **typed relation labels control deterministic public routing on this source-derived mechanism test**. This packet does not show improved language-model reasoning, generalization, or training gains.

## Route demonstrations

${routeLines}

Open [concept_fields.html](concept_fields.html) for the offline interactive view. Select fields, bubbles, routes, and sentence nodes. Theme bubbles are amber hypotheses; source annotations are green.

## Reproduce

From \`packages/agent-bus\`:

\`\`\`powershell
npm run build
node scripts/build_nested_concept_fields.mjs --source "${sourceDirectory}"
node scripts/build_nested_concept_fields.mjs --verify
\`\`\`
`;
  const systemMap = `# System map

\`\`\`text
DOCX source (SHA-256 bound)
  ↓ sentence-function lattice: exact text, roles, phrase spans
public reasoning-artifact DAG
  ├─ canonical UTF-8 hash
  ├─ one exact KO/AV/RU/CA/UM/DR byte view per node
  ├─ public summary + state transition
  └─ event hash chain
  ↓ exact artifact ids + verified graph digest
nested concept-field graph
  ├─ source role bubbles (overlapping)
  ├─ source phrase-function bubbles (overlapping)
  ├─ paragraph fields (nested)
  ├─ deterministic theme proposals (hypothesis only)
  └─ typed source-derived edges
  ↓ goal + admitted evidence policy
deterministic Dijkstra route
  ├─ relation-specific positive costs
  ├─ source/verified-only gate
  ├─ allow-policy gate
  ├─ stable E_NO_ROUTE refusal
  └─ per-hop hash receipt
  ↓
public route / visualization / replay verifier
\`\`\`

The six tongues are reversible addresses and integrity views. They are not six independent semantic votes. Theme lexicons propose memberships but cannot enter a strict route until an external check changes their evidence status.
`;
  const math = String.raw`# Math ledger

Let \(V\) be the 84 source-bound public artifacts, \(E\) the typed directed edges, \(B\) the overlapping concept bubbles, and \(F\) the acyclic topic-field hierarchy.

## Canonical identity and tongue view

For sentence bytes \(x_i\) and tongue permutation \(\sigma_k\):

\[v_{i,k}=\sigma_k(x_i), \qquad \sigma_k^{-1}(v_{i,k})=x_i.\]

The round trip proves representation integrity only.

## Overlapping membership

\[M(v_i)=\{(b,w,a,s,H):v_i\in b\}.\]

Here \(w\in(0,1]\), \(a\) is authority, \(s\in\{source,verified,hypothesis,rejected\}\), and \(H\) is the receipt-hash set. One sentence may occupy several bubbles.

## Goal-conditioned edge cost

For edge \(e\) with relation \(r(e)\), positive base cost \(c(e)\), and goal multiplier \(g_r>0\):

\[c_G(e)=c(e)g_{r(e)}.\]

The selected route is

\[P^*=\arg\min_{P:s\leadsto T}\sum_{e\in P}c_G(e),\]

with lexical artifact-id order as the deterministic tie-break. Dijkstra is valid because every admitted cost is positive.

## Bubble hop

A bubble is an explicit hyperedge. If two artifacts have admitted memberships in the same bubble, the router may add a \(co\_member\) hop at the goal's declared bubble cost. No geometric closeness creates an edge.

## Receipt chain

\[h_0=H(goal, reasoning\_graph, concept\_graph),\qquad h_j=H(h_{j-1},e_j,c_j,C_j).\]

Changing a hop, cost, graph, or goal changes the route digest. Replanning from the normalized goal must reproduce the same digest.

## Control rule

Typed routing must beat the flat baseline and untyped baseline, and

\[A_{typed}-\bar A_{shuffle}>2s_{pooled}.\]

Observed: \(${controls.typed.accuracy.toFixed(4)}-${controls.shuffled_relation_labels.mean_accuracy.toFixed(4)}=${(controls.typed.accuracy - controls.shuffled_relation_labels.mean_accuracy).toFixed(4)}\); threshold \(${controls.claim_rule.two_pooled_sd.toFixed(4)}\).
`;
  const boundary = `# Source and claim boundary

## Directly source-bound

- Sentence bytes and SHA-256 digests.
- Paragraph, rhetorical-role, map-job, and phrase-function annotations from the supplied guide.
- Previous/next source order.

## Deterministic derivations

- Claim/evidence/explanation edges derived from those source roles.
- Route selection, tie-breaking, receipts, and replay.
- Keyword theme matches.

## Hypotheses

- Theme meaning beyond literal keyword matches. These memberships remain \`hypothesis\` and strict routes exclude them.

## Established here

- ${controls.claim_rule.interpretation}
- Exact route replay and byte-view round trips passed.
- Hash tampering and hash-consistent malformed membership were rejected: **${tamperChecks.direct_hash_tamper_rejected && tamperChecks.recomputed_hash_malformed_value_rejected ? 'PASS' : 'FAIL'}**.

## Not established

- Better model reasoning, writing, truth, or generalization.
- Faithful access to hidden model reasoning.
- Independent evidence from six deterministic encodings.
- A training benefit for Clay.
`;
  return {
    'README.md': readme,
    'SYSTEM_MAP.md': systemMap,
    'MATH_LEDGER.md': math,
    'SOURCE_AND_CLAIM_BOUNDARY.md': boundary,
  };
}

function buildManifest(outputDirectory) {
  const names = fs
    .readdirSync(outputDirectory)
    .filter((name) => name !== 'MANIFEST.sha256')
    .sort();
  const lines = names.map((name) => `${sha256File(path.join(outputDirectory, name))}  ${name}`);
  fs.writeFileSync(path.join(outputDirectory, 'MANIFEST.sha256'), `${lines.join('\n')}\n`, 'utf8');
}

function verifyManifest(outputDirectory) {
  const manifestPath = path.join(outputDirectory, 'MANIFEST.sha256');
  const failures = [];
  for (const line of fs.readFileSync(manifestPath, 'utf8').split(/\r?\n/).filter(Boolean)) {
    const match = /^([a-f0-9]{64})  (.+)$/.exec(line);
    if (!match) {
      failures.push(`malformed manifest line: ${line}`);
      continue;
    }
    const filePath = path.join(outputDirectory, match[2]);
    if (!fs.existsSync(filePath)) failures.push(`missing: ${match[2]}`);
    else if (sha256File(filePath) !== match[1]) failures.push(`hash mismatch: ${match[2]}`);
  }
  return failures;
}

function verifyOutput(outputDirectory, sourceDirectory) {
  const inputs = loadInputs(sourceDirectory);
  const codec = buildCodec(inputs.tongueDocument);
  const reasoning = readJson(path.join(outputDirectory, 'REASONING_ARTIFACT_GRAPH.json'));
  const concepts = readJson(path.join(outputDirectory, 'CONCEPT_FIELD_GRAPH.json'));
  const routes = readJson(path.join(outputDirectory, 'ROUTE_DEMOS.json'));
  const errors = verifyManifest(outputDirectory);
  try {
    verifyInlineScript(fs.readFileSync(path.join(outputDirectory, 'concept_fields.html'), 'utf8'));
  } catch (error) {
    errors.push(`interactive HTML: ${error instanceof Error ? error.message : String(error)}`);
  }
  const reasoningCheck = verifyReasoningArtifactGraph(reasoning, { codec });
  if (!reasoningCheck.ok)
    errors.push(...reasoningCheck.errors.map((error) => `reasoning: ${error}`));
  const conceptCheck = verifyConceptFieldGraph(concepts, reasoning);
  if (!conceptCheck.ok) errors.push(...conceptCheck.errors.map((error) => `concept: ${error}`));
  for (const route of routes) {
    const check = verifyConceptRoute(route, concepts, reasoning);
    if (!check.ok) errors.push(...check.errors.map((error) => `route ${route.route_id}: ${error}`));
  }
  return { ok: errors.length === 0, errors, files: fs.readdirSync(outputDirectory).length };
}

function main() {
  const options = parseArguments(process.argv.slice(2));
  if (options.verifyOnly) {
    const verification = verifyOutput(options.output, options.source);
    console.log(JSON.stringify(verification, null, 2));
    if (!verification.ok) process.exitCode = 1;
    return;
  }
  const inputs = loadInputs(options.source);
  const codec = buildCodec(inputs.tongueDocument);
  const { graph: reasoningGraph, verification: reasoningVerification } = buildReasoningGraph(
    inputs,
    codec
  );
  const { graph: conceptGraph, verification: conceptVerification } = buildConceptGraph(
    inputs,
    reasoningGraph
  );
  const controls = evaluateControls(conceptGraph, reasoningGraph);
  const routes = buildRouteDemos(conceptGraph, reasoningGraph);
  const tamperChecks = runTamperChecks(conceptGraph, reasoningGraph);
  fs.mkdirSync(options.output, { recursive: true });
  writeJson(path.join(options.output, 'REASONING_ARTIFACT_GRAPH.json'), reasoningGraph);
  writeJson(path.join(options.output, 'CONCEPT_FIELD_GRAPH.json'), conceptGraph);
  writeJson(path.join(options.output, 'ROUTE_DEMOS.json'), routes);
  writeJson(path.join(options.output, 'CONTROL_RESULTS.json'), controls);
  writeJson(path.join(options.output, 'THEME_RULES.json'), themeRules);
  writeJson(
    path.join(options.output, 'SOURCE_INDEX.json'),
    inputs.rows.map((row) => ({
      sentence_id: row.sentence_id,
      source_text: row.source_text,
      source_utf8_sha256: row.source_utf8_sha256,
      role: row.role,
      map_job: row.map_job,
      slots: row.slots,
    }))
  );
  writeJson(path.join(options.output, 'RESULT.json'), {
    schema: 'nested_concept_fields_result_v1',
    built_at: new Date().toISOString(),
    source_directory: options.source,
    source_hashes: inputs.hashes,
    source_document_sha256: inputs.result.source_sha256,
    reasoning_graph_sha256: reasoningVerification.graph_sha256,
    concept_graph_sha256: conceptVerification.graph_sha256,
    sentences: inputs.rows.length,
    bubbles: conceptGraph.bubbles.length,
    fields: conceptGraph.fields.length,
    typed_edges: conceptGraph.edges.length,
    route_demos: routes.length,
    controls: controls,
    tamper_checks: tamperChecks,
    claims: {
      established: [controls.claim_rule.interpretation],
      not_established: [
        'improved model reasoning or generalization',
        'access to private model chain of thought',
        'independent semantic evidence from deterministic tongue views',
        'a training gain for Clay',
      ],
    },
  });
  const interactiveHtml = htmlDocument(inputs, reasoningGraph, conceptGraph, routes, controls);
  verifyInlineScript(interactiveHtml);
  fs.writeFileSync(path.join(options.output, 'concept_fields.html'), interactiveHtml, 'utf8');
  const documents = markdownDocuments(
    inputs,
    options.source,
    conceptGraph,
    routes,
    controls,
    tamperChecks
  );
  for (const [name, value] of Object.entries(documents)) {
    fs.writeFileSync(path.join(options.output, name), value, 'utf8');
  }
  buildManifest(options.output);
  const verification = verifyOutput(options.output, options.source);
  console.log(
    JSON.stringify(
      {
        output: options.output,
        sentences: inputs.rows.length,
        bubbles: conceptGraph.bubbles.length,
        fields: conceptGraph.fields.length,
        edges: conceptGraph.edges.length,
        tasks: controls.task_count,
        typed_accuracy: controls.typed.accuracy,
        flat_accuracy: controls.flat_lexical.accuracy,
        untyped_accuracy: controls.untyped_equal_cost.accuracy,
        shuffled_mean_accuracy: controls.shuffled_relation_labels.mean_accuracy,
        claim_gate: controls.claim_rule.passed,
        verification,
      },
      null,
      2
    )
  );
  if (!verification.ok) process.exitCode = 1;
}

main();
