import type { Config, Context } from '@netlify/functions';
import { json, methodNotAllowed } from './_shared/response';

export default async (req: Request, context: Context) => {
  if (req.method !== 'GET') {
    return methodNotAllowed(req.method, ['GET']);
  }

  return json({
    ok: true,
    service: 'scbe-aethermoore',
    status: 'ready',
    requestId: context.requestId,
    deploy: {
      context: context.deploy.context ?? null,
      id: context.deploy.id ?? null,
      published: context.deploy.published ?? false,
    },
    site: {
      id: context.site.id ?? null,
      name: context.site.name ?? null,
      url: context.site.url ?? null,
    },
    geo: {
      city: context.geo.city ?? null,
      country: context.geo.country?.code ?? null,
      timezone: context.geo.timezone ?? null,
    },
  });
};

export const config: Config = {
  path: '/api/health',
  method: ['GET'],
};
