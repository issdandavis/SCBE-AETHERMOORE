"use strict";
/**
 * Spiralverse Protocol SDK - TypeScript Implementation
 *
 * Implements RWP v2.1 with Roundtable multi-signature governance,
 * Six Sacred Tongues domain separation, and 6D vector navigation.
 *
 * @version 2.1.0
 * @author Issac Davis
 * @license MIT
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.SecurityTier = exports.SpiralverseProtocol = exports.SacredTongue = void 0;
exports.getRequiredTongues = getRequiredTongues;
exports.classifyAction = classifyAction;
const crypto_1 = __importDefault(require("crypto"));
// ========== TYPES ==========
/** Six Sacred Tongues as protocol domains */
var SacredTongue;
(function (SacredTongue) {
    SacredTongue["KO"] = "KO";
    SacredTongue["AV"] = "AV";
    SacredTongue["RU"] = "RU";
    SacredTongue["CA"] = "CA";
    SacredTongue["UM"] = "UM";
    SacredTongue["DR"] = "DR";
})(SacredTongue || (exports.SacredTongue = SacredTongue = {}));
// ========== CORE SDK CLASS ==========
class SpiralverseProtocol {
    secrets = new Map();
    constructor(secrets) {
        Object.entries(secrets).forEach(([tongue, secret]) => {
            this.secrets.set(tongue, secret);
        });
    }
    /**
     * Create signed envelope with specified tongues
     * @param origin Primary tongue initiating the action
     * @param requiredTongues Additional tongues for Roundtable governance
     * @param action Action payload
     */
    createEnvelope(origin, requiredTongues, action) {
        const ts = new Date().toISOString();
        const nonce = crypto_1.default.randomBytes(16).toString('hex');
        const seq = Math.floor(Math.random() * 1000000);
        // Construct spelltext with semantic metadata
        const spelltext = `AXIOM<origin>${origin}</origin><seq>${seq}</seq><ts>${ts}</ts>`;
        // Encode payload
        const payload = Buffer.from(JSON.stringify(action)).toString('base64url');
        // Create canonical signing string
        const canonical = this.canonicalString(spelltext, payload, ts, nonce);
        // Generate signatures for origin + required tongues
        const tongues = [origin, ...requiredTongues.filter((t) => t !== origin)];
        const signatures = {};
        tongues.forEach((tongue) => {
            const secret = this.secrets.get(tongue);
            if (!secret)
                throw new Error(`Missing secret for tongue: ${tongue}`);
            signatures[tongue] = this.sign(canonical, secret, tongue);
        });
        return { spelltext, payload, signatures, ts, nonce };
    }
    /**
     * Verify envelope signatures against required tongues
     * @param envelope Message to verify
     * @param requiredTongues Tongues that must have signed
     */
    verifyEnvelope(envelope, requiredTongues) {
        const canonical = this.canonicalString(envelope.spelltext, envelope.payload, envelope.ts, envelope.nonce);
        // Check all required tongues have valid signatures
        for (const tongue of requiredTongues) {
            const sig = envelope.signatures[tongue];
            if (!sig) {
                console.error(`Missing signature for required tongue: ${tongue}`);
                return false;
            }
            const secret = this.secrets.get(tongue);
            if (!secret) {
                console.error(`Missing secret for tongue: ${tongue}`);
                return false;
            }
            const expected = this.sign(canonical, secret, tongue);
            if (sig !== expected) {
                console.error(`Invalid signature for tongue: ${tongue}`);
                return false;
            }
        }
        // Check timestamp freshness (5 minute window)
        const age = Date.now() - new Date(envelope.ts).getTime();
        if (age > 5 * 60 * 1000) {
            console.error('Envelope expired');
            return false;
        }
        return true;
    }
    /**
     * Decode payload from envelope
     */
    decodePayload(envelope) {
        const json = Buffer.from(envelope.payload, 'base64url').toString('utf-8');
        return JSON.parse(json);
    }
    // ========== INTERNAL HELPERS ==========
    canonicalString(spelltext, payload, ts, nonce) {
        return `${spelltext}\n${payload}\n${ts}\n${nonce}`;
    }
    sign(data, secret, tongue) {
        // Domain-separated HMAC
        const domain = `spiralverse:v2.1:${tongue}`;
        const hmac = crypto_1.default.createHmac('sha256', secret);
        hmac.update(domain);
        hmac.update(data);
        return hmac.digest('hex');
    }
}
exports.SpiralverseProtocol = SpiralverseProtocol;
// ========== GOVERNANCE POLICIES ==========
var SecurityTier;
(function (SecurityTier) {
    SecurityTier[SecurityTier["TIER1_LOW"] = 1] = "TIER1_LOW";
    SecurityTier[SecurityTier["TIER2_MEDIUM"] = 2] = "TIER2_MEDIUM";
    SecurityTier[SecurityTier["TIER3_HIGH"] = 3] = "TIER3_HIGH";
    SecurityTier[SecurityTier["TIER4_CRITICAL"] = 4] = "TIER4_CRITICAL";
})(SecurityTier || (exports.SecurityTier = SecurityTier = {}));
/**
 * Get required tongues for a given security tier
 */
function getRequiredTongues(tier) {
    switch (tier) {
        case SecurityTier.TIER1_LOW:
            return [SacredTongue.KO];
        case SecurityTier.TIER2_MEDIUM:
            return [SacredTongue.KO, SacredTongue.RU];
        case SecurityTier.TIER3_HIGH:
            return [SacredTongue.KO, SacredTongue.RU, SacredTongue.UM];
        case SecurityTier.TIER4_CRITICAL:
            return [SacredTongue.KO, SacredTongue.RU, SacredTongue.UM, SacredTongue.DR];
        default:
            throw new Error(`Unknown tier: ${tier}`);
    }
}
/**
 * Classify action by security tier
 */
function classifyAction(action) {
    const criticalActions = ['deploy', 'delete', 'rotate_key', 'grant_access'];
    const highActions = ['modify_state', 'execute_command', 'send_signal'];
    const mediumActions = ['query_state', 'log_event', 'update_metadata'];
    if (criticalActions.includes(action))
        return SecurityTier.TIER4_CRITICAL;
    if (highActions.includes(action))
        return SecurityTier.TIER3_HIGH;
    if (mediumActions.includes(action))
        return SecurityTier.TIER2_MEDIUM;
    return SecurityTier.TIER1_LOW;
}
// ========== EXAMPLE USAGE ==========
/*
const sdk = new SpiralverseProtocol({
  [SacredTongue.KO]: 'secret_ko_key',
  [SacredTongue.RU]: 'secret_ru_key',
  [SacredTongue.UM]: 'secret_um_key',
  [SacredTongue.AV]: 'secret_av_key',
  [SacredTongue.CA]: 'secret_ca_key',
  [SacredTongue.DR]: 'secret_dr_key',
});

const action: ActionPayload = {
  action: 'move_arm',
  params: { x: 10, y: 20, z: 5 },
};

const tier = classifyAction(action.action);
const requiredTongues = getRequiredTongues(tier);

const envelope = sdk.createEnvelope(
  SacredTongue.KO,
  requiredTongues,
  action
);

const isValid = sdk.verifyEnvelope(envelope, requiredTongues);
console.log('Valid:', isValid);

if (isValid) {
  const decoded = sdk.decodePayload(envelope);
  console.log('Action:', decoded);
}
*/
//# sourceMappingURL=spiralverse-sdk.js.map