import type { Config, Context } from '@netlify/functions';
import { json, methodNotAllowed } from './_shared/response';

const capabilities = [
  'geoseal-pqc',
  'scbe-cli',
  'chemistry-tokenizer',
  'agentic-memory-health',
  'skill-recovery',
  'governance-submit',
];

export default async (req: Request, context: Context) => {
  if (req.method !== 'GET') {
    return methodNotAllowed(req.method, ['GET']);
  }

  return json({
    ok: true,
    name: 'SCBE-AETHERMOORE Netlify API',
    requestId: context.requestId,
    capabilities,
    endpoints: {
      health: '/api/health',
      manifest: '/api/system/manifest',
      governanceSubmit: '/api/governance/submit',
    },
  });
};

export const config: Config = {
  path: '/api/system/manifest',
  method: ['GET'],
};
