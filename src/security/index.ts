/**
 * SCBE Security Module
 *
 * Unified 14-layer security pipeline with:
 * - Input validation & sanitization
 * - 14-layer hyperbolic risk assessment
 * - 4-tier governance decisions (ALLOW / QUARANTINE / ESCALATE / DENY)
 * - SHA-256 hash-chained audit trail
 * - HMAC integrity tagging
 * - Replay protection
 *
 * @module security
 */

// ── Security Pipeline ────────────────────────────────────────────
export {
  SecurityPipeline,
  createSecurityPipeline,
  DEFAULT_SECURITY_CONFIG,
  type SecurityPipelineConfig,
  type SecurityRequest,
  type SecurityResult,
} from './securityPipeline.js';

// ── Input Validation ─────────────────────────────────────────────
export {
  validateInput,
  validateSacredTongueDimension,
  normalizeInputLength,
  DEFAULT_VALIDATOR_CONFIG,
  type ValidationResult,
  type ValidatorConfig,
} from './inputValidator.js';

// ── Audit Trail ──────────────────────────────────────────────────
export {
  SecurityAuditTrail,
  type GovernanceDecision,
  type AuditEntry,
  type AuditStats,
} from './auditTrail.js';
