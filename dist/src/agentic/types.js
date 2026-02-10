"use strict";
/**
 * Agentic Coder Platform Types
 *
 * @module agentic/types
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.COMPLEXITY_GROUP_SIZE = exports.TASK_AGENT_RECOMMENDATIONS = exports.DEFAULT_PLATFORM_CONFIG = exports.ROLE_TIER_MAP = exports.ROLE_TONGUE_MAP = void 0;
/**
 * Agent role to Sacred Tongue mapping
 */
exports.ROLE_TONGUE_MAP = {
    architect: 'KO',
    coder: 'AV',
    reviewer: 'RU',
    tester: 'CA',
    security: 'UM',
    deployer: 'DR',
};
/**
 * Agent role to governance tier mapping
 */
exports.ROLE_TIER_MAP = {
    architect: 'KO',
    coder: 'AV',
    reviewer: 'RU',
    tester: 'CA',
    security: 'UM',
    deployer: 'DR',
};
/**
 * Default platform configuration
 */
exports.DEFAULT_PLATFORM_CONFIG = {
    maxAgentsPerGroup: 3,
    maxConcurrentTasks: 5,
    defaultProvider: 'openai',
    requireConsensus: true,
    minConfidence: 0.7,
};
/**
 * Task type to recommended agents mapping
 */
exports.TASK_AGENT_RECOMMENDATIONS = {
    design: ['architect'],
    implement: ['coder', 'architect'],
    review: ['reviewer', 'security'],
    test: ['tester', 'coder'],
    security_audit: ['security', 'reviewer'],
    deploy: ['deployer', 'security'],
    refactor: ['coder', 'reviewer'],
    debug: ['coder', 'tester'],
    document: ['architect', 'coder'],
    optimize: ['coder', 'reviewer', 'tester'],
};
/**
 * Complexity to group size mapping
 */
exports.COMPLEXITY_GROUP_SIZE = {
    simple: 'solo',
    moderate: 'pair',
    complex: 'trio',
};
//# sourceMappingURL=types.js.map