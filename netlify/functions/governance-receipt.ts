import type { Config } from '@netlify/functions';
import type { GovernanceReceiptRecord } from './_shared/receipt-store';
import { findGovernanceReceipt } from './_shared/receipt-store';
import { corsPreflight, json, methodNotAllowed, withCors } from './_shared/response';

function configuredReceiptApiKey(): string | null {
  return (process.env.GOVERNANCE_RECEIPT_API_KEY || process.env.SCBE_API_KEY || '').trim() || null;
}

function requestCredential(req: Request): string {
  const apiKey = req.headers.get('x-api-key')?.trim();
  if (apiKey) {
    return apiKey;
  }

  const authorization = req.headers.get('authorization')?.trim() ?? '';
  const match = /^Bearer\s+(.+)$/i.exec(authorization);
  return match?.[1]?.trim() ?? '';
}

function isAuthorizedReceiptRequest(req: Request): boolean {
  const expected = configuredReceiptApiKey();
  return Boolean(expected && requestCredential(req) === expected);
}

type PublicGovernanceReceiptRecord = Pick<
  GovernanceReceiptRecord,
  'receipt' | 'status' | 'requestId' | 'createdAt' | 'storageKey'
> & {
  payload: Pick<GovernanceReceiptRecord['payload'], 'intent' | 'source'>;
};

function publicGovernanceReceiptRecord(
  record: GovernanceReceiptRecord
): PublicGovernanceReceiptRecord {
  return {
    receipt: record.receipt,
    status: record.status,
    requestId: record.requestId,
    createdAt: record.createdAt,
    storageKey: record.storageKey,
    payload: {
      intent: record.payload.intent,
      source: record.payload.source,
    },
  };
}

export default async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return corsPreflight(['GET']);
  }

  if (req.method !== 'GET') {
    return withCors(methodNotAllowed(req.method, ['GET']));
  }

  if (!isAuthorizedReceiptRequest(req)) {
    return withCors(json({ ok: false, error: 'unauthorized' }, { status: 401 }));
  }

  const receipt = new URL(req.url).pathname.split('/').pop() ?? '';
  if (!/^[a-f0-9]{64}$/.test(receipt)) {
    return withCors(json({ ok: false, error: 'invalid_receipt' }, { status: 400 }));
  }

  const record = await findGovernanceReceipt(receipt);
  if (!record) {
    return withCors(json({ ok: false, error: 'receipt_not_found' }, { status: 404 }));
  }

  return withCors(json({ ok: true, record: publicGovernanceReceiptRecord(record) }));
};

export const config: Config = {
  path: '/api/governance/receipts/:receipt',
  method: ['OPTIONS', 'GET'],
};
