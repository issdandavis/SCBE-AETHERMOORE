'use strict';

const fs = require('node:fs');
const path = require('node:path');

const FAST_START_PAGE = path.join(process.cwd(), 'public', 'service-fast-start.html');

module.exports = async function handler(req, res) {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.setHeader('Allow', 'GET, HEAD');
    return res.status(405).json({ ok: false, error: 'method_not_allowed' });
  }

  try {
    const html = fs.readFileSync(FAST_START_PAGE, 'utf8');
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 'public, max-age=300, s-maxage=300');
    return res.status(200).send(req.method === 'HEAD' ? '' : html);
  } catch (err) {
    return res.status(500).json({
      ok: false,
      error: 'service_fast_start_unavailable',
      detail: err && err.message ? err.message : String(err),
    });
  }
};
