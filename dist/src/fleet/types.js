"use strict";
/**
 * Fleet Management Type Definitions
 *
 * @module fleet/types
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.DIMENSIONAL_THRESHOLDS = exports.PRIORITY_WEIGHTS = exports.GOVERNANCE_TIERS = void 0;
exports.getDimensionalState = getDimensionalState;
/**
 * Governance tier requirements
 */
exports.GOVERNANCE_TIERS = {
    KO: { minTrustScore: 0.1, requiredTongues: 1, description: 'Read-only operations' },
    AV: { minTrustScore: 0.3, requiredTongues: 2, description: 'Write operations' },
    RU: { minTrustScore: 0.5, requiredTongues: 3, description: 'Execute operations' },
    CA: { minTrustScore: 0.7, requiredTongues: 4, description: 'Deploy operations' },
    UM: { minTrustScore: 0.85, requiredTongues: 5, description: 'Admin operations' },
    DR: { minTrustScore: 0.95, requiredTongues: 6, description: 'Critical/destructive operations' },
};
/**
 * Priority weights for task scheduling
 */
exports.PRIORITY_WEIGHTS = {
    critical: 4,
    high: 3,
    medium: 2,
    low: 1,
};
/**
 * Dimensional state thresholds
 */
exports.DIMENSIONAL_THRESHOLDS = {
    POLLY: 0.8, // nu >= 0.8 = Full participation
    QUASI: 0.5, // 0.5 <= nu < 0.8 = Partial participation
    DEMI: 0.1, // 0.1 <= nu < 0.5 = Minimal participation
    COLLAPSED: 0, // nu < 0.1 = Offline/archived
};
/**
 * Get dimensional state from nu value
 */
function getDimensionalState(nu) {
    if (nu >= exports.DIMENSIONAL_THRESHOLDS.POLLY)
        return 'POLLY';
    if (nu >= exports.DIMENSIONAL_THRESHOLDS.QUASI)
        return 'QUASI';
    if (nu >= exports.DIMENSIONAL_THRESHOLDS.DEMI)
        return 'DEMI';
    return 'COLLAPSED';
}
//# sourceMappingURL=types.js.map