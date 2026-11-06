'use strict';

const path = require('node:path');
const { resolveNative } = require('./cli-host');
const { probe } = require('./process-diagnostics');

function createShellResolver(options = {}) {
  const platform = options.platform || process.platform;
  const env = options.env || process.env;
  const resolve = options.resolve || ((name) => resolveNative(name, env, platform));
  let cached;
  function inspect(refresh = false) {
    if (cached && !refresh) return structuredClone(cached);
    if (platform !== 'win32') {
      const selected = resolve('/bin/sh');
      const result = selected ? probe(selected, ['-c', 'exit 0'], { ...options, env }) : null;
      cached = {
        kind: 'posix',
        selected: result?.status === 'ready' ? selected : null,
        attempts: result ? [result] : [],
        status: result?.status || 'missing_executable',
      };
      return structuredClone(cached);
    }
    const candidates = [
      ...(env.SCBE_POWERSHELL ? [{ label: 'configured', value: env.SCBE_POWERSHELL }] : []),
      { label: 'PowerShell 7 on PATH', value: 'pwsh' },
      {
        label: 'Windows PowerShell',
        value: path.win32.join(
          env.SystemRoot || 'C:\\Windows',
          'System32',
          'WindowsPowerShell',
          'v1.0',
          'powershell.exe'
        ),
      },
      { label: 'Windows PowerShell on PATH', value: 'powershell' },
    ];
    const attempts = [];
    const seen = new Set();
    let selected = null;
    for (const candidate of candidates) {
      const executable = resolve(candidate.value);
      if (!executable) {
        attempts.push({
          candidate: candidate.label,
          executable: null,
          status: 'missing_executable',
        });
        continue;
      }
      const key = executable.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      const result = probe(
        executable,
        [
          '-NoLogo',
          '-NoProfile',
          '-NonInteractive',
          '-Command',
          '$PSVersionTable.PSVersion.ToString()',
        ],
        { ...options, env, timeoutMs: 5000 }
      );
      if (result.status === 'ready' && !result.version) {
        result.status = 'invalid_probe_output';
        result.next_step = 'The executable did not return a PowerShell version.';
      }
      attempts.push({ candidate: candidate.label, ...result });
      if (result.status === 'ready') {
        selected = executable;
        break;
      }
    }
    cached = {
      kind: 'powershell',
      selected,
      status: selected ? 'ready' : 'shell_unavailable',
      attempts,
    };
    return structuredClone(cached);
  }
  return { inspect, resolve: () => inspect().selected };
}

const current = createShellResolver();
module.exports = {
  createShellResolver,
  inspectShell: current.inspect,
  resolvePowerShellCommand: current.resolve,
};
