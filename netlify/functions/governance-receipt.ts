import type { Config } from '@netlify/functions';
import { findGovernanceReceipt } from './_shared/receipt-store';
import { corsPreflight, json, methodNotAllowed, withCors } from './_shared/response';

export default async (req: Request) => {
  if (req.method === 'OPTIONS') {
    return corsPreflight(['GET']);
  }

  if (req.method !== 'GET') {
    return withCors(methodNotAllowed(req.method, ['GET']));
  }

  const receipt = new URL(req.url).pathname.split('/').pop() ?? '';
  if (!/^[a-f0-9]{64}$/.test(receipt)) {
    return withCors(json({ ok: false, error: 'invalid_receipt' }, { status: 400 }));
  }

  const record = await findGovernanceReceipt(receipt);
  if (!record) {
    return withCors(json({ ok: false, error: 'receipt_not_found' }, { status: 404 }));
  }

  return withCors(json({ ok: true, record }));
};

export const config: Config = {
  path: '/api/governance/receipts/:receipt',
  method: ['OPTIONS', 'GET'],
};
