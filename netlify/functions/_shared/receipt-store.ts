import type { Context } from '@netlify/functions';
import { getStore } from '@netlify/blobs';
import type { NormalizedGovernancePayload } from './governance';

const RECEIPT_STORE = 'scbe-governance-receipts';

export type GovernanceReceiptRecord = {
  receipt: string;
  status: 'queued' | 'processed';
  payload: NormalizedGovernancePayload;
  requestId: string;
  createdAt: string;
  storageKey: string;
  netlify: {
    deployContext?: string;
    deployId?: string;
    siteId?: string;
    siteName?: string;
  };
};

export type GovernanceRollupRecord = {
  ok: true;
  day: string;
  receiptCount: number;
  receipts: string[];
  generatedAt: string;
  storageKey: string;
};

function receiptDay(createdAt: string): string {
  return createdAt.slice(0, 10);
}

export function governanceReceiptKey(receipt: string, createdAt: string): string {
  return `receipts/${receiptDay(createdAt)}/${receipt}.json`;
}

export function governanceRollupKey(day: string): string {
  return `rollups/${day}.json`;
}

function governanceReceiptIndexKey(receipt: string): string {
  return `indexes/receipts/${receipt}.json`;
}

function receiptStore() {
  return getStore({ name: RECEIPT_STORE, consistency: 'strong' });
}

export async function saveGovernanceReceipt(input: {
  receipt: string;
  payload: NormalizedGovernancePayload;
  context: Context;
  createdAt?: string;
}): Promise<GovernanceReceiptRecord> {
  const createdAt = input.createdAt ?? new Date().toISOString();
  const storageKey = governanceReceiptKey(input.receipt, createdAt);
  const record: GovernanceReceiptRecord = {
    receipt: input.receipt,
    status: 'queued',
    payload: input.payload,
    requestId: input.context.requestId,
    createdAt,
    storageKey,
    netlify: {
      deployContext: input.context.deploy?.context,
      deployId: input.context.deploy?.id,
      siteId: input.context.site?.id,
      siteName: input.context.site?.name,
    },
  };

  await receiptStore().setJSON(storageKey, record, {
    metadata: {
      receipt: input.receipt,
      status: record.status,
      day: receiptDay(createdAt),
      source: input.payload.source,
    },
  });
  await receiptStore().setJSON(governanceReceiptIndexKey(input.receipt), {
    receipt: input.receipt,
    storageKey,
    createdAt,
  });

  return record;
}

export async function findGovernanceReceipt(
  receipt: string
): Promise<GovernanceReceiptRecord | null> {
  const store = receiptStore();
  const index = (await store.get(governanceReceiptIndexKey(receipt), { type: 'json' })) as {
    storageKey?: unknown;
  } | null;
  if (typeof index?.storageKey !== 'string') {
    return null;
  }

  return (await store.get(index.storageKey, { type: 'json' })) as GovernanceReceiptRecord | null;
}

export async function buildDailyGovernanceRollup(
  day = new Date().toISOString().slice(0, 10)
): Promise<GovernanceRollupRecord> {
  const store = receiptStore();
  const listing = await store.list({ prefix: `receipts/${day}/` });
  const receipts = listing.blobs
    .map((blob) =>
      blob.key
        .split('/')
        .pop()
        ?.replace(/\.json$/, '')
    )
    .filter((receipt): receipt is string => Boolean(receipt))
    .sort();
  const storageKey = governanceRollupKey(day);
  const rollup: GovernanceRollupRecord = {
    ok: true,
    day,
    receiptCount: receipts.length,
    receipts,
    generatedAt: new Date().toISOString(),
    storageKey,
  };

  await store.setJSON(storageKey, rollup, {
    metadata: {
      day,
      receiptCount: String(receipts.length),
      generatedAt: rollup.generatedAt,
    },
  });

  return rollup;
}
