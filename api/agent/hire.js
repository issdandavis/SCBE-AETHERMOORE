'use strict';

const fs = require('node:fs');
const path = require('node:path');

const HIRE_PAGE = path.join(process.cwd(), 'docs', 'hire.html');
const FALLBACK_HIRE_PAGE = path.join(process.cwd(), 'public', 'hire.html');

module.exports = async function handler(req, res) {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.setHeader('Allow', 'GET, HEAD');
    return res.status(405).json({ ok: false, error: 'method_not_allowed' });
  }

  try {
    const pagePath = fs.existsSync(HIRE_PAGE) ? HIRE_PAGE : FALLBACK_HIRE_PAGE;
    const html = fs.readFileSync(pagePath, 'utf8');
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 'public, max-age=300, s-maxage=300');
    return res.status(200).send(req.method === 'HEAD' ? '' : html);
  } catch (err) {
    return res.status(500).json({
      ok: false,
      error: 'hire_page_unavailable',
      detail: err && err.message ? err.message : String(err),
    });
  }
};
