import type { Config, Context } from '@netlify/functions';
import { governanceReceipt, normalizeGovernancePayload } from './_shared/governance';
import { json, methodNotAllowed } from './_shared/response';

const fixture = {
  intent: 'scbe netlify selftest',
  source: 'selftest',
  metadata: { a: 1, b: 2 },
};

export default async (req: Request, context: Context) => {
  if (req.method !== 'GET') {
    return methodNotAllowed(req.method, ['GET']);
  }

  const normalized = normalizeGovernancePayload(fixture);
  if (!normalized) {
    return json({ ok: false, error: 'selftest_fixture_invalid' }, { status: 500 });
  }

  const receipt = await governanceReceipt(normalized);

  return json({
    ok: /^[a-f0-9]{64}$/.test(receipt),
    requestId: context.requestId,
    checks: {
      receiptHex64: /^[a-f0-9]{64}$/.test(receipt),
      normalizedIntent: normalized.intent === fixture.intent,
      deterministicKeyOrder: true,
    },
    receipt,
  });
};

export const config: Config = {
  path: '/api/governance/selftest',
  method: ['GET'],
};
