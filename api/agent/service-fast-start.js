'use strict';

const fs = require('node:fs');
const path = require('node:path');

const FAST_START_PAGE = path.join(process.cwd(), 'public', 'service-fast-start.html');
const INLINE_FAST_START_HTML = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SCBE Service Fast-Start Packet</title>
    <style>
      body { margin: 0; font-family: Inter, system-ui, sans-serif; color: #e8f0fb; background: #08111f; line-height: 1.55; }
      main { max-width: 860px; margin: 0 auto; padding: 48px 22px 80px; }
      h1 { font-size: clamp(30px, 5vw, 52px); line-height: 1.04; margin: 0 0 18px; }
      h2 { margin-top: 34px; color: #17c6cf; }
      a { color: #17c6cf; }
      .panel { border: 1px solid #243352; background: #101a2b; border-radius: 8px; padding: 20px; margin: 16px 0; }
      li { margin: 8px 0; }
    </style>
  </head>
  <body>
    <main>
      <p style="color:#17c6cf;font-weight:700;text-transform:uppercase;letter-spacing:.12em">Immediate service packet</p>
      <h1>SCBE Service Fast-Start</h1>
      <p>This packet gives a buyer immediate value before human review: what to send, what not to send, what the first AI inspection checks, and what happens next.</p>
      <section class="panel">
        <h2>Send First</h2>
        <ul>
          <li>One paragraph describing the AI system, workflow, or governance problem.</li>
          <li>Public documentation, screenshots, architecture notes, or sanitized logs.</li>
          <li>Deadline, buyer type, budget range, and the decision you need help making.</li>
        </ul>
      </section>
      <section class="panel">
        <h2>Do Not Send Yet</h2>
        <ul>
          <li>API keys, passwords, production credentials, private customer data, or regulated records.</li>
          <li>Anything requiring an NDA before scope and handling rules are confirmed.</li>
        </ul>
      </section>
      <section class="panel">
        <h2>Initial AI Inspection</h2>
        <ul>
          <li>Classifies the request into advisory, audit, custom overlay, subcontract, or training.</li>
          <li>Checks for missing scope, unsafe secrets, obvious abuse risk, and fastest useful first deliverable.</li>
          <li>Produces a buyer recap and follow-up checklist so the engagement starts with structure.</li>
        </ul>
      </section>
      <section class="panel">
        <h2>Useful Links</h2>
        <ul>
          <li><a href="/hire">Open the hire page</a></li>
          <li><a href="/v1/polly/catalog">View the live product catalog</a></li>
          <li><a href="https://github.com/issdandavis/SCBE-AETHERMOORE">Review the public repository</a></li>
        </ul>
      </section>
    </main>
  </body>
</html>`;

module.exports = async function handler(req, res) {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.setHeader('Allow', 'GET, HEAD');
    return res.status(405).json({ ok: false, error: 'method_not_allowed' });
  }

  try {
    const html = fs.existsSync(FAST_START_PAGE)
      ? fs.readFileSync(FAST_START_PAGE, 'utf8')
      : INLINE_FAST_START_HTML;
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
