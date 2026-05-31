'use strict';

const fs = require('node:fs');
const path = require('node:path');
const { sendJson, setCors } = require('../_agent_common');

function readPublicJson(name) {
  const target = path.join(process.cwd(), 'docs', name);
  return JSON.parse(fs.readFileSync(target, 'utf8'));
}

module.exports = async function handler(req, res) {
  setCors(res);
  if (req.method === 'OPTIONS') return res.status(204).end();
  if (req.method !== 'GET') return sendJson(res, 405, { ok: false, error: 'GET required' });

  res.setHeader('Cache-Control', 's-maxage=300, stale-while-revalidate=86400');
  return sendJson(res, 200, {
    ok: true,
    source: 'docs/offers.json',
    ...readPublicJson('offers.json'),
  });
};
