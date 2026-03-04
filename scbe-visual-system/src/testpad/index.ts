/**
 * SCBE Test Pad - Module Exports
 * USPTO #63/961,403
 */

export { checkContainment, analyzeCodeVector, hyperbolicDistance, harmonicWallScaling, breathingTransform, scanForViolations } from './containment';
export type { ContainmentResult, CodeVector } from './containment';

export { createSession, getSession, closeSession, preflightCheck, formatResult, DEFAULT_PACKAGE_JSON, DEFAULT_CONFIG } from './sandbox';
export type { TestCommand, SandboxConfig, SandboxResult, TestPadSession } from './sandbox';
