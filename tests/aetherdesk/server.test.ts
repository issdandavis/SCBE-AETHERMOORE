import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import * as http from 'http';
import { AddressInfo } from 'net';

// eslint-disable-next-line @typescript-eslint/no-require-imports
const aetherdesk = require('../../aetherdesk/server.js');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const RECEIPTS_DIR = path.join(REPO_ROOT, 'artifacts', 'aetherdesk_receipts');

let server: http.Server;
let baseUrl: string;

function fetchJson(url: string, init?: RequestInit) {
  return fetch(url, init).then((r) => r.json().then((b) => ({ status: r.status, body: b })));
}

beforeEach(async () => {
  const app = aetherdesk.buildApp();
  await new Promise<void>((resolve) => {
    server = app.listen(0, '127.0.0.1', () => resolve());
  });
  const addr = server.address() as AddressInfo;
  baseUrl = `http://127.0.0.1:${addr.port}`;
});

afterEach(async () => {
  await new Promise<void>((resolve) => server.close(() => resolve()));
});

describe('AetherDesk server — health + introspection', () => {
  it('GET /api/health returns ok', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/health`);
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.schema).toBe('aetherdesk_health_v0');
  });

  it('GET /api/commands lists the spec commands plus app launcher tiles', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/commands`);
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.schema).toBe('aetherdesk_commands_v0');
    const ids = body.commands.map((c: { id: string }) => c.id);
    // the original spec commands must remain (containment, not exact -- the shell grows as tools wire in)
    for (const core of [
      'typecheck',
      'ts_tests',
      'benchmark_cli',
      'chemistry_lookup',
      'forge_demo',
      'rosetta_demo',
    ]) {
      expect(ids).toContain(core);
    }
    // the wired-in SCBE tools (step 1: tools into the shell)
    for (const tool of [
      'host_check',
      'coding_ladder',
      'reasoning_ladder',
      'stepwise',
      'failure_map',
      'pazaak_board',
      'mahss_game_gym',
    ]) {
      expect(ids).toContain(tool);
    }
  });

  it('every command surface includes launcher metadata', async () => {
    const { body } = await fetchJson(`${baseUrl}/api/commands`);
    for (const c of body.commands) {
      expect(typeof c.label).toBe('string');
      expect(typeof c.npm_script).toBe('string');
      expect(typeof c.category).toBe('string');
      expect(typeof c.icon).toBe('string');
      expect(typeof c.risk_tier).toBe('string');
      expect(typeof c.description).toBe('string');
      expect(c.label.length).toBeGreaterThan(0);
    }
  });
});

describe('AetherDesk server — allowlist enforcement (security boundary)', () => {
  it('POST /api/run/<known> resolves to a known command id without spawning', async () => {
    // We don't actually invoke runCommand here (it spawns npm). We verify
    // that the allowlist export contains only the bounded launcher entries.
    const ids = Object.keys(aetherdesk.COMMAND_ALLOWLIST);
    // every entry is a bounded {npmScript} reference -- no raw shell strings (the security boundary)
    for (const id of ids) {
      expect(typeof aetherdesk.COMMAND_ALLOWLIST[id].npmScript).toBe('string');
    }
    for (const core of ['typecheck', 'forge_demo', 'host_check', 'coding_ladder']) {
      expect(ids).toContain(core);
    }
  });

  it('POST /api/run/<unknown> rejects with 400 and does not run anything', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/run/rm_dash_rf`, { method: 'POST' });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
    expect(body.error).toMatch(/not allowlisted/i);
    expect(body.command_id).toBe('rm_dash_rf');
  });

  it('POST /api/run/<shell-injection-attempt> rejects with 400', async () => {
    const malicious = encodeURIComponent('typecheck; rm -rf /');
    const { status, body } = await fetchJson(`${baseUrl}/api/run/${malicious}`, { method: 'POST' });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
  });

  it('POST /api/run/<prototype-pollution-attempt> rejects with 400', async () => {
    // Object.prototype.hasOwnProperty test: __proto__ MUST NOT be treated
    // as an allowlisted command even though it lives on Object.prototype.
    const { status, body } = await fetchJson(`${baseUrl}/api/run/__proto__`, { method: 'POST' });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
  });
});

describe('AetherDesk server — bounded shell profiles', () => {
  it('GET /api/shell/profiles lists bounded shell profiles without raw command text', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/shell/profiles`);
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.schema).toBe('aetherdesk_shell_profiles_v0');
    const ids = body.profiles.map((p: { id: string }) => p.id).sort();
    expect(ids).toEqual([
      'agent_shell_codex_brief',
      'agent_shell_probe',
      'git_status',
      'powershell_probe',
      'pwd',
    ]);
    for (const p of body.profiles) {
      expect(typeof p.label).toBe('string');
      expect(typeof p.shell).toBe('string');
      expect(typeof p.risk_tier).toBe('string');
      expect(typeof p.description).toBe('string');
      expect(p.command).toBeUndefined();
      expect(p.args).toBeUndefined();
    }
  });

  it('POST /api/shell/run rejects arbitrary shell text', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/shell/run`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ id: 'Get-ChildItem; Remove-Item C:\\\\' }),
    });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
    expect(body.error).toMatch(/not allowlisted/i);
  });

  it('shell allowlist export contains only bounded profiles', () => {
    const ids = Object.keys(aetherdesk.SHELL_ALLOWLIST).sort();
    expect(ids).toEqual([
      'agent_shell_codex_brief',
      'agent_shell_probe',
      'git_status',
      'powershell_probe',
      'pwd',
    ]);
  });

  it('read-only agent profile passes the Agent Shell worktree guard', () => {
    const profile = aetherdesk.SHELL_ALLOWLIST.agent_shell_codex_brief;
    expect(profile.args).toContain('--readonly-worktree');
    expect(profile.risk_tier).toBe('read-only-agent');
  });
});

describe('AetherDesk server — bounded PowerShell terminal', () => {
  it('validates PowerShell text before execution', () => {
    expect(aetherdesk.validatePowerShellCommand('Get-Location').ok).toBe(true);
    expect(aetherdesk.validatePowerShellCommand('').ok).toBe(false);
    expect(aetherdesk.validatePowerShellCommand('Remove-Item C:\\\\Temp -Recurse').ok).toBe(false);
    expect(aetherdesk.validatePowerShellCommand('Get-ChildItem > out.txt').ok).toBe(false);
  });

  it('POST /api/powershell/run executes a harmless command and writes a receipt', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/powershell/run`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ command: 'Write-Output AETHERDESK_OK' }),
    });
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.receipt.command_id).toBe('powershell:command');
    expect(body.receipt.risk_tier).toBe('bounded-host-read');
    expect(body.receipt.stdout_tail).toContain('AETHERDESK_OK');
    expect(body.receipt.command_digest).toMatch(/^[a-f0-9]{64}$/);
  });

  it('POST /api/powershell/run blocks destructive commands before execution', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/powershell/run`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ command: 'Remove-Item C:\\\\Users -Recurse -Force' }),
    });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
    expect(body.error).toMatch(/blocked/i);
    expect(body.receipt.command_label).toBe('PowerShell blocked');
    expect(body.receipt.exit_code).toBe(126);
  });
});

describe('AetherDesk server — receipt schema + listing', () => {
  it('buildReceipt produces an aetherdesk_receipt_v0 with the required fields', () => {
    const r = aetherdesk.buildReceipt({
      commandId: 'typecheck',
      exitCode: 0,
      stdoutTail: 'ok',
      stderrTail: '',
      startedAt: '2026-05-10T12:00:00.000Z',
      finishedAt: '2026-05-10T12:00:01.500Z',
      artifactPath: null,
    });
    expect(r.schema).toBe('aetherdesk_receipt_v0');
    expect(r.command_id).toBe('typecheck');
    expect(r.command).toBe('npm run typecheck');
    expect(r.command_digest).toMatch(/^[a-f0-9]{64}$/);
    expect(r.exit_code).toBe(0);
    expect(r.result).toBe('pass');
    expect(r.duration_ms).toBe(1500);
    expect(r.risk_tier).toBe('read-only');
    expect(r.allowed_paths).toEqual(['<repo-readonly>']);
    expect(r.task_id).toMatch(/_typecheck$/);
  });

  it('non-zero exit code maps to result=fail', () => {
    const r = aetherdesk.buildReceipt({
      commandId: 'typecheck',
      exitCode: 1,
      stdoutTail: '',
      stderrTail: 'TS2322 error',
      startedAt: '2026-05-10T12:00:00.000Z',
      finishedAt: '2026-05-10T12:00:00.500Z',
      artifactPath: null,
    });
    expect(r.exit_code).toBe(1);
    expect(r.result).toBe('fail');
  });

  it('GET /api/receipts returns a list bounded by limit', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/receipts?limit=5`);
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.schema).toBe('aetherdesk_receipt_list_v0');
    expect(Array.isArray(body.receipts)).toBe(true);
    expect(body.receipts.length).toBeLessThanOrEqual(5);
  });

  it('GET /api/receipts/<traversal-attempt> rejects', async () => {
    const malicious = encodeURIComponent('../../../etc/passwd');
    const { status, body } = await fetchJson(`${baseUrl}/api/receipts/${malicious}`);
    expect(status).toBe(404);
    expect(body.ok).toBe(false);
  });

  it('GET /api/receipts/<bad-name> rejects (no path traversal, only safe chars)', async () => {
    const { status } = await fetchJson(`${baseUrl}/api/receipts/some%2Fnested%2Ffile.json`);
    expect(status).toBe(404);
  });
});

describe('AetherDesk server — receipt round-trip on disk', () => {
  it('writeReceipt + listReceipts + readReceipt round-trips a receipt', () => {
    const r = aetherdesk.buildReceipt({
      commandId: 'typecheck',
      exitCode: 0,
      stdoutTail: 'all good',
      stderrTail: '',
      startedAt: '2026-05-10T12:00:00.000Z',
      finishedAt: '2026-05-10T12:00:00.250Z',
      artifactPath: null,
    });
    const filePath = aetherdesk.writeReceipt(r);
    expect(fs.existsSync(filePath)).toBe(true);

    const list = aetherdesk.listReceipts(50);
    const found = list.find((x: { task_id: string }) => x.task_id === r.task_id);
    expect(found).toBeTruthy();

    const file = path.basename(filePath);
    const readBack = aetherdesk.readReceipt(file);
    expect(readBack).toBeTruthy();
    expect(readBack.task_id).toBe(r.task_id);
    expect(readBack.command_digest).toBe(r.command_digest);

    // Cleanup
    fs.unlinkSync(filePath);
  });

  it('readReceipt rejects names with separators or traversal', () => {
    expect(aetherdesk.readReceipt('../etc/passwd')).toBeNull();
    expect(aetherdesk.readReceipt('foo/bar.json')).toBeNull();
    expect(aetherdesk.readReceipt('foo\\bar.json')).toBeNull();
  });
});

describe('AetherDesk server — output truncation', () => {
  it('tailBytes truncates oversized output and adds a marker', () => {
    const big = 'A'.repeat(20000);
    const tail = aetherdesk._private.tailBytes(big, 8192);
    expect(tail.length).toBeLessThan(big.length);
    expect(tail).toMatch(/truncated/);
    expect(tail.endsWith('A'.repeat(100))).toBe(true);
  });

  it('tailBytes leaves small output untouched', () => {
    const small = 'B'.repeat(100);
    expect(aetherdesk._private.tailBytes(small, 8192)).toBe(small);
  });
});

// Smoke marker: confirm the receipts dir is created on demand under artifacts/
describe('AetherDesk server — receipts directory', () => {
  it('RECEIPTS_DIR resolves under artifacts/', () => {
    expect(aetherdesk.RECEIPTS_DIR.replace(/\\/g, '/')).toMatch(/artifacts\/aetherdesk_receipts$/);
    expect(aetherdesk.RECEIPTS_DIR.startsWith(REPO_ROOT)).toBe(true);
    expect(RECEIPTS_DIR).toBe(aetherdesk.RECEIPTS_DIR);
  });
});

describe('AetherDesk server — Provider Status (v0.1)', () => {
  it('PROVIDER_DEFS includes the spec providers (ollama, lmstudio, hf, anthropic, openai)', () => {
    const ids = aetherdesk.PROVIDER_DEFS.map((p: { id: string }) => p.id);
    expect(ids).toEqual(
      expect.arrayContaining(['ollama', 'lmstudio', 'huggingface', 'anthropic', 'openai'])
    );
  });

  it('GET /api/providers returns the v0 schema and a result per provider', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/providers`);
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.schema).toBe('aetherdesk_providers_v0');
    expect(body.generated_at).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    expect(Array.isArray(body.providers)).toBe(true);
    expect(body.providers.length).toBe(aetherdesk.PROVIDER_DEFS.length);
    for (const p of body.providers) {
      expect(typeof p.id).toBe('string');
      expect(typeof p.label).toBe('string');
      expect(['local-http', 'env-var']).toContain(p.kind);
    }
  }, 10000);

  it('local-http providers report reachable + latency_ms (or an error)', async () => {
    const { body } = await fetchJson(`${baseUrl}/api/providers`);
    const httpProviders = body.providers.filter((p: { kind: string }) => p.kind === 'local-http');
    expect(httpProviders.length).toBeGreaterThan(0);
    for (const p of httpProviders) {
      expect(typeof p.reachable).toBe('boolean');
      expect(typeof p.latency_ms).toBe('number');
      expect(p.url).toMatch(/^http/);
      // We don't assert true/false reachable — depends on what's running locally.
    }
  }, 10000);

  it('env-var providers never expose secret values, only presence + name', async () => {
    const { body } = await fetchJson(`${baseUrl}/api/providers`);
    const envProviders = body.providers.filter((p: { kind: string }) => p.kind === 'env-var');
    expect(envProviders.length).toBeGreaterThan(0);
    for (const p of envProviders) {
      expect(typeof p.has_secret).toBe('boolean');
      expect(Array.isArray(p.env_vars_checked)).toBe(true);
      // The env_vars_checked is just NAMES, not values:
      for (const name of p.env_vars_checked) {
        expect(typeof name).toBe('string');
        // Sanity: shouldn't look like an API key
        expect(name).not.toMatch(/^sk-/);
        expect(name).not.toMatch(/^hf_/);
      }
      // secret_env_var is the matched name (or null), never the value
      if (p.has_secret) {
        expect(p.env_vars_checked).toContain(p.secret_env_var);
      } else {
        expect(p.secret_env_var).toBeNull();
      }
    }
  }, 10000);

  it('probeEnv detects truthy env vars and returns the matched name', () => {
    const KEY = '__AETHERDESK_TEST_KEY_' + Math.random().toString(36).slice(2);
    expect(aetherdesk.probeEnv([KEY])).toEqual({ has_secret: false, secret_env_var: null });
    process.env[KEY] = 'sentinel-value';
    try {
      const r = aetherdesk.probeEnv([KEY, 'OTHER_NAME']);
      expect(r.has_secret).toBe(true);
      expect(r.secret_env_var).toBe(KEY);
    } finally {
      delete process.env[KEY];
    }
  });

  it('probeEnv treats empty string as not-set', () => {
    const KEY = '__AETHERDESK_EMPTY_' + Math.random().toString(36).slice(2);
    process.env[KEY] = '';
    try {
      const r = aetherdesk.probeEnv([KEY]);
      expect(r.has_secret).toBe(false);
      expect(r.secret_env_var).toBeNull();
    } finally {
      delete process.env[KEY];
    }
  });
});

describe('AetherDesk server — Playwright Vision boundary', () => {
  it('normalizes Playwright URLs conservatively', () => {
    expect(aetherdesk.normalizePlaywrightUrl('example.com')).toBe('https://example.com/');
    expect(aetherdesk.normalizePlaywrightUrl('https://example.com/path')).toBe(
      'https://example.com/path'
    );
    expect(aetherdesk.normalizePlaywrightUrl('about:blank')).toBe('about:blank');
  });

  it('rejects unsafe Playwright URL schemes and embedded credentials', () => {
    expect(() => aetherdesk.normalizePlaywrightUrl('file:///C:/Windows/win.ini')).toThrow(
      /only http/i
    );
    expect(() => aetherdesk.normalizePlaywrightUrl('https://user:pass@example.com')).toThrow(
      /credentials/i
    );
  });

  it('POST /api/playwright/view rejects unsafe URLs before launching a browser', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/playwright/view`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ url: 'file:///C:/Windows/win.ini' }),
    });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
    expect(body.error).toMatch(/only http/i);
  });

  it('browser action validators reject unsafe actions, sessions, and selectors', () => {
    expect(aetherdesk.normalizeBrowserAction('goto')).toBe('goto');
    expect(aetherdesk.normalizeBrowserAction('aria')).toBe('aria');
    expect(aetherdesk.normalizeBrowserAction('guide')).toBe('guide');
    expect(aetherdesk.normalizeSessionId('main.1')).toBe('main.1');
    expect(aetherdesk.normalizeSelector('#q')).toBe('#q');
    expect(() => aetherdesk.normalizeBrowserAction('delete')).toThrow(/unsupported/i);
    expect(() => aetherdesk.normalizeSessionId('../x')).toThrow(/invalid/i);
    expect(() => aetherdesk.normalizeSelector('')).toThrow(/selector/i);
  });

  it('POST /api/browser/action rejects unsafe goto URLs before launching a page', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/browser/action`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ action: 'goto', session_id: 'main', url: 'file:///C:/Windows/win.ini' }),
    });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
    expect(body.error).toMatch(/only http/i);
  });

  it('POST /api/browser/action rejects unsupported actions', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/browser/action`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ action: 'format-disk', session_id: 'main' }),
    });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
    expect(body.error).toMatch(/unsupported/i);
  });
});

describe('AetherDesk server — transcript, email, notebook apps', () => {
  it('extracts YouTube video IDs from common URL forms', () => {
    expect(aetherdesk.extractYouTubeVideoId('dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    expect(aetherdesk.extractYouTubeVideoId('https://youtu.be/dQw4w9WgXcQ')).toBe('dQw4w9WgXcQ');
    expect(aetherdesk.extractYouTubeVideoId('https://www.youtube.com/watch?v=dQw4w9WgXcQ')).toBe(
      'dQw4w9WgXcQ'
    );
    expect(aetherdesk.extractYouTubeVideoId('https://www.youtube.com/shorts/dQw4w9WgXcQ')).toBe(
      'dQw4w9WgXcQ'
    );
  });

  it('POST /api/youtube/transcript rejects invalid targets before external fetch', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/youtube/transcript`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ target: 'bad' }),
    });
    expect(status).toBe(400);
    expect(body.ok).toBe(false);
    expect(body.error).toMatch(/invalid|youtube/i);
  });

  it('validates email drafts and refuses send-shaped misuse', () => {
    const draft = aetherdesk.validateEmailDraft({
      to: 'test@example.com',
      subject: 'Hello',
      body: 'Draft only',
    });
    expect(draft.to).toBe('test@example.com');
    expect(() => aetherdesk.validateEmailDraft({ to: 'bad', subject: 'x', body: 'y' })).toThrow(
      /email address/i
    );
    expect(aetherdesk.createEmailDraft({ to: 'test@example.com', subject: 'Saved', body: 'Body' }).status).toBe(
      'draft_only_not_sent'
    );
  });

  it('POST /api/email/draft writes a draft artifact and never reports sent', async () => {
    const { status, body } = await fetchJson(`${baseUrl}/api/email/draft`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ to: 'desk@example.com', subject: 'AetherDesk', body: 'Draft body' }),
    });
    expect(status).toBe(200);
    expect(body.ok).toBe(true);
    expect(body.schema).toBe('aetherdesk_email_draft_v0');
    expect(body.status).toBe('draft_only_not_sent');
    expect(body.artifact_path).toMatch(/artifacts\/aetherdesk_email_drafts/);
    expect(fs.existsSync(path.join(REPO_ROOT, body.artifact_path))).toBe(true);
    fs.unlinkSync(path.join(REPO_ROOT, body.artifact_path));
  });

  it('notebook IDs reject traversal and round-trip through the API', async () => {
    expect(aetherdesk.normalizeNotebookId('default.notes')).toBe('default.notes');
    expect(() => aetherdesk.normalizeNotebookId('../bad')).toThrow(/invalid/i);

    const id = `test_${Date.now()}`;
    const saved = await fetchJson(`${baseUrl}/api/notebook/${id}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ title: 'Test Notes', body: 'line one' }),
    });
    expect(saved.status).toBe(200);
    expect(saved.body.ok).toBe(true);
    expect(saved.body.artifact_path).toMatch(/artifacts\/aetherdesk_notebooks/);

    const loaded = await fetchJson(`${baseUrl}/api/notebook/${id}`);
    expect(loaded.status).toBe(200);
    expect(loaded.body.title).toBe('Test Notes');
    expect(loaded.body.body).toBe('line one');
    fs.unlinkSync(path.join(REPO_ROOT, saved.body.artifact_path));
  });
});

describe('AetherDesk server — desktop UI is served', () => {
  function fetchText(url: string) {
    return fetch(url).then((r) =>
      r.text().then((t) => ({ status: r.status, type: r.headers.get('content-type'), body: t }))
    );
  }

  it('GET / serves the desktop shell as HTML', async () => {
    const { status, type, body } = await fetchText(`${baseUrl}/`);
    expect(status).toBe(200);
    expect(type).toMatch(/text\/html/);
    expect(body).toContain('<title>');
  });

  it('the served shell includes every app-window surface', async () => {
    const { body } = await fetchText(`${baseUrl}/`);
    for (const app of [
      'browser',
      'playwright',
      'youtube',
      'email',
      'notebook',
      'word',
      'editor',
      'image',
      'speech',
      'vision',
      'receipts',
      'providers',
    ]) {
      expect(body).toContain(`id="window-${app}"`);
    }
  });

  it('the terminal advertises agent shell aliases', async () => {
    const { body } = await fetchText(`${baseUrl}/`);
    expect(body).toContain('agent probe');
    expect(body).toContain('agent codex');
    expect(body).toContain('AG: ');
    expect(body).toContain('pwsh Get-ChildItem');
    expect(body).toContain('/api/powershell/run');
  });

  it('the desktop shell includes Playwright Vision controls', async () => {
    const { body } = await fetchText(`${baseUrl}/`);
    expect(body).toContain('id="window-playwright"');
    expect(body).toContain('Playwright Vision');
    expect(body).toContain('data-open="playwright"');
    expect(body).toContain('/api/browser/action');
    expect(body).toContain('id="playwright-text"');
    expect(body).toContain('id="playwright-aria"');
    expect(body).toContain('id="playwright-guide"');
    expect(body).toContain('id="playwright-close-session"');
  });

  it('the served shell includes headed transcript, email, and notebook apps', async () => {
    const { body } = await fetchText(`${baseUrl}/`);
    expect(body).toContain('id="window-youtube"');
    expect(body).toContain('id="youtube-pull"');
    expect(body).toContain('/api/youtube/transcript');
    expect(body).toContain('id="window-email"');
    expect(body).toContain('id="email-save-draft"');
    expect(body).toContain('/api/email/draft');
    expect(body).toContain('id="window-notebook"');
    expect(body).toContain('id="notebook-save"');
    expect(body).toContain('/api/notebook/');
  });

  it('the served shell carries no removed Kimi branding', async () => {
    const { body } = await fetchText(`${baseUrl}/`);
    expect(body.toLowerCase()).not.toContain('kimi');
  });

  it('snap-full controls render a real glyph, not a broken placeholder', async () => {
    const { body } = await fetchText(`${baseUrl}/`);
    // regression guard: the launcher/terminal/receipts/providers snap-full buttons once showed a lone "?"
    expect(body).not.toMatch(/title="Snap full">\?</);
  });
});
