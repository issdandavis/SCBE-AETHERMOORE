'use strict';

const crypto = require('node:crypto');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const { URL } = require('node:url');
const { AgentRuntime } = require('./agent-runtime');
const { executeSlash } = require('./agent-shell');
const { listProviders } = require('./provider-registry');
const { mechanicalModel } = require('./mechanical-primitives');
const {
  deleteCommand,
  expandCommand,
  getCommand,
  listCommands,
  saveCommand,
} = require('./custom-commands');

const WEB_ROOT = path.resolve(__dirname, '..', 'web');
const MAX_BODY_BYTES = 1024 * 1024;
const LOOPBACK_HOSTS = new Set(['127.0.0.1', '::1', 'localhost']);
const CONTENT_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.json': 'application/json; charset=utf-8',
};

function sendJson(response, status, payload) {
  const body = `${JSON.stringify(payload)}\n`;
  response.writeHead(status, {
    'content-type': 'application/json; charset=utf-8',
    'content-length': Buffer.byteLength(body),
    'cache-control': 'no-store',
    'x-content-type-options': 'nosniff',
  });
  response.end(body);
}

function readJsonBody(request) {
  return new Promise((resolve, reject) => {
    const contentType = String(request.headers['content-type'] || '')
      .split(';', 1)[0]
      .trim()
      .toLowerCase();
    if (contentType !== 'application/json') {
      reject(new Error('content-type must be application/json'));
      return;
    }
    let bytes = 0;
    let body = '';
    request.setEncoding('utf8');
    request.on('data', (chunk) => {
      bytes += Buffer.byteLength(chunk);
      if (bytes > MAX_BODY_BYTES) {
        reject(new Error('request body is too large'));
        request.destroy();
        return;
      }
      body += chunk;
    });
    request.on('end', () => {
      try {
        const value = JSON.parse(body || '{}');
        if (!value || typeof value !== 'object' || Array.isArray(value)) {
          reject(new Error('JSON body must be an object'));
          return;
        }
        resolve(value);
      } catch (error) {
        reject(new Error(`invalid JSON body: ${error.message}`));
      }
    });
    request.on('error', reject);
  });
}

function serveStatic(response, pathname, options = {}) {
  const relative = pathname === '/' ? 'index.html' : pathname.replace(/^\/+/, '');
  const target = path.resolve(WEB_ROOT, relative);
  if (!target.startsWith(`${WEB_ROOT}${path.sep}`) && target !== WEB_ROOT) {
    sendJson(response, 404, { ok: false, error: 'not found' });
    return;
  }
  if (!fs.existsSync(target) || !fs.statSync(target).isFile()) {
    sendJson(response, 404, { ok: false, error: 'not found' });
    return;
  }
  let content = fs.readFileSync(target);
  if (path.basename(target) === 'index.html' && options.apiToken) {
    let html = content.toString('utf8');
    const escapedToken = String(options.apiToken).replace(/[&<>"']/g, (character) => {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character];
    });
    const meta = `<meta name="scbe-api-token" content="${escapedToken}" />`;
    html = html.includes('__SCBE_API_TOKEN__')
      ? html.replace('__SCBE_API_TOKEN__', escapedToken)
      : html.replace('</head>', `    ${meta}\n  </head>`);
    content = Buffer.from(html, 'utf8');
  }
  response.writeHead(200, {
    'content-type': CONTENT_TYPES[path.extname(target)] || 'application/octet-stream',
    'content-length': content.length,
    'cache-control': 'no-cache',
    'content-security-policy':
      "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
    'x-content-type-options': 'nosniff',
    'x-frame-options': 'DENY',
    'referrer-policy': 'no-referrer',
  });
  response.end(content);
}

function trustedHost(request, port) {
  const value = String(request.headers.host || '').toLowerCase();
  return new Set([`127.0.0.1:${port}`, `localhost:${port}`, `[::1]:${port}`]).has(value);
}

function trustedOrigin(request) {
  const origin = String(request.headers.origin || '').trim().toLowerCase();
  if (!origin) return true;
  return origin === `http://${String(request.headers.host || '').toLowerCase()}`;
}

function equalToken(expected, actual) {
  const left = Buffer.from(String(expected || ''), 'utf8');
  const right = Buffer.from(String(actual || ''), 'utf8');
  return left.length === right.length && left.length > 0 && crypto.timingSafeEqual(left, right);
}

function consumeApproval(approvals, tool) {
  const remaining = Number(approvals.get(tool) || 0);
  if (remaining < 1) return false;
  if (remaining === 1) approvals.delete(tool);
  else approvals.set(tool, remaining - 1);
  return true;
}

function approvalCounts(values) {
  const counts = new Map();
  for (const value of Array.isArray(values) ? values : []) {
    const name = String(value || '');
    counts.set(name, Number(counts.get(name) || 0) + 1);
  }
  return counts;
}

function commandPayload(workspaceRoot, options) {
  return listCommands(workspaceRoot, options).map((command) => ({
    name: command.name,
    scope: command.scope,
    description: command.description,
    template: command.template,
  }));
}

function createSessionLock() {
  const locks = new Map();
  return async (key, work) => {
    const previous = locks.get(key) || Promise.resolve();
    const current = previous.catch(() => {}).then(work);
    locks.set(key, current);
    try {
      return await current;
    } finally {
      if (locks.get(key) === current) locks.delete(key);
    }
  };
}

async function startAgentWebServer(options = {}) {
  const host = String(options.host || '127.0.0.1');
  if (!LOOPBACK_HOSTS.has(host)) {
    throw new Error(
      'SCBE web is loopback-only; use an authenticated tunnel or reverse proxy instead of a public bind'
    );
  }
  const apiToken = String(options.apiToken || crypto.randomBytes(32).toString('hex'));
  const workspaceRoot = path.resolve(options.workspaceRoot || process.cwd());
  const storageOptions = { env: options.env, home: options.home };
  const runtimes = new Map();
  const withLock = createSessionLock();

  const createRuntime = (sessionId) => {
    const runtime = new AgentRuntime({
      workspaceRoot,
      env: options.env,
      home: options.home,
      transport: options.transport,
      permissionResolver: null,
      onEvent: null,
    });
    if (sessionId) runtime.resume(sessionId);
    runtimes.set(runtime.session.id, runtime);
    return runtime;
  };

  const getRuntime = (sessionId) => {
    let runtime = sessionId ? runtimes.get(sessionId) : null;
    if (!runtime) runtime = createRuntime(sessionId);
    return runtime;
  };

  const server = http.createServer(async (request, response) => {
    try {
      const address = server.address();
      const port = typeof address === 'object' && address ? address.port : options.port || 0;
      const baseHost = host === '::1' ? '[::1]' : host;
      const url = new URL(request.url || '/', `http://${baseHost}:${port}`);

      if (!trustedHost(request, port)) {
        sendJson(response, 421, { ok: false, error: 'untrusted Host header' });
        return;
      }
      if (!trustedOrigin(request)) {
        sendJson(response, 403, { ok: false, error: 'cross-origin API access is not allowed' });
        return;
      }

      const publicApi =
        request.method === 'GET' && ['/api/health', '/api/mechanics'].includes(url.pathname);
      if (
        url.pathname.startsWith('/api/') &&
        !publicApi &&
        !equalToken(apiToken, request.headers['x-scbe-web-token'])
      ) {
        sendJson(response, 401, { ok: false, error: 'invalid SCBE web token' });
        return;
      }

      if (request.method === 'GET' && url.pathname === '/api/health') {
        sendJson(response, 200, { ok: true, service: 'scbe-agent-web', loopback: LOOPBACK_HOSTS.has(host) });
        return;
      }

      if (request.method === 'GET' && url.pathname === '/api/mechanics') {
        sendJson(response, 200, { ok: true, mechanics: mechanicalModel() });
        return;
      }

      if (request.method === 'GET' && url.pathname === '/api/status') {
        const requested = url.searchParams.get('session_id') || '';
        const runtime = getRuntime(requested);
        sendJson(response, 200, {
          ok: true,
          status: runtime.status(),
          providers: listProviders(storageOptions),
          sessions: runtime.sessions().slice(0, 30),
          tools: runtime.registry.list().map(({ name, description, kind }) => ({ name, description, kind })),
          commands: commandPayload(workspaceRoot, storageOptions),
        });
        return;
      }

      if (request.method === 'POST' && url.pathname === '/api/chat') {
        const body = await readJsonBody(request);
        const message = String(body.message || '').trim();
        if (!message) {
          sendJson(response, 400, { ok: false, error: 'message is required' });
          return;
        }
        const events = [];
        const runtime = getRuntime(String(body.session_id || ''));
        const key = runtime.session.id;
        const result = await withLock(key, async () => {
          const approved = approvalCounts(
            Array.isArray(body.approved_tools) ? body.approved_tools.map(String) : []
          );
          const previousPermissionResolver = runtime.permissionResolver;
          const previousOnEvent = runtime.onEvent;
          runtime.permissionResolver = async ({ tool }) => consumeApproval(approved, tool);
          runtime.onEvent = async (event) => events.push(event);
          try {
            if (body.model) runtime.setModel(String(body.model));
            if (body.permission_mode) runtime.setPermissionMode(String(body.permission_mode));
            const slash = await executeSlash(runtime, message, storageOptions);
            if (slash.handled && !slash.prompt) {
              return { content: slash.output || '', control: true, exit: slash.exit === true };
            }
            return await runtime.runTurn(slash.prompt || message);
          } finally {
            runtime.permissionResolver = previousPermissionResolver;
            runtime.onEvent = previousOnEvent;
          }
        });
        sendJson(response, 200, {
          ok: true,
          session_id: runtime.session.id,
          message: result.content,
          control: result.control === true,
          events,
          status: runtime.status(),
        });
        return;
      }

      if (request.method === 'POST' && url.pathname === '/api/session/new') {
        const body = await readJsonBody(request);
        const runtime = getRuntime(String(body.session_id || ''));
        const previousId = runtime.session.id;
        const session = await withLock(previousId, async () => {
          const created = runtime.newSession();
          runtimes.delete(previousId);
          runtimes.set(created.id, runtime);
          return created;
        });
        sendJson(response, 200, { ok: true, session_id: session.id, status: runtime.status() });
        return;
      }

      if (request.method === 'POST' && url.pathname === '/api/session/resume') {
        const body = await readJsonBody(request);
        const requested = String(body.session_id || 'latest');
        const runtime = await withLock(requested, async () => getRuntime(requested));
        sendJson(response, 200, {
          ok: true,
          session_id: runtime.session.id,
          status: runtime.status(),
          messages: runtime.session.messages
            .filter((message) => message.role === 'user' || message.role === 'assistant')
            .map((message) => ({ role: message.role, content: String(message.content || '') })),
        });
        return;
      }

      if (request.method === 'POST' && url.pathname === '/api/commands') {
        const body = await readJsonBody(request);
        const action = String(body.action || 'list').toLowerCase();
        let result = null;
        if (action === 'list') {
          result = commandPayload(workspaceRoot, storageOptions);
        } else if (action === 'new' || action === 'edit') {
          result = saveCommand(
            workspaceRoot,
            {
              name: body.name,
              template: body.template,
              description: body.description,
              scope: body.scope === 'project' ? 'project' : 'user',
              createOnly: action === 'new',
            },
            storageOptions
          );
        } else if (action === 'delete') {
          result = deleteCommand(workspaceRoot, body.name, {
            ...storageOptions,
            ...(body.scope ? { scope: body.scope } : {}),
          });
        } else if (action === 'run') {
          const command = getCommand(workspaceRoot, body.name, storageOptions);
          if (!command) throw new Error(`no command named /${body.name}`);
          result = { prompt: expandCommand(command, body.args || ''), command: command.name };
        } else {
          throw new Error('action must be list, new, edit, delete, or run');
        }
        sendJson(response, 200, {
          ok: true,
          result,
          commands: commandPayload(workspaceRoot, storageOptions),
        });
        return;
      }

      if (request.method === 'GET') {
        serveStatic(response, url.pathname, { apiToken });
        return;
      }
      sendJson(response, 404, { ok: false, error: 'not found' });
    } catch (error) {
      sendJson(
        response,
        /invalid|must|required|no command|outside|content-type/i.test(error.message) ? 400 : 500,
        {
        ok: false,
        error: error.message || String(error),
        }
      );
    }
  });

  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(Number(options.port || 0), host, resolve);
  });
  const address = server.address();
  const port = typeof address === 'object' && address ? address.port : Number(options.port || 0);
  return {
    host,
    port,
    url: `http://${host === '::1' ? '[::1]' : host}:${port}`,
    apiToken,
    server,
    close: () => new Promise((resolve, reject) => server.close((error) => (error ? reject(error) : resolve()))),
  };
}

function parseWebArgs(args) {
  const options = { host: '127.0.0.1', port: 4179, allowRemote: false, json: false };
  for (let index = 0; index < args.length; index += 1) {
    const token = args[index];
    if (token === '--host') options.host = args[++index] || options.host;
    else if (token === '--port') options.port = Number(args[++index] || options.port);
    else if (token === '--allow-remote') options.allowRemote = true;
    else if (token === '--json') options.json = true;
    else if (token === '--help' || token === '-h') options.help = true;
  }
  return options;
}

async function runWebCommand(args = [], options = {}) {
  const parsed = parseWebArgs(args);
  if (parsed.help) {
    process.stdout.write(
      'Usage: scbe web [--port 4179] [--host 127.0.0.1] [--json]\n' +
        'Starts the first-party SCBE chat interface on loopback.\n'
    );
    return null;
  }
  if (parsed.allowRemote) {
    throw new Error(
      '--allow-remote is disabled; use an authenticated tunnel or reverse proxy to the loopback server'
    );
  }
  const handle = await startAgentWebServer({ ...options, ...parsed });
  if (parsed.json) {
    process.stdout.write(`${JSON.stringify({ ok: true, url: handle.url, host: handle.host, port: handle.port })}\n`);
  } else {
    process.stdout.write(`SCBE web is ready at ${handle.url}\nPress Ctrl+C to stop.\n`);
  }
  return handle;
}

module.exports = {
  WEB_ROOT,
  startAgentWebServer,
  parseWebArgs,
  runWebCommand,
};
