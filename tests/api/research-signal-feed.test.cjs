'use strict';

const assert = require('node:assert/strict');
const { afterEach, test } = require('node:test');

const handler = require('../../api/agent/research-signal-feed.js');
const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
});

function response(body, status = 200) {
  const bytes = Buffer.from(body);
  return {
    ok: status >= 200 && status < 300,
    status,
    async arrayBuffer() {
      return bytes;
    },
  };
}

function mockRes() {
  return {
    statusCode: 200,
    headers: {},
    body: '',
    setHeader(name, value) {
      this.headers[name.toLowerCase()] = value;
    },
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(value) {
      this.body = JSON.stringify(value);
      return this;
    },
    send(value) {
      this.body = String(value || '');
      return this;
    },
  };
}

function sampleRss(title) {
  return `<?xml version="1.0"?><rss><channel><item><title><![CDATA[${title} &amp; context]]></title><link>https://example.org/${encodeURIComponent(title)}</link><description><![CDATA[<b>Source supplied</b> summary]]></description><pubDate>Thu, 20 Aug 2026 10:00:00 GMT</pubDate></item></channel></rss>`;
}

function sampleAtom() {
  return `<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Verified robot preprint</title><id>https://arxiv.org/abs/2608.12345</id><link href="https://arxiv.org/abs/2608.12345" rel="alternate"/><published>2026-08-20T09:00:00Z</published><summary>Preprint abstract.</summary><author><name>A. Researcher</name></author></entry></feed>`;
}

function sampleCrossref() {
  return JSON.stringify({
    message: {
      items: [
        {
          DOI: '10.1000/research-signal',
          URL: 'https://doi.org/10.1000/research-signal',
          title: ['Governed research streams'],
          author: [{ given: 'Issac', family: 'Davis' }],
          'container-title': ['Test Journal'],
          published: { 'date-parts': [[2026, 8, 19]] },
        },
        {
          DOI: '10.1000/future-metadata-error',
          URL: 'https://doi.org/10.1000/future-metadata-error',
          title: ['Future metadata error'],
          published: { 'date-parts': [[2121, 1, 1]] },
        },
      ],
    },
  });
}

test('aggregates independent source lanes and strips feed markup', async () => {
  global.fetch = async (url) => {
    const parsed = new URL(url);
    if (parsed.hostname === 'export.arxiv.org') return response(sampleAtom());
    if (parsed.hostname === 'api.crossref.org') return response(sampleCrossref());
    return response(sampleRss(parsed.hostname));
  };

  const res = mockRes();
  await handler({ method: 'GET', query: {} }, res);

  assert.equal(res.statusCode, 200);
  const payload = JSON.parse(res.body);
  assert.equal(payload.schema, 'aethermoore-research-signal-v1');
  assert.equal(payload.status.length, 7);
  assert.ok(payload.status.every((source) => source.ok));
  assert.ok(payload.items.some((item) => item.channel === 'world'));
  assert.ok(payload.items.some((item) => item.channel === 'research'));
  assert.ok(payload.items.some((item) => item.channel === 'space'));
  assert.ok(payload.items.every((item) => item.url.startsWith('https://')));
  assert.ok(payload.items.every((item) => !/[<>]/.test(item.summary)));
  assert.ok(payload.items.every((item) => item.title !== 'Future metadata error'));
  assert.match(res.headers['cache-control'], /stale-while-revalidate/);
});

test('returns partial results and visible status when one source fails', async () => {
  global.fetch = async (url) => {
    const parsed = new URL(url);
    if (parsed.hostname === 'feeds.bbci.co.uk') throw new Error('upstream_timeout');
    if (parsed.hostname === 'export.arxiv.org') return response(sampleAtom());
    if (parsed.hostname === 'api.crossref.org') return response(sampleCrossref());
    return response(sampleRss(parsed.hostname));
  };

  const res = mockRes();
  await handler({ method: 'GET', query: {} }, res);
  const payload = JSON.parse(res.body);

  assert.equal(res.statusCode, 200);
  assert.ok(payload.items.length > 0);
  assert.equal(payload.status.find((source) => source.id === 'bbc-world').ok, false);
  assert.equal(payload.status.find((source) => source.id === 'arxiv').ok, true);
});

test('serves a subscribable RSS view and rejects write methods', async () => {
  global.fetch = async (url) => {
    const parsed = new URL(url);
    if (parsed.hostname === 'export.arxiv.org') return response(sampleAtom());
    if (parsed.hostname === 'api.crossref.org') return response(sampleCrossref());
    return response(sampleRss(parsed.hostname));
  };

  const rss = mockRes();
  await handler({ method: 'GET', query: { format: 'rss' } }, rss);
  assert.equal(rss.statusCode, 200);
  assert.match(rss.headers['content-type'], /application\/rss\+xml/);
  assert.match(rss.body, /<title>AetherMoore Research Signal<\/title>/);
  assert.match(rss.body, /<item>/);

  const post = mockRes();
  await handler({ method: 'POST', query: {} }, post);
  assert.equal(post.statusCode, 405);
  assert.match(post.body, /method_not_allowed/);
});

test('parser helpers reject script URLs and remove markup', () => {
  assert.equal(handler._test.safeUrl('javascript:alert(1)'), '');
  assert.equal(handler._test.cleanText('<script>bad()</script><b>good</b>'), 'good');
  assert.equal(handler._test.sourceDefinitions().length, 7);
});
