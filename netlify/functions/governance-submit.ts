import type { Config, Context } from '@netlify/functions';
import {
  GovernancePayload,
  governanceReceipt,
  normalizeGovernancePayload,
} from './_shared/governance';
import { corsPreflight, json, methodNotAllowed, withCors } from './_shared/response';

export default async (req: Request, context: Context) => {
  if (req.method === 'OPTIONS') {
    return corsPreflight(['POST']);
  }

  if (req.method !== 'POST') {
    return withCors(methodNotAllowed(req.method, ['POST']));
  }

  let payload: GovernancePayload;
  try {
    payload = (await req.json()) as GovernancePayload;
  } catch {
    return withCors(json({ ok: false, error: 'invalid_json' }, { status: 400 }));
  }

  const normalized = normalizeGovernancePayload(payload);
  if (!normalized) {
    return withCors(
      json(
        {
          ok: false,
          error: 'invalid_payload',
          required: ['intent:string'],
        },
        { status: 422 }
      )
    );
  }

  const receipt = await governanceReceipt(normalized);

  context.waitUntil(
    Promise.resolve().then(() => {
      console.log('governance_submit', {
        receipt,
        requestId: context.requestId,
        source: normalized.source,
      });
    })
  );

  return withCors(
    json(
      {
        ok: true,
        decision: 'queued',
        receipt,
        requestId: context.requestId,
      },
      { status: 202 }
    )
  );
};

export const config: Config = {
  path: '/api/governance/submit',
  method: ['OPTIONS', 'POST'],
};
