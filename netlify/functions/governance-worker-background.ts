import type { Config, Context } from '@netlify/functions';
import {
  GovernancePayload,
  governanceReceipt,
  normalizeGovernancePayload,
} from './_shared/governance';

export default async (req: Request, context: Context) => {
  let payload: GovernancePayload = {};
  try {
    payload = (await req.json()) as GovernancePayload;
  } catch {
    console.warn('governance_worker_invalid_json', { requestId: context.requestId });
    return;
  }

  const normalized = normalizeGovernancePayload(payload);
  if (!normalized) {
    console.warn('governance_worker_invalid_payload', { requestId: context.requestId });
    return;
  }

  const receipt = await governanceReceipt(normalized);
  console.log('governance_worker_processed', {
    receipt,
    requestId: context.requestId,
    source: normalized.source,
    intentLength: normalized.intent.length,
  });
};

export const config: Config = {
  path: '/api/governance/process',
  method: ['POST'],
};
