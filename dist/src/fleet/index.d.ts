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
 * - Multi-agent browser crawl coordination
 *
 * @module fleet
 */
export * from './agent-registry';
export * from './fleet-manager';
export * from './governance';
export * from './swarm';
export * from './task-dispatcher';
export * from './crawl-message-bus';
export * from './crawl-frontier';
export * from './crawl-coordinator';
export * from './crawl-runner';
export * from './types';
export { AuditEntry, AuditStatus, GrowthMilestone, PadNote, PadSketch, PadTool, PollyPad, PollyPadManager, TIER_THRESHOLDS, getNextTier, getXPForNextTier, } from './polly-pad';
//# sourceMappingURL=index.d.ts.map