export type GovernancePayload = {
  intent?: unknown;
  source?: unknown;
  metadata?: unknown;
};

export type NormalizedGovernancePayload = {
  intent: string;
  source: string;
  metadata: Record<string, unknown>;
};

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function normalizeGovernancePayload(
  payload: GovernancePayload
): NormalizedGovernancePayload | null {
  if (
    !isRecord(payload) ||
    typeof payload.intent !== 'string' ||
    payload.intent.trim().length === 0
  ) {
    return null;
  }

  return {
    intent: payload.intent.trim(),
    source: typeof payload.source === 'string' ? payload.source : 'netlify',
    metadata: isRecord(payload.metadata) ? payload.metadata : {},
  };
}

export function stableStringify(value: unknown): string {
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

export async function sha256Hex(input: string): Promise<string> {
  const data = new TextEncoder().encode(input);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash))
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

export async function governanceReceipt(payload: NormalizedGovernancePayload): Promise<string> {
  return sha256Hex(stableStringify(payload));
}
