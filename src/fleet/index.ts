/**
 * SCBE Fleet Management System
 * 
 * Integrates SCBE security (TrustManager, SpectralIdentity) with
 * AI Workflow Architect's agent orchestration for secure AI fleet management.
 * 
 * Features:
 * - Agent registration with spectral identity
 * - Sacred Tongue governance for agent actions
 * - Trust-based task assignment
 * - Fleet-wide security monitoring
 * - Roundtable consensus for critical operations
 * - Polly Pads: Personal agent workspaces with dimensional flux
 * - Swarm coordination with flux ODE dynamics
 * 
 * @module fleet
 */

export * from './agent-registry';
export * from './fleet-manager';
export * from './governance';
export * from './swarm';
export * from './task-dispatcher';

// Export types (canonical source for shared types)
export * from './types';

// Export polly-pad specific items (excluding types already exported from ./types)
export {
  // Polly-pad specific types
  AuditEntry,
  AuditStatus,
  GrowthMilestone,
  // Polly-pad interfaces (canonical source)
  PadNote,
  PadSketch,
  PadTool,
  PollyPad,
  // Polly-pad specific functions and classes
  PollyPadManager,
  TIER_THRESHOLDS,
  getNextTier,
  getXPForNextTier
} from './polly-pad';

