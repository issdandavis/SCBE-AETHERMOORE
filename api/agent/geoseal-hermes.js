'use strict';

const crypto = require('node:crypto');

function setCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST,OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
}

function readBody(req, maxBytes = 8000) {
  if (req.body && typeof req.body === 'object') return Promise.resolve(req.body);
  return new Promise((resolve, reject) => {
    let raw = '';
    req.on('data', (chunk) => {
      raw += chunk;
      if (raw.length > maxBytes) {
        reject(new Error('request body too large'));
        req.destroy();
      }
    });
    req.on('end', () => {
      if (!raw.trim()) return resolve({});
      try {
        resolve(JSON.parse(raw));
      } catch (error) {
        reject(error);
      }
    });
    req.on('error', reject);
  });
}

function sha(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function shellQuote(value) {
  return `"${String(value).replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`;
}

function classify(task) {
  const text = String(task || '').toLowerCase();
  if (/\b(code|repo|test|patch|build|api|frontend|backend|deploy)\b/.test(text)) return 'do';
  if (/\b(explain|summarize|what|why|analyze|inspect)\b/.test(text)) return 'ask';
  if (/\b(receipt|route|seal|packet|command)\b/.test(text)) return 'run-command';
  return 'ask';
}

function commandFor(task, routeType, outputMode) {
  const jsonFlag = outputMode === 'json' ? ' --json' : '';
  if (routeType === 'api') {
    return `geoseal ${classify(task)} ${shellQuote(task)} --api-base http://127.0.0.1:8002${jsonFlag}`;
  }
  if (routeType === 'hosted') {
    return `geoseal do ${shellQuote(task)}${jsonFlag} # hosted intake: https://aethermoore.com/hosted-run`;
  }
  return `geoseal ${classify(task)} ${shellQuote(task)}${jsonFlag}`;
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'POST') return res.status(405).json({ ok: false, error: 'POST required' });

  try {
    const body = await readBody(req);
    const task = String(body.task || '').trim();
    const routeType = String(body.route_type || 'local').trim().toLowerCase();
    const outputMode = String(body.output_mode || 'json').trim().toLowerCase();
    if (!task) return res.status(400).json({ ok: false, error: 'task is required' });
    if (task.length > 2000) return res.status(400).json({ ok: false, error: 'task is too long' });

    const backend =
      routeType === 'api' ? 'local GeoSeal API' : routeType === 'hosted' ? 'AetherMoore hosted run' : 'local CLI';
    const policy =
      routeType === 'hosted'
        ? 'paid dispatch with receipt'
        : routeType === 'api'
          ? 'service route with API receipt'
          : 'free local first';

    const payload = {
      ok: true,
      schema_version: 'aethermoore-geoseal-hermes-v1',
      receipt_id: `hermes_${sha(`${routeType}|${outputMode}|${task}`).slice(0, 16)}`,
      route_type: routeType,
      backend,
      policy,
      command: commandFor(task, routeType, outputMode),
      summary: `Prepared a ${routeType} GeoSeal route for a ${classify(task)} task.`,
      next_steps: [
        'Run the command locally or attach it to the hosted intake.',
        'Keep the JSON receipt with the customer delivery.',
        'Turn repeat routes into one-click product actions.',
      ],
    };

    return res.status(200).json(payload);
  } catch (error) {
    return res.status(500).json({ ok: false, error: error && error.message ? error.message : String(error) });
  }
};
