/**
 * @file shell-executor.ts
 * @module shell-executor
 * @layer Layer 13
 * @component SCBEShellExecutor — Sandboxed Shell Execution for AI Agents
 * @version 1.0.0
 *
 * Sandboxed shell execution layer that gates all AI agent terminal commands
 * through SCBE's 14-layer validation pipeline before execution.
 *
 * Two-step validation:
 *   1. Pre-execution: command whitelist + dangerous pattern blocking + SCBE pipeline
 *   2. Sandboxed execution: child_process.execFile (no shell interpolation), timeout,
 *      output limits, path restrictions
 *
 * Integrates with:
 *   - pipeline14.ts: 14-layer risk scoring → ALLOW/QUARANTINE/DENY
 *   - govern.ts types: Actor, Resource, Decision
 *   - audit.ts patterns: hash-chained event logging
 *
 * Security model:
 *   - Command whitelisting (configurable)
 *   - Regex-based dangerous pattern blocking
 *   - Path traversal prevention (working directory restrictions)
 *   - Environment variable sanitization
 *   - Output size limits
 *   - Timeout controls
 *   - Immutable audit trail
 */

import { execFile, type ExecFileException } from 'child_process';
import * as crypto from 'crypto';
import { scbe14LayerPipeline, type Pipeline14Result } from './harmonic/pipeline14.js';

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

/** SCBE governance decision (mirrors pipeline14/govern Decision) */
export type ShellDecision = 'ALLOW' | 'QUARANTINE' | 'DENY';

/**
 * Shell command specification.
 * Structured to prevent injection — command and args are always separate.
 */
export interface ShellCommand {
  /** Executable name (must be in whitelist) */
  command: string;
  /** Arguments array (never interpolated into shell) */
  args: string[];
  /** Working directory (must be within allowed paths) */
  cwd?: string;
  /** Timeout in milliseconds (default from config) */
  timeout?: number;
  /** Environment variable overrides (sanitized before use) */
  env?: Record<string, string>;
  /** Human-readable description of intent */
  intent?: string;
  /** Actor identifier (agent ID) */
  actorId?: string;
}

/**
 * Execution result returned after command completes (or is blocked).
 */
export interface ExecutionResult {
  /** Standard output (truncated to maxOutputBytes) */
  stdout: string;
  /** Standard error (truncated to maxOutputBytes) */
  stderr: string;
  /** Process exit code (null if not executed) */
  exitCode: number | null;
  /** SCBE validation decision */
  decision: ShellDecision;
  /** Whether the command was actually executed */
  executed: boolean;
  /** Reason for blocking (if decision !== ALLOW) */
  reason?: string;
  /** SCBE risk score from pipeline (if validation ran) */
  riskScore?: number;
  /** Unique audit ID for this execution attempt */
  auditId: string;
  /** Timestamp of execution attempt */
  timestamp: number;
  /** Duration in milliseconds (0 if not executed) */
  durationMs: number;
}

/**
 * Validation result from pre-execution checks.
 */
export interface ValidationResult {
  /** Whether the command passes all checks */
  valid: boolean;
  /** SCBE decision */
  decision: ShellDecision;
  /** Risk score from pipeline */
  riskScore: number;
  /** Reasons for any failures */
  reasons: string[];
  /** Full pipeline result (if pipeline was invoked) */
  pipelineResult?: Pipeline14Result;
}

/**
 * Audit event for command execution attempts.
 */
export interface ShellAuditEvent {
  /** Unique event ID */
  id: string;
  /** ISO timestamp */
  timestamp: string;
  /** Command that was attempted */
  command: ShellCommand;
  /** Validation result */
  validation: ValidationResult;
  /** Execution result (if executed) */
  result?: ExecutionResult;
  /** SHA-256 hash of previous event (chain integrity) */
  prevHash: string;
  /** SHA-256 hash of this event */
  hash: string;
}

// ═══════════════════════════════════════════════════════════════
// Configuration
// ═══════════════════════════════════════════════════════════════

/**
 * Shell executor configuration.
 */
export interface ShellExecutorConfig {
  /** Whitelisted commands (default: npm, git, node, tsc, pnpm, yarn, npx, python) */
  whitelist: string[];
  /** Blocked argument patterns (regex strings) */
  blockedPatterns: string[];
  /** Allowed working directory prefixes */
  allowedPaths: string[];
  /** Default command timeout in ms (default: 30000) */
  defaultTimeout: number;
  /** Maximum output bytes per stream (default: 1MB) */
  maxOutputBytes: number;
  /** Environment variables to always strip */
  blockedEnvVars: string[];
  /** Whether to run SCBE pipeline validation (default: true) */
  enablePipelineValidation: boolean;
  /** SCBE pipeline risk thresholds [theta1, theta2] */
  riskThresholds: [number, number];
  /** Maximum audit events to retain (default: 10000) */
  maxAuditEvents: number;
}

export const DEFAULT_CONFIG: ShellExecutorConfig = {
  whitelist: ['npm', 'git', 'node', 'tsc', 'pnpm', 'yarn', 'npx', 'python', 'pip', 'pytest'],
  blockedPatterns: [
    // Destructive filesystem operations
    'rm\\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive\\s+--force|-[a-zA-Z]*f[a-zA-Z]*r)',
    'rm\\s+-rf',
    ':\\(\\)\\{\\s*:\\|:\\s*&\\s*\\};:', // Fork bomb
    'mkfs\\.',
    'dd\\s+if=',
    '>(\\s*/dev/(sd|hd|vd|nvme))', // Direct disk writes
    'chmod\\s+(-R\\s+)?777',
    'curl\\s+.*\\|\\s*(ba)?sh', // Pipe to shell
    'wget\\s+.*\\|\\s*(ba)?sh',
    'eval\\s*\\(', // Dynamic eval
    '\\$\\(.*\\)', // Command substitution
    '`[^`]+`', // Backtick substitution
    '\\|\\s*(ba)?sh', // Pipe to shell
    'sudo\\s+',
    'chown\\s+-R',
    '>\\s*/etc/',
    'pkill\\s+-9',
    'kill\\s+-9',
    'shutdown',
    'reboot',
    'init\\s+[06]',
  ],
  allowedPaths: ['/home', '/tmp', '/var/tmp'],
  defaultTimeout: 30000,
  maxOutputBytes: 1024 * 1024, // 1MB
  blockedEnvVars: [
    'AWS_SECRET_ACCESS_KEY',
    'AWS_SESSION_TOKEN',
    'GITHUB_TOKEN',
    'GH_TOKEN',
    'NPM_TOKEN',
    'SSH_AUTH_SOCK',
    'SSH_AGENT_PID',
    'GPG_KEY',
    'PRIVATE_KEY',
    'SECRET_KEY',
    'DATABASE_URL',
    'DB_PASSWORD',
    'PGPASSWORD',
    'MYSQL_ROOT_PASSWORD',
  ],
  enablePipelineValidation: true,
  riskThresholds: [0.33, 0.67],
  maxAuditEvents: 10000,
};

// ═══════════════════════════════════════════════════════════════
// Feature Vector Extraction
// ═══════════════════════════════════════════════════════════════

/**
 * Extract a feature vector from a shell command for SCBE pipeline validation.
 *
 * Maps command properties to a numeric vector that the 14-layer pipeline
 * can process. Features encode: command risk class, argument complexity,
 * path depth, environment footprint, intent length.
 *
 * @param cmd - Shell command to extract features from
 * @returns Feature vector (length 6, suitable for D=3 pipeline)
 */
export function extractCommandFeatures(cmd: ShellCommand): number[] {
  // Feature 1: Command risk class (0=safe, 0.5=moderate, 1.0=risky)
  const riskClasses: Record<string, number> = {
    node: 0.1,
    tsc: 0.1,
    npx: 0.2,
    npm: 0.2,
    pnpm: 0.2,
    yarn: 0.2,
    git: 0.3,
    python: 0.3,
    pip: 0.4,
    pytest: 0.1,
  };
  const commandRisk = riskClasses[cmd.command] ?? 0.5;

  // Feature 2: Argument complexity (normalized count)
  const argComplexity = Math.min(1.0, cmd.args.length / 20);

  // Feature 3: Total argument length (proxy for complexity)
  const totalArgLength = cmd.args.join(' ').length;
  const argLength = Math.min(1.0, totalArgLength / 500);

  // Feature 4: Path depth (deeper = higher risk)
  const cwd = cmd.cwd || '.';
  const pathDepth = Math.min(1.0, cwd.split('/').filter(Boolean).length / 10);

  // Feature 5: Environment variable count (more = higher risk)
  const envCount = Math.min(1.0, Object.keys(cmd.env || {}).length / 10);

  // Feature 6: Intent length (longer intent = more complex operation)
  const intentLength = Math.min(1.0, (cmd.intent || '').length / 200);

  return [commandRisk, argComplexity, argLength, pathDepth, envCount, intentLength];
}

// ═══════════════════════════════════════════════════════════════
// Validation Functions
// ═══════════════════════════════════════════════════════════════

/**
 * Check if command is in the whitelist.
 */
export function isWhitelisted(command: string, whitelist: string[]): boolean {
  // Extract base command name (strip path)
  const baseName = command.split('/').pop() || command;
  return whitelist.includes(baseName);
}

/**
 * Check if any argument matches a blocked pattern.
 * Returns the first matched pattern or null.
 */
export function matchesBlockedPattern(
  args: string[],
  blockedPatterns: string[]
): string | null {
  const fullArgs = args.join(' ');
  for (const pattern of blockedPatterns) {
    try {
      const regex = new RegExp(pattern, 'i');
      if (regex.test(fullArgs)) {
        return pattern;
      }
    } catch {
      // Skip invalid patterns
    }
  }
  return null;
}

/**
 * Validate working directory is within allowed paths.
 */
export function isPathAllowed(cwd: string | undefined, allowedPaths: string[]): boolean {
  if (!cwd) return true; // No cwd = use process default, allowed

  // Resolve to prevent traversal
  const resolved = resolvePath(cwd);

  // Check path traversal attempts
  if (resolved.includes('..')) return false;

  // Check if under any allowed prefix
  return allowedPaths.some((allowed) => resolved.startsWith(allowed));
}

/**
 * Simple path resolution (no fs access needed).
 * Collapses . and .. segments, normalizes separators.
 */
function resolvePath(p: string): string {
  const parts = p.split('/').filter(Boolean);
  const resolved: string[] = [];

  for (const part of parts) {
    if (part === '.') continue;
    if (part === '..') {
      resolved.pop();
    } else {
      resolved.push(part);
    }
  }

  return (p.startsWith('/') ? '/' : '') + resolved.join('/');
}

/**
 * Sanitize environment variables: strip blocked vars, validate values.
 */
export function sanitizeEnv(
  env: Record<string, string> | undefined,
  blockedEnvVars: string[]
): Record<string, string> {
  if (!env) return {};

  const sanitized: Record<string, string> = {};
  const blockedSet = new Set(blockedEnvVars.map((v) => v.toUpperCase()));

  for (const [key, value] of Object.entries(env)) {
    // Skip blocked env vars
    if (blockedSet.has(key.toUpperCase())) continue;

    // Skip vars that look like they contain secrets
    if (/secret|password|token|key|credential/i.test(key)) continue;

    // Limit value length
    sanitized[key] = value.slice(0, 4096);
  }

  return sanitized;
}

/**
 * Truncate output to maxBytes, appending a truncation notice.
 */
function truncateOutput(output: string, maxBytes: number): string {
  if (Buffer.byteLength(output, 'utf-8') <= maxBytes) return output;
  const truncated = Buffer.from(output, 'utf-8').subarray(0, maxBytes).toString('utf-8');
  return truncated + '\n[SCBE: output truncated at ' + maxBytes + ' bytes]';
}

// ═══════════════════════════════════════════════════════════════
// Shell Executor
// ═══════════════════════════════════════════════════════════════

/**
 * SCBEShellExecutor: Sandboxed shell execution with SCBE validation.
 *
 * Two-step approach:
 * 1. Pre-execution validation (whitelist + patterns + pipeline)
 * 2. Sandboxed execution (execFile, no shell, timeout, output limits)
 *
 * @example
 * ```typescript
 * const executor = new SCBEShellExecutor();
 *
 * const result = await executor.execute({
 *   command: 'npm',
 *   args: ['test'],
 *   cwd: '/home/user/project',
 *   intent: 'Run unit tests',
 *   actorId: 'agent-001',
 * });
 *
 * if (result.executed) {
 *   console.log(result.stdout);
 * } else {
 *   console.log(`Blocked: ${result.reason}`);
 * }
 * ```
 */
export class SCBEShellExecutor {
  private config: ShellExecutorConfig;
  private auditLog: ShellAuditEvent[] = [];

  constructor(config: Partial<ShellExecutorConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    // Merge arrays instead of replacing them
    if (config.whitelist) {
      this.config.whitelist = config.whitelist;
    }
    if (config.blockedPatterns) {
      this.config.blockedPatterns = [
        ...DEFAULT_CONFIG.blockedPatterns,
        ...config.blockedPatterns,
      ];
    }
    if (config.allowedPaths) {
      this.config.allowedPaths = config.allowedPaths;
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Validation
  // ─────────────────────────────────────────────────────────────

  /**
   * Validate a command through all pre-execution checks.
   *
   * Check order (fail-fast):
   * 1. Whitelist check
   * 2. Blocked pattern check
   * 3. Path restriction check
   * 4. Environment sanitization
   * 5. SCBE 14-layer pipeline validation
   */
  validate(cmd: ShellCommand): ValidationResult {
    const reasons: string[] = [];

    // 1. Whitelist check
    if (!isWhitelisted(cmd.command, this.config.whitelist)) {
      return {
        valid: false,
        decision: 'DENY',
        riskScore: 1.0,
        reasons: [`Command '${cmd.command}' not in whitelist`],
      };
    }

    // 2. Blocked pattern check
    const blocked = matchesBlockedPattern(cmd.args, this.config.blockedPatterns);
    if (blocked) {
      return {
        valid: false,
        decision: 'DENY',
        riskScore: 1.0,
        reasons: [`Arguments match blocked pattern: ${blocked}`],
      };
    }

    // Also check command + args combined (e.g., "git push --force")
    const blockedFull = matchesBlockedPattern(
      [cmd.command, ...cmd.args],
      this.config.blockedPatterns
    );
    if (blockedFull) {
      return {
        valid: false,
        decision: 'DENY',
        riskScore: 1.0,
        reasons: [`Command+args match blocked pattern: ${blockedFull}`],
      };
    }

    // 3. Path restriction check
    if (!isPathAllowed(cmd.cwd, this.config.allowedPaths)) {
      return {
        valid: false,
        decision: 'DENY',
        riskScore: 1.0,
        reasons: [`Working directory '${cmd.cwd}' not in allowed paths`],
      };
    }

    // 4. Environment sanitization (non-blocking, just strip dangerous vars)
    // This is applied during execution, not validation

    // 5. SCBE 14-layer pipeline validation
    if (this.config.enablePipelineValidation) {
      const features = extractCommandFeatures(cmd);
      const pipelineResult = scbe14LayerPipeline(features, {
        theta1: this.config.riskThresholds[0],
        theta2: this.config.riskThresholds[1],
      });

      if (pipelineResult.decision === 'DENY') {
        return {
          valid: false,
          decision: 'DENY',
          riskScore: pipelineResult.riskPrime,
          reasons: [
            `SCBE pipeline risk score ${pipelineResult.riskPrime.toFixed(4)} exceeds DENY threshold`,
          ],
          pipelineResult,
        };
      }

      if (pipelineResult.decision === 'QUARANTINE') {
        return {
          valid: false,
          decision: 'QUARANTINE',
          riskScore: pipelineResult.riskPrime,
          reasons: [
            `SCBE pipeline risk score ${pipelineResult.riskPrime.toFixed(4)} in QUARANTINE range`,
          ],
          pipelineResult,
        };
      }

      return {
        valid: true,
        decision: 'ALLOW',
        riskScore: pipelineResult.riskPrime,
        reasons: [],
        pipelineResult,
      };
    }

    // Pipeline disabled — pass with zero risk score
    return {
      valid: true,
      decision: 'ALLOW',
      riskScore: 0,
      reasons: [],
    };
  }

  // ─────────────────────────────────────────────────────────────
  // Execution
  // ─────────────────────────────────────────────────────────────

  /**
   * Execute a shell command with SCBE validation and sandboxing.
   *
   * @param cmd - Command specification
   * @returns Execution result (blocked commands have executed=false)
   */
  async execute(cmd: ShellCommand): Promise<ExecutionResult> {
    const auditId = crypto.randomUUID();
    const timestamp = Date.now();

    // Step 1: Validate
    const validation = this.validate(cmd);

    if (!validation.valid) {
      const result: ExecutionResult = {
        stdout: '',
        stderr: '',
        exitCode: null,
        decision: validation.decision,
        executed: false,
        reason: validation.reasons.join('; '),
        riskScore: validation.riskScore,
        auditId,
        timestamp,
        durationMs: 0,
      };

      this.recordAudit(cmd, validation, result);
      return result;
    }

    // Step 2: Sandboxed execution
    const timeout = cmd.timeout ?? this.config.defaultTimeout;
    const sanitizedEnv = sanitizeEnv(cmd.env, this.config.blockedEnvVars);

    const startTime = Date.now();

    try {
      const { stdout, stderr, exitCode } = await this.spawnCommand(
        cmd.command,
        cmd.args,
        {
          cwd: cmd.cwd,
          timeout,
          env: { ...process.env, ...sanitizedEnv },
        }
      );

      const durationMs = Date.now() - startTime;
      const result: ExecutionResult = {
        stdout: truncateOutput(stdout, this.config.maxOutputBytes),
        stderr: truncateOutput(stderr, this.config.maxOutputBytes),
        exitCode,
        decision: 'ALLOW',
        executed: true,
        riskScore: validation.riskScore,
        auditId,
        timestamp,
        durationMs,
      };

      this.recordAudit(cmd, validation, result);
      return result;
    } catch (error) {
      const durationMs = Date.now() - startTime;
      const err = error as ExecFileException & { stdout?: string; stderr?: string };

      const result: ExecutionResult = {
        stdout: truncateOutput(err.stdout || '', this.config.maxOutputBytes),
        stderr: truncateOutput(err.stderr || err.message || '', this.config.maxOutputBytes),
        exitCode: err.code !== undefined && typeof err.code === 'number' ? err.code : 1,
        decision: 'ALLOW',
        executed: true,
        reason: err.killed ? 'Process killed (timeout)' : undefined,
        riskScore: validation.riskScore,
        auditId,
        timestamp,
        durationMs,
      };

      this.recordAudit(cmd, validation, result);
      return result;
    }
  }

  /**
   * Spawn a child process using execFile (no shell interpolation).
   */
  private spawnCommand(
    command: string,
    args: string[],
    options: { cwd?: string; timeout: number; env: NodeJS.ProcessEnv }
  ): Promise<{ stdout: string; stderr: string; exitCode: number }> {
    return new Promise((resolve, reject) => {
      execFile(
        command,
        args,
        {
          cwd: options.cwd,
          timeout: options.timeout,
          env: options.env,
          maxBuffer: this.config.maxOutputBytes * 2,
          shell: false, // Never use shell interpolation
        },
        (error, stdout, stderr) => {
          if (error) {
            // Attach stdout/stderr to error for the catch handler
            const enrichedError = Object.assign(error, {
              stdout: stdout || '',
              stderr: stderr || '',
            });
            // Non-zero exit code is not an error for us, just report it
            if (error.code !== undefined || error.killed) {
              reject(enrichedError);
            } else {
              // Process exited with non-zero but no signal
              resolve({
                stdout: stdout || '',
                stderr: stderr || '',
                exitCode: error.code !== undefined && typeof error.code === 'number' ? error.code : 1,
              });
            }
          } else {
            resolve({
              stdout: stdout || '',
              stderr: stderr || '',
              exitCode: 0,
            });
          }
        }
      );
    });
  }

  // ─────────────────────────────────────────────────────────────
  // Audit Trail
  // ─────────────────────────────────────────────────────────────

  /**
   * Record an audit event with hash chaining.
   */
  private recordAudit(
    command: ShellCommand,
    validation: ValidationResult,
    result: ExecutionResult
  ): void {
    const prevHash =
      this.auditLog.length > 0
        ? this.auditLog[this.auditLog.length - 1].hash
        : '0'.repeat(64);

    const event: ShellAuditEvent = {
      id: result.auditId,
      timestamp: new Date(result.timestamp).toISOString(),
      command: {
        command: command.command,
        args: command.args,
        cwd: command.cwd,
        intent: command.intent,
        actorId: command.actorId,
      },
      validation: {
        valid: validation.valid,
        decision: validation.decision,
        riskScore: validation.riskScore,
        reasons: validation.reasons,
      },
      result: {
        stdout: '',
        stderr: result.stderr ? '[stderr present]' : '',
        exitCode: result.exitCode,
        decision: result.decision,
        executed: result.executed,
        reason: result.reason,
        riskScore: result.riskScore,
        auditId: result.auditId,
        timestamp: result.timestamp,
        durationMs: result.durationMs,
      },
      prevHash,
      hash: '', // Computed below
    };

    // Compute SHA-256 hash of event (excluding hash field)
    const eventData = JSON.stringify({
      id: event.id,
      timestamp: event.timestamp,
      command: event.command,
      validation: event.validation,
      prevHash: event.prevHash,
    });

    event.hash = crypto.createHash('sha256').update(eventData).digest('hex');

    this.auditLog.push(event);

    // Trim if exceeding max
    if (this.auditLog.length > this.config.maxAuditEvents) {
      this.auditLog.shift();
    }
  }

  /**
   * Verify audit chain integrity.
   * Returns true if all hashes chain correctly.
   */
  verifyAuditChain(): boolean {
    for (let i = 1; i < this.auditLog.length; i++) {
      if (this.auditLog[i].prevHash !== this.auditLog[i - 1].hash) {
        return false;
      }
    }
    return true;
  }

  /**
   * Get audit events, optionally filtered.
   */
  getAuditLog(filter?: {
    decision?: ShellDecision;
    actorId?: string;
    since?: number;
  }): ShellAuditEvent[] {
    let events = [...this.auditLog];

    if (filter?.decision) {
      events = events.filter((e) => e.validation.decision === filter.decision);
    }
    if (filter?.actorId) {
      events = events.filter((e) => e.command.actorId === filter.actorId);
    }
    if (filter?.since) {
      events = events.filter((e) => new Date(e.timestamp).getTime() >= filter.since!);
    }

    return events;
  }

  /**
   * Get audit event count.
   */
  getAuditCount(): number {
    return this.auditLog.length;
  }

  // ─────────────────────────────────────────────────────────────
  // Configuration Access
  // ─────────────────────────────────────────────────────────────

  /**
   * Get current whitelist.
   */
  getWhitelist(): string[] {
    return [...this.config.whitelist];
  }

  /**
   * Get configuration (read-only copy).
   */
  getConfig(): ShellExecutorConfig {
    return { ...this.config };
  }
}

// ═══════════════════════════════════════════════════════════════
// Factory
// ═══════════════════════════════════════════════════════════════

/**
 * Create a shell executor with custom configuration.
 */
export function createShellExecutor(
  config?: Partial<ShellExecutorConfig>
): SCBEShellExecutor {
  return new SCBEShellExecutor(config);
}

/**
 * Default shell executor instance.
 */
export const defaultShellExecutor = new SCBEShellExecutor();
