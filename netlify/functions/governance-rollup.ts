import type { Config, Context } from '@netlify/functions';
import { buildDailyGovernanceRollup } from './_shared/receipt-store';

export default async (_req: Request, context: Context) => {
  const rollup = await buildDailyGovernanceRollup();
  console.log('governance_rollup_written', {
    requestId: context.requestId,
    day: rollup.day,
    receiptCount: rollup.receiptCount,
    storageKey: rollup.storageKey,
  });
};

export const config: Config = {
  schedule: '@daily',
};
