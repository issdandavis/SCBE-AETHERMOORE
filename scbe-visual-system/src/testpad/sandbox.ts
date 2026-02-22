/**
 * SCBE Test Pad - Sandboxed npm Execution Engine
 *
 * Runs npm commands in isolated temp directories with:
 * - Time-limited execution (configurable timeout)
 * - Directory isolation (fresh tmpdir per run)
 * - Output capture (stdout + stderr)
 * - Automatic cleanup
 * - Audit trail for governance logging
 *
 * USPTO #63/961,403
 */

import { checkContainment, type ContainmentResult } from './containment';

// ---------- Types ----------

export type TestCommand = 'install' | 'test' | 'run' | 'build' | 'lint';

export interface SandboxConfig {
  timeout: number;         // ms, default 60000
  maxOutputSize: number;   // chars, default 100000
  cleanupOnExit: boolean;  // default true
  allowNetwork: boolean;   // default false for 'run', true for 'install'
}

export interface SandboxResult {
  success: boolean;
  exitCode: number;
  stdout: string;
  stderr: string;
  duration: number;
  containment: ContainmentResult;
  auditTrail: string[];
  sandboxDir: string;
}

export interface TestPadSession {
  id: string;
  startedAt: number;
  packageJson: string;
  code: string;
  results: SandboxResult[];
  auditLog: string[];
}

// ---------- Constants ----------

const DEFAULT_CONFIG: SandboxConfig = {
  timeout: 60000,
  maxOutputSize: 100000,
  cleanupOnExit: true,
  allowNetwork: false,
};

const DEFAULT_PACKAGE_JSON = JSON.stringify({
  name: 'scbe-test-pad-sandbox',
  version: '1.0.0',
  private: true,
  scripts: {
    test: 'echo "No test specified"',
    start: 'node index.js',
  },
}, null, 2);

// ---------- Session Management ----------

let sessions: Map<string, TestPadSession> = new Map();

function generateSessionId(): string {
  return `tps-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Create a new Test Pad session.
 */
export function createSession(packageJson?: string, code?: string): TestPadSession {
  const session: TestPadSession = {
    id: generateSessionId(),
    startedAt: Date.now(),
    packageJson: packageJson || DEFAULT_PACKAGE_JSON,
    code: code || '',
    results: [],
    auditLog: [`[${new Date().toISOString()}] Session created`],
  };

  sessions.set(session.id, session);
  return session;
}

/**
 * Get session by ID.
 */
export function getSession(id: string): TestPadSession | undefined {
  return sessions.get(id);
}

/**
 * Close and clean up a session.
 */
export function closeSession(id: string): void {
  const session = sessions.get(id);
  if (session) {
    session.auditLog.push(`[${new Date().toISOString()}] Session closed`);
    sessions.delete(id);
  }
}

/**
 * Run a command in the sandbox.
 * This function is designed to be called from the Electron main process
 * via IPC. The actual child_process execution happens in main.cjs.
 *
 * In the renderer process, this returns the containment check result
 * so the UI can show governance status before execution begins.
 */
export function preflightCheck(
  code: string,
  command: TestCommand,
  config: Partial<SandboxConfig> = {}
): { containment: ContainmentResult; config: SandboxConfig } {
  const fullConfig = { ...DEFAULT_CONFIG, ...config };

  // Map TestCommand to containment intent
  const intent = command === 'install' ? 'install' as const
    : command === 'test' ? 'test' as const
    : 'run' as const;

  // Allow network for install
  if (command === 'install') {
    fullConfig.allowNetwork = true;
  }

  const containment = checkContainment(code, intent);

  return { containment, config: fullConfig };
}

/**
 * Format a sandbox result for display.
 */
export function formatResult(result: SandboxResult): string {
  const lines: string[] = [
    `--- SCBE Test Pad Result ---`,
    `Status: ${result.success ? 'PASS' : 'FAIL'} (exit code: ${result.exitCode})`,
    `Duration: ${result.duration}ms`,
    `Containment: ${result.containment.allowed ? 'ALLOWED' : 'DENIED'}`,
    `Hyperbolic Distance: ${result.containment.distance.toFixed(4)}`,
    `Risk Score: ${result.containment.riskScore.toFixed(4)}`,
    '',
  ];

  if (result.stdout.trim()) {
    lines.push('--- stdout ---', result.stdout.trim());
  }

  if (result.stderr.trim()) {
    lines.push('', '--- stderr ---', result.stderr.trim());
  }

  if (result.containment.violations.length > 0) {
    lines.push('', '--- Governance Violations ---');
    for (const v of result.containment.violations) {
      lines.push(`  ! ${v}`);
    }
  }

  return lines.join('\n');
}

// ---------- Exports ----------

export { DEFAULT_PACKAGE_JSON, DEFAULT_CONFIG };
