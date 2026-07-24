import crypto from 'node:crypto';

export const GOVERNED_TASK_SCHEMA_VERSION = 'scbe.governed-task-run.v1' as const;
export const GOVERNED_TASK_STATUSES = [
  'queued',
  'running',
  'completed',
  'failed',
  'cancelled',
] as const;
export const GOVERNED_TASK_DISPOSITIONS = [
  'pending',
  'review_required',
  'failed_evidence_check',
  'failed_execution',
  'cancelled',
] as const;

export type GovernedTaskStatus = (typeof GOVERNED_TASK_STATUSES)[number];
export type GovernedTaskDispositionStatus = (typeof GOVERNED_TASK_DISPOSITIONS)[number];

export interface GovernedTaskCitation {
  source_id?: string;
  title: string;
  url: string;
  content_sha256: string;
  quote: string;
}

export interface GovernedTaskFieldBasis {
  field: string;
  confidence: number;
  citations: GovernedTaskCitation[];
  reasoning: string;
}

export interface GovernedTaskDisposition {
  status: GovernedTaskDispositionStatus;
  negative_example: boolean;
  do_not_promote_to_fact: true;
  reason: string;
}

export interface GovernedTaskSeal {
  kind: string;
  previous_sha256: string;
  payload_sha256: string;
  sha256: string;
}

export interface GovernedTaskRun {
  schema_version: typeof GOVERNED_TASK_SCHEMA_VERSION;
  run_id: string;
  interaction_id: string;
  status: GovernedTaskStatus;
  submitted_at: string;
  started_at: string | null;
  completed_at: string | null;
  input_sha256: string;
  output_sha256?: string;
  result: unknown;
  error: unknown;
  basis: GovernedTaskFieldBasis[];
  metrics: Record<string, unknown>;
  disposition: GovernedTaskDisposition;
  seal?: GovernedTaskSeal;
  completion_seal?: GovernedTaskSeal;
  contract_sha256?: string;
}

export interface GovernedTaskValidation {
  ok: boolean;
  errors: string[];
  run?: GovernedTaskRun;
}

const HASH_RE = /^[a-f0-9]{64}$/;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function sortCanonical(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortCanonical);
  if (isRecord(value)) {
    return Object.keys(value)
      .sort()
      .reduce<Record<string, unknown>>((result, key) => {
        result[key] = sortCanonical(value[key]);
        return result;
      }, {});
  }
  return value;
}

export function canonicalTaskJson(value: unknown): string {
  const encoded = JSON.stringify(sortCanonical(value));
  if (encoded === undefined) throw new TypeError('value is not JSON serializable');
  return encoded;
}

export function sha256TaskValue(value: unknown): string {
  return crypto.createHash('sha256').update(canonicalTaskJson(value), 'utf8').digest('hex');
}

function normalizeDisposition(status: GovernedTaskStatus, value: unknown): GovernedTaskDisposition {
  const source = isRecord(value) ? value : {};
  if (status === 'cancelled' && source.status === 'pending') {
    return {
      status: 'cancelled',
      negative_example: true,
      do_not_promote_to_fact: true,
      reason: 'Cancelled runs are not eligible for factual training.',
    };
  }
  return {
    status: String(source.status || 'pending') as GovernedTaskDispositionStatus,
    negative_example: source.negative_example === true,
    do_not_promote_to_fact: true,
    reason: String(source.reason || 'No evidence disposition was supplied.'),
  };
}

function normalizeBasis(value: unknown): GovernedTaskFieldBasis[] {
  if (!Array.isArray(value)) return [];
  return value.map((entry) => {
    const row = isRecord(entry) ? entry : {};
    const citations = Array.isArray(row.citations)
      ? row.citations.map((citation) => {
          const item = isRecord(citation) ? citation : {};
          return {
            ...(typeof item.source_id === 'string' ? { source_id: item.source_id } : {}),
            title: String(item.title || ''),
            url: String(item.url || ''),
            content_sha256: String(item.content_sha256 || ''),
            quote: String(item.quote || ''),
          };
        })
      : [];
    return {
      field: String(row.field || ''),
      confidence: Number(row.confidence),
      citations,
      reasoning: String(row.reasoning || ''),
    };
  });
}

/**
 * Adapt the Clay Parallel Task Lab response to the package-level contract.
 *
 * The staging server predates this exported schema tag, so the adapter adds
 * only the protocol tag and normalizes cancelled runs. It does not invent
 * evidence, hashes, or a successful disposition.
 */
export function normalizeTaskLabRun(value: unknown): GovernedTaskRun {
  if (!isRecord(value)) throw new TypeError('task run must be an object');
  const status = String(value.status || '') as GovernedTaskStatus;
  const run: GovernedTaskRun = {
    schema_version: GOVERNED_TASK_SCHEMA_VERSION,
    run_id: String(value.run_id || ''),
    interaction_id: String(value.interaction_id || ''),
    status,
    submitted_at: String(value.submitted_at || ''),
    started_at: typeof value.started_at === 'string' ? value.started_at : null,
    completed_at: typeof value.completed_at === 'string' ? value.completed_at : null,
    input_sha256: String(value.input_sha256 || ''),
    ...(typeof value.output_sha256 === 'string' ? { output_sha256: value.output_sha256 } : {}),
    result: value.result ?? null,
    error: value.error ?? null,
    basis: normalizeBasis(value.basis),
    metrics: isRecord(value.metrics) ? value.metrics : {},
    disposition: normalizeDisposition(status, value.disposition),
    ...(isRecord(value.seal) ? { seal: value.seal as unknown as GovernedTaskSeal } : {}),
    ...(isRecord(value.completion_seal)
      ? { completion_seal: value.completion_seal as unknown as GovernedTaskSeal }
      : {}),
  };
  const validation = validateGovernedTaskRun(run);
  if (!validation.ok) {
    throw new TypeError(`invalid governed task run: ${validation.errors.join('; ')}`);
  }
  return run;
}

function validateSeal(value: unknown, path: string, errors: string[]): void {
  if (value === undefined) return;
  if (!isRecord(value)) {
    errors.push(`${path} must be an object`);
    return;
  }
  for (const field of ['previous_sha256', 'payload_sha256', 'sha256']) {
    if (!HASH_RE.test(String(value[field] || ''))) {
      errors.push(`${path}.${field} must be a lowercase SHA-256 digest`);
    }
  }
}

export function validateGovernedTaskRun(value: unknown): GovernedTaskValidation {
  const errors: string[] = [];
  if (!isRecord(value)) return { ok: false, errors: ['task run must be an object'] };
  if (value.schema_version !== GOVERNED_TASK_SCHEMA_VERSION) {
    errors.push(`schema_version must be ${GOVERNED_TASK_SCHEMA_VERSION}`);
  }
  if (typeof value.run_id !== 'string' || !value.run_id.trim()) {
    errors.push('run_id must be a non-empty string');
  }
  if (typeof value.interaction_id !== 'string' || !value.interaction_id.trim()) {
    errors.push('interaction_id must be a non-empty string');
  }

  const status = String(value.status || '') as GovernedTaskStatus;
  if (!(GOVERNED_TASK_STATUSES as readonly string[]).includes(status)) {
    errors.push('status is not a governed task state');
  }
  if (!HASH_RE.test(String(value.input_sha256 || ''))) {
    errors.push('input_sha256 must be a lowercase SHA-256 digest');
  }
  if (value.output_sha256 !== undefined && !HASH_RE.test(String(value.output_sha256))) {
    errors.push('output_sha256 must be a lowercase SHA-256 digest');
  }

  const disposition = value.disposition;
  if (!isRecord(disposition)) {
    errors.push('disposition must be an object');
  } else {
    const dispositionStatus = String(disposition.status || '');
    if (!(GOVERNED_TASK_DISPOSITIONS as readonly string[]).includes(dispositionStatus)) {
      errors.push('disposition.status is not recognized');
    }
    if (typeof disposition.negative_example !== 'boolean') {
      errors.push('disposition.negative_example must be boolean');
    }
    if (disposition.do_not_promote_to_fact !== true) {
      errors.push('disposition.do_not_promote_to_fact must remain true');
    }
    if (typeof disposition.reason !== 'string' || !disposition.reason.trim()) {
      errors.push('disposition.reason must be a non-empty string');
    }
  }

  const basis = normalizeBasis(value.basis);
  if (!Array.isArray(value.basis)) errors.push('basis must be an array');
  for (const [index, field] of basis.entries()) {
    if (!field.field) errors.push(`basis[${index}].field must be non-empty`);
    if (!Number.isFinite(field.confidence) || field.confidence < 0 || field.confidence > 1) {
      errors.push(`basis[${index}].confidence must be between 0 and 1`);
    }
    if (!field.reasoning) errors.push(`basis[${index}].reasoning must be non-empty`);
    for (const [citationIndex, citation] of field.citations.entries()) {
      if (!citation.title || !citation.url || !citation.quote) {
        errors.push(`basis[${index}].citations[${citationIndex}] is incomplete`);
      }
      if (!HASH_RE.test(citation.content_sha256)) {
        errors.push(`basis[${index}].citations[${citationIndex}].content_sha256 must be SHA-256`);
      }
    }
  }

  const citationCount = basis.reduce((count, field) => count + field.citations.length, 0);
  if (isRecord(disposition)) {
    if (status === 'completed') {
      if (!HASH_RE.test(String(value.output_sha256 || ''))) {
        errors.push('completed runs require output_sha256');
      }
      if (citationCount > 0) {
        if (disposition.status !== 'review_required' || disposition.negative_example !== false) {
          errors.push('evidence-backed completion must remain review_required');
        }
      } else if (
        disposition.status !== 'failed_evidence_check' ||
        disposition.negative_example !== true
      ) {
        errors.push('completion without evidence must be a failed_evidence_check negative');
      }
    }
    if (
      status === 'failed' &&
      (disposition.status !== 'failed_execution' || disposition.negative_example !== true)
    ) {
      errors.push('failed runs must use failed_execution and remain negative examples');
    }
    if (
      status === 'cancelled' &&
      (disposition.status !== 'cancelled' || disposition.negative_example !== true)
    ) {
      errors.push('cancelled runs must remain negative and non-promotable');
    }
  }

  validateSeal(value.seal, 'seal', errors);
  validateSeal(value.completion_seal, 'completion_seal', errors);
  return errors.length
    ? { ok: false, errors }
    : { ok: true, errors: [], run: value as unknown as GovernedTaskRun };
}

export function sealGovernedTaskRun(run: GovernedTaskRun): GovernedTaskRun {
  const validation = validateGovernedTaskRun(run);
  if (!validation.ok) {
    throw new TypeError(`cannot seal invalid governed task run: ${validation.errors.join('; ')}`);
  }
  const material = { ...run };
  delete material.contract_sha256;
  return { ...material, contract_sha256: sha256TaskValue(material) };
}

export function verifyGovernedTaskRunSeal(run: GovernedTaskRun): boolean {
  if (!HASH_RE.test(String(run.contract_sha256 || ''))) return false;
  const material = { ...run };
  delete material.contract_sha256;
  return crypto.timingSafeEqual(
    Buffer.from(run.contract_sha256 || '', 'hex'),
    Buffer.from(sha256TaskValue(material), 'hex')
  );
}
