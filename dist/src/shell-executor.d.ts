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
import { type Pipeline14Result } from './harmonic/pipeline14.js';
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
export declare const DEFAULT_CONFIG: ShellExecutorConfig;
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
export declare function extractCommandFeatures(cmd: ShellCommand): number[];
/**
 * Check if command is in the whitelist.
 */
export declare function isWhitelisted(command: string, whitelist: string[]): boolean;
/**
 * Check if any argument matches a blocked pattern.
 * Returns the first matched pattern or null.
 */
export declare function matchesBlockedPattern(args: string[], blockedPatterns: string[]): string | null;
/**
 * Validate working directory is within allowed paths.
 */
export declare function isPathAllowed(cwd: string | undefined, allowedPaths: string[]): boolean;
/**
 * Sanitize environment variables: strip blocked vars, validate values.
 */
export declare function sanitizeEnv(env: Record<string, string> | undefined, blockedEnvVars: string[]): Record<string, string>;
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
export declare class SCBEShellExecutor {
    private config;
    private auditLog;
    constructor(config?: Partial<ShellExecutorConfig>);
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
    validate(cmd: ShellCommand): ValidationResult;
    /**
     * Execute a shell command with SCBE validation and sandboxing.
     *
     * @param cmd - Command specification
     * @returns Execution result (blocked commands have executed=false)
     */
    execute(cmd: ShellCommand): Promise<ExecutionResult>;
    /**
     * Spawn a child process using execFile (no shell interpolation).
     */
    private spawnCommand;
    /**
     * Record an audit event with hash chaining.
     */
    private recordAudit;
    /**
     * Verify audit chain integrity.
     * Returns true if all hashes chain correctly.
     */
    verifyAuditChain(): boolean;
    /**
     * Get audit events, optionally filtered.
     */
    getAuditLog(filter?: {
        decision?: ShellDecision;
        actorId?: string;
        since?: number;
    }): ShellAuditEvent[];
    /**
     * Get audit event count.
     */
    getAuditCount(): number;
    /**
     * Get current whitelist.
     */
    getWhitelist(): string[];
    /**
     * Get configuration (read-only copy).
     */
    getConfig(): ShellExecutorConfig;
}
/**
 * Create a shell executor with custom configuration.
 */
export declare function createShellExecutor(config?: Partial<ShellExecutorConfig>): SCBEShellExecutor;
/**
 * Default shell executor instance.
 */
export declare const defaultShellExecutor: SCBEShellExecutor;
//# sourceMappingURL=shell-executor.d.ts.map