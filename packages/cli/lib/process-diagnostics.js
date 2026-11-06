'use strict';

// Classify observed failures without returning potentially secret-bearing output.
function processDiagnosis(child = {}) {
  const code = child.error?.code || child.process_error;
  const text = `${child.stderr || ''}\n${child.stdout || ''}`.toLowerCase();
  if (code === 'ETIMEDOUT') return 'timeout';
  if (code === 'ENOBUFS') return 'output_limit';
  if (code === 'ENOENT') return 'missing_executable';
  if (['EACCES', 'EPERM', 'SHELL_UNAVAILABLE'].includes(code))
    return code === 'SHELL_UNAVAILABLE' ? 'shell_unavailable' : 'permission_denied';
  if (code) return 'startup_failed';
  if (child.status === 0) return 'ready';
  if (
    /invalid_grant|unauthenticated|authentication (?:is )?required|(?:token|credentials?) (?:has |have )?expired|expired (?:token|credentials?)|not logged in|http(?:\/\S+)?\s+401|bad credentials/.test(
      text
    )
  )
    return 'authentication_required';
  if (/access (?:is )?denied|permission denied|0x80041003|createprocessasuserw failed/.test(text))
    return 'permission_denied';
  if (/http(?:\/\S+)?\s+403|insufficient scopes?/.test(text)) return 'provider_access_denied';
  if (/not recognized|command not found|no such file or directory/.test(text))
    return 'missing_executable';
  return 'command_failed';
}

const NEXT_STEPS = {
  ready: 'The bounded probe succeeded in this process context.',
  missing_executable: 'Check the configured executable path and this process PATH.',
  permission_denied:
    'Check access under the same worker account and sandbox; signing into Google does not grant Windows permissions.',
  timeout: 'The bounded probe timed out. Inspect load and startup behavior before retrying.',
  output_limit: 'The probe exceeded its output limit.',
  startup_failed: 'The operating system could not start this executable.',
  shell_unavailable:
    'No PowerShell backend passed its probe; inspect the shell diagnostic attempts.',
  authentication_required:
    'The tool reported an authentication failure; reauthenticate that service through its normal sign-in flow.',
  provider_access_denied:
    'Check the service account permissions or scopes; this does not establish a local Windows permission failure.',
  command_failed: 'The process started but failed; inspect its ordinary execution receipt.',
};

function probe(executable, args, options = {}) {
  const spawn = options.spawn || require('node:child_process').spawnSync;
  const started = Date.now();
  let child;
  try {
    child = spawn(executable, args, {
      cwd: options.cwd,
      env: options.env || process.env,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
      shell: false,
      windowsHide: true,
      timeout: options.timeoutMs || 2000,
      maxBuffer: 16384,
    });
  } catch (error) {
    child = { status: null, error };
  }
  const status = processDiagnosis(child);
  const version =
    status === 'ready'
      ? `${child.stdout || ''}\n${child.stderr || ''}`.match(
          /\b\d+\.\d+\.\d+(?:\.\d+)?(?:-[a-z0-9.]+)?\b/i
        )?.[0] || null
      : null;
  return {
    executable,
    status,
    version,
    exit_code: typeof child.status === 'number' ? child.status : null,
    error_code: child.error?.code || null,
    duration_ms: Date.now() - started,
    next_step: NEXT_STEPS[status],
  };
}

module.exports = { processDiagnosis, NEXT_STEPS, probe };
