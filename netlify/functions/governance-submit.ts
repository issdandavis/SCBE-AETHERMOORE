import type { Config, Context } from '@netlify/functions';
import { corsPreflight, json, methodNotAllowed, withCors } from './_shared/response';

type GovernancePayload = {
  intent?: unknown;
  source?: unknown;
  metadata?: unknown;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(',')}]`;
  }

  if (isRecord(value)) {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`)
      .join(',')}}`;
  }

  return JSON.stringify(value);
}

async function sha256Hex(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

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

  if (
    !isRecord(payload) ||
    typeof payload.intent !== 'string' ||
    payload.intent.trim().length === 0
  ) {
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

  const normalized = {
    intent: payload.intent.trim(),
    source: typeof payload.source === 'string' ? payload.source : 'netlify',
    metadata: isRecord(payload.metadata) ? payload.metadata : {},
  };
  const receipt = await sha256Hex(stableStringify(normalized));

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
