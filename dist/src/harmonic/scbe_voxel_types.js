"use strict";
/**
 * @file scbe_voxel_types.ts
 * @module harmonic/scbe_voxel_types
 * @layer Layer 1, Layer 12, Layer 13, Layer 14
 * @component Voxel Record Schema
 * @version 3.2.4
 *
 * Canonical payload envelope stored at a voxel address [X,Y,Z,V,P,S] per tongue.
 * Fits QR Cubes + Sacred Eggs + Polly Pads + Byzantine quorum.
 *
 * Addressing: cubeId = sha256(canonical({lang, voxel, epoch, padMode}))
 * Content:    payloadDigest = sha256(payloadCiphertextBytes)
 * Quorum:     ≥4/6 votes on same (cubeId, payloadDigest) to commit
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TONGUE_ROLES = exports.PAD_MODE_TONGUE = exports.PAD_MODES = exports.LANGS = void 0;
/** All valid tongue codes */
exports.LANGS = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR'];
/** All valid pad modes */
exports.PAD_MODES = [
    'ENGINEERING',
    'NAVIGATION',
    'SYSTEMS',
    'SCIENCE',
    'COMMS',
    'MISSION',
];
/** Pad mode to tongue mapping */
exports.PAD_MODE_TONGUE = {
    ENGINEERING: 'CA',
    NAVIGATION: 'AV',
    SYSTEMS: 'DR',
    SCIENCE: 'UM',
    COMMS: 'KO',
    MISSION: 'RU',
};
/** Tongue semantic impedance roles */
exports.TONGUE_ROLES = {
    KO: 'flow_orientation',
    AV: 'boundary_condition',
    RU: 'constraint_field',
    CA: 'active_operator',
    DR: 'structural_tensor',
    UM: 'entropic_sink',
};
//# sourceMappingURL=scbe_voxel_types.js.map