"use strict";
/**
 * @file voxel-types.ts
 * @module fleet/polly-pads/voxel-types
 * @layer Layer 12, Layer 13
 * @version 1.0.0
 *
 * VoxelRecord schema - canonical payload envelope at 6D voxel address.
 *
 * Each record is content-addressed via deterministic cubeId and sealed
 * with a SacredEggSeal envelope. Squad-scoped commits require Byzantine
 * 4/6 quorum proof.
 *
 * Addressing: [X, Y, Z, V, P, S] per Sacred Tongue dimension.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.langToTongueCode = langToTongueCode;
exports.tongueCodeToLang = tongueCodeToLang;
exports.validateVoxelRecord = validateVoxelRecord;
// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
/** Map uppercase Lang to lowercase TongueCode */
function langToTongueCode(lang) {
    return lang.toLowerCase();
}
/** Map lowercase TongueCode to uppercase Lang */
function tongueCodeToLang(code) {
    return code.toUpperCase();
}
/** Validate a VoxelRecord has required fields for its scope */
function validateVoxelRecord(record) {
    if (record.version !== 1) {
        throw new Error(`Unsupported VoxelRecord version: ${record.version}`);
    }
    if (record.scope === 'unit' && !record.unitId) {
        throw new Error('Unit-scoped VoxelRecord requires unitId');
    }
    if (record.scope === 'squad' && !record.squadId) {
        throw new Error('Squad-scoped VoxelRecord requires squadId');
    }
    if (record.scope === 'squad' && !record.quorum) {
        throw new Error('Squad-scoped VoxelRecord requires quorum proof');
    }
    if (record.voxel.length !== 6) {
        throw new Error(`Voxel must be 6D, got ${record.voxel.length}D`);
    }
}
//# sourceMappingURL=voxel-types.js.map