export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export function json(data: JsonValue, init: ResponseInit = {}): Response {
  const headers = new Headers(init.headers);
  headers.set('Content-Type', 'application/json; charset=utf-8');
  headers.set('Cache-Control', 'no-store');

  return new Response(JSON.stringify(data, null, 2), {
    ...init,
    headers,
  });
}

export function methodNotAllowed(method: string, allowed: string[]): Response {
  return json(
    {
      ok: false,
      error: 'method_not_allowed',
      method,
      allowed,
    },
    {
      status: 405,
      headers: { Allow: allowed.join(', ') },
    }
  );
}

export function corsPreflight(methods: string[]): Response {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-API-Key',
      'Access-Control-Allow-Methods': ['OPTIONS', ...methods].join(', '),
      'Access-Control-Max-Age': '86400',
    },
  });
}

export function withCors(response: Response): Response {
  const headers = new Headers(response.headers);
  headers.set('Access-Control-Allow-Origin', '*');
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}
