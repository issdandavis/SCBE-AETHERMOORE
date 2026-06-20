const assert = require('node:assert/strict');
const test = require('node:test');
const { EventEmitter } = require('node:events');
const { execFileSync } = require('node:child_process');
const { mkdtempSync, existsSync, writeFileSync } = require('node:fs');
const { tmpdir } = require('node:os');
const { join } = require('node:path');

const handler = require('../../api/agent/geoseal-hermes.js');

function invoke(body) {
  const req = new EventEmitter();
  req.method = 'POST';
  req.body = body;
  const res = {
    statusCode: 200,
    headers: {},
    setHeader(name, value) {
      this.headers[name] = value;
    },
    status(code) {
      this.statusCode = code;
      return this;
    },
    json(payload) {
      this.payload = payload;
      return this;
    },
    end() {
      return this;
    },
  };
  return handler(req, res).then(() => res);
}

test('GeoSeal Hermes command output single-quotes shell metacharacters and exposes argv', async () => {
  const task = "deploy $(printf INJECTED > marker) `touch marker2` and 'quote'";
  const res = await invoke({ task, route_type: 'local', output_mode: 'json' });

  assert.equal(res.statusCode, 200);
  assert.deepEqual(res.payload.command_argv, ['geoseal', 'do', task, '--json']);
  assert.match(res.payload.command, /^geoseal do '/);
  assert.doesNotMatch(res.payload.command, /".*\$\(/);
  assert.match(res.payload.command, /'\\''quote'\\'''/);
});

test('GeoSeal Hermes generated command does not evaluate command substitution in POSIX shell', async () => {
  const temp = mkdtempSync(join(tmpdir(), 'geoseal-hermes-'));
  const marker = join(temp, 'pwned');
  const geoseal = join(temp, 'geoseal');
  writeFileSync(geoseal, '#!/bin/sh\nexit 0\n', { mode: 0o755 });

  const task = `deploy $(printf INJECTED > ${marker})`;
  const res = await invoke({ task, route_type: 'local', output_mode: 'json' });

  execFileSync('/bin/sh', ['-c', res.payload.command], {
    env: { ...process.env, PATH: `${temp}:${process.env.PATH}` },
  });
  assert.equal(existsSync(marker), false);
});
