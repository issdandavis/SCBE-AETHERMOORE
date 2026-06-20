'use strict';

// /hire-b — A/B variant of /hire with a Snapshot-led hero. Funnel
// beacons fire with page='hire-b' so the operator dashboard can
// compare conversion against the consulting-services-led /hire page.
// Below-the-fold content matches /hire so the test isolates hero impact.

const fs = require('node:fs');
const path = require('node:path');

const HIRE_B_PAGE = path.join(process.cwd(), 'docs', 'hire-b.html');
const FALLBACK_HIRE_B_PAGE = path.join(process.cwd(), 'public', 'hire-b.html');

module.exports = async function handler(req, res) {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.setHeader('Allow', 'GET, HEAD');
    return res.status(405).json({ ok: false, error: 'method_not_allowed' });
  }

  try {
    const pagePath = fs.existsSync(HIRE_B_PAGE) ? HIRE_B_PAGE : FALLBACK_HIRE_B_PAGE;
    const html = fs.readFileSync(pagePath, 'utf8');
    res.setHeader('Content-Type', 'text/html; charset=utf-8');
    res.setHeader('Cache-Control', 'public, max-age=300, s-maxage=300');
    return res.status(200).send(req.method === 'HEAD' ? '' : html);
  } catch (err) {
    return res.status(500).json({
      ok: false,
      error: 'hire_b_page_unavailable',
      detail: err && err.message ? err.message : String(err),
    });
  }
};
