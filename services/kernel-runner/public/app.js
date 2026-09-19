const el = (id) => document.getElementById(id);
const statusEl = el('status');
const resultEl = el('result');
const outputEl = el('output');

const defaultPackageJson = {
  name: 'sandbox-demo',
  version: '1.0.0',
  private: true,
  scripts: {
    test: 'node index.js',
  },
  dependencies: {
    lodash: '^4.17.21',
  },
};

const defaultFiles = {
  'index.js': "const _ = require('lodash');\nconsole.log('sum:', _.sum([1,2,3,4]));\n",
};

el('packageJson').value = JSON.stringify(defaultPackageJson, null, 2);
el('files').value = JSON.stringify(defaultFiles, null, 2);

function setStatus(text, isError = false) {
  statusEl.textContent = text;
  statusEl.style.color = isError ? '#ff8787' : '#98f5a7';
}

function setJSON(target, value) {
  target.textContent = JSON.stringify(value, null, 2);
}

function readPayload() {
  const packageJsonText = el('packageJson').value || '{}';
  const filesText = el('files').value || '{}';
  let packageJson;
  let files;
  try {
    packageJson = JSON.parse(packageJsonText);
  } catch {
    throw new Error('package.json must be valid JSON');
  }
  try {
    files = JSON.parse(filesText);
  } catch {
    throw new Error('files must be valid JSON object');
  }
  return {
    packageJson,
    files,
    runCommand: el('runCommand').value || 'npm test',
    allowNetworkInstall: el('allowNetworkInstall').checked,
  };
}

function toHex(bytes) {
  return Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
}

function randomNonce() {
  const bytes = crypto.getRandomValues(new Uint8Array(18));
  return btoa(String.fromCharCode(...bytes))
    .replaceAll('+', '-')
    .replaceAll('/', '_')
    .replaceAll('=', '');
}

async function signedHeaders(path, bodyText) {
  const secret = el('sharedSecret').value;
  const encoder = new TextEncoder();
  if (encoder.encode(secret).byteLength < 32) {
    throw new Error('Service secret must be at least 32 UTF-8 bytes.');
  }
  const timestamp = Date.now();
  const nonce = randomNonce();
  const bodyHash = toHex(
    new Uint8Array(await crypto.subtle.digest('SHA-256', encoder.encode(bodyText)))
  );
  const canonical = ['scbe-kernel-v1', 'POST', path, String(timestamp), nonce, bodyHash].join('\n');
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const signature = toHex(
    new Uint8Array(await crypto.subtle.sign('HMAC', key, encoder.encode(canonical)))
  );
  return {
    'Content-Type': 'application/json',
    'X-SCBE-Auth-Version': 'scbe-kernel-v1',
    'X-SCBE-Timestamp': String(timestamp),
    'X-SCBE-Nonce': nonce,
    'X-SCBE-Signature': signature,
  };
}

async function callApi(path, payload) {
  const bodyText = payload ? JSON.stringify(payload) : undefined;
  const response = await fetch(path, {
    method: payload ? 'POST' : 'GET',
    headers: payload ? await signedHeaders(path, bodyText) : undefined,
    body: bodyText,
  });
  const data = await response.json();
  return { ok: response.ok, data };
}

el('btnHealth').addEventListener('click', async () => {
  setStatus('Checking health...');
  outputEl.textContent = '';
  try {
    const { ok, data } = await callApi('/api/health');
    setStatus(ok ? 'Health OK' : 'Health failed', !ok);
    setJSON(resultEl, data);
  } catch (error) {
    setStatus(String(error.message || error), true);
  }
});

el('btnPreflight').addEventListener('click', async () => {
  setStatus('Running preflight...');
  outputEl.textContent = '';
  try {
    const payload = readPayload();
    const { ok, data } = await callApi('/api/preflight', payload);
    setStatus(
      ok ? `Decision: ${data?.decision_record?.action || 'UNKNOWN'}` : 'Preflight failed',
      !ok
    );
    setJSON(resultEl, data);
  } catch (error) {
    setStatus(String(error.message || error), true);
  }
});

el('btnRun').addEventListener('click', async () => {
  setStatus('Running sandbox...');
  try {
    const payload = readPayload();
    const { ok, data } = await callApi('/api/run', payload);
    setStatus(ok ? 'Run completed' : 'Run blocked/failed', !ok);
    setJSON(resultEl, data);
    const installOut = data?.install?.stdout || '';
    const installErr = data?.install?.stderr || '';
    const executeOut = data?.execute?.stdout || '';
    const executeErr = data?.execute?.stderr || '';
    outputEl.textContent = [
      '=== INSTALL STDOUT ===',
      installOut,
      '',
      '=== INSTALL STDERR ===',
      installErr,
      '',
      '=== EXECUTE STDOUT ===',
      executeOut,
      '',
      '=== EXECUTE STDERR ===',
      executeErr,
    ].join('\n');
  } catch (error) {
    setStatus(String(error.message || error), true);
  }
});
