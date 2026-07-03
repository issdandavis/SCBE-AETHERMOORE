// @ts-nocheck
import { describe, expect, it } from 'vitest';
import { join } from 'node:path';

const bridge = await import('../../scripts/system/aetherbrowser_mcp_server.mjs');

describe('aetherbrowser MCP bridge', () => {
  it('builds allowlisted agent arguments for named targets', () => {
    expect(
      bridge.buildAgentArgs('start', {
        target: 'github',
        port: 9444,
        profile_name: 'seller-demo',
        headless: true,
      })
    ).toEqual([
      'start',
      '--port',
      '9444',
      '--profile',
      join(process.env.USERPROFILE || '', '.aetherdesk', 'browser-profiles', 'seller-demo'),
      '--target',
      'github',
      '--headless',
    ]);
  });

  it('rejects ambiguous open destinations before shelling out', () => {
    expect(() =>
      bridge.buildAgentArgs('open', {
        url: 'https://example.com',
        target: 'github',
      })
    ).toThrow(/either url or target/i);
  });

  it('keeps screenshot artifacts inside the MCP artifact root', () => {
    const outDir = bridge.resolveArtifactDir('demo-run');

    expect(outDir).toBe(join(bridge.DEFAULT_ARTIFACT_ROOT, 'demo-run'));
    expect(() => bridge.resolveArtifactDir('..\\escape')).toThrow(/artifact_subdir/i);
  });

  it('builds the local voiceover command with explicit speak-now opt in', () => {
    expect(
      bridge.buildAgentArgs('voiceover', {
        text: 'Speak this product note.',
        artifact_subdir: 'voice-demo',
        voice: 'Zira',
        rate: 1,
        engine: 'sapi',
        basename: 'product-note',
        speak_now: true,
      })
    ).toEqual([
      'voiceover',
      '--text',
      'Speak this product note.',
      '--out-dir',
      join(bridge.DEFAULT_VOICEOVER_ARTIFACT_ROOT, 'voice-demo'),
      '--voice',
      'Zira',
      '--rate',
      '1',
      '--engine',
      'sapi',
      '--basename',
      'product-note',
      '--speak-now',
    ]);
  });

  it('builds the local voice-code command for governed musical code receipts', () => {
    expect(
      bridge.buildAgentArgs('voice-code', {
        action: 'guitar',
        artifact_subdir: 'voice-code-demo',
        notes: 'E E G',
        dialect: 'E minor',
        basename: 'guitar-smoke',
        speak: false,
      })
    ).toEqual([
      'voice-code',
      '--action',
      'guitar',
      '--out-dir',
      join(bridge.DEFAULT_VOICE_CODE_ARTIFACT_ROOT, 'voice-code-demo'),
      '--basename',
      'guitar-smoke',
      '--notes',
      'E E G',
      '--dialect',
      'E minor',
    ]);
  });

  it('parses JSON receipts even when a child process emits preface text', () => {
    const parsed = bridge.parseAgentStdout('debug line\n{"ok":true,"title":"Example"}');

    expect(parsed).toEqual({ ok: true, title: 'Example' });
  });

  it('wraps agent execution in a stable MCP result schema', () => {
    const calls = [];
    const result = bridge.runAgent(
      'doctor',
      {},
      {
        spawnSyncImpl(command, args, options) {
          calls.push({ command, args, cwd: options.cwd, env: options.env });
          return { status: 0, signal: null, stdout: '{"ok":true}', stderr: '' };
        },
      }
    );

    expect(result.ok).toBe(true);
    expect(result.schema_version).toBe('aetherbrowser-mcp-result-v1');
    expect(result.stdout).toEqual({ ok: true });
    expect(calls[0].args).toEqual([bridge.AGENT_PATH, 'doctor']);
    expect(calls[0].cwd).toBe(bridge.REPO_ROOT);
    expect(calls[0].env.AETHERBROWSER_MCP_BRIDGE).toBe('1');
  });

  it('declares the expected first-class tool names', () => {
    expect(bridge.TOOL_NAMES).toEqual([
      'aetherbrowser_doctor',
      'aetherbrowser_targets',
      'aetherbrowser_start',
      'aetherbrowser_status',
      'aetherbrowser_open',
      'aetherbrowser_inspect',
      'aetherbrowser_screen',
      'aetherbrowser_click_text',
      'aetherbrowser_type_text',
      'aetherbrowser_press_key',
      'aetherbrowser_monitor',
      'aetherbrowser_voiceover',
      'aetherbrowser_voice_code',
    ]);
  });
});
