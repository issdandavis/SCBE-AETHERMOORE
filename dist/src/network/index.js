"use strict";
/**
 * Network Module - Space Combat Communications
 *
 * Implements secure, redundant routing for interplanetary communications
 * with quantum-resistant encryption and combat-grade reliability.
 *
 * Components:
 * - SpaceTorRouter: Onion routing with trust scoring and load balancing
 * - HybridSpaceCrypto: Hybrid classical/quantum-resistant encryption
 * - CombatNetwork: Multipath routing with path health monitoring
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.CombatNetwork = exports.HybridSpaceCrypto = exports.SpaceTorRouter = void 0;
var space_tor_router_js_1 = require("./space-tor-router.js");
Object.defineProperty(exports, "SpaceTorRouter", { enumerable: true, get: function () { return space_tor_router_js_1.SpaceTorRouter; } });
var hybrid_crypto_js_1 = require("./hybrid-crypto.js");
Object.defineProperty(exports, "HybridSpaceCrypto", { enumerable: true, get: function () { return hybrid_crypto_js_1.HybridSpaceCrypto; } });
var combat_network_js_1 = require("./combat-network.js");
Object.defineProperty(exports, "CombatNetwork", { enumerable: true, get: function () { return combat_network_js_1.CombatNetwork; } });
//# sourceMappingURL=index.js.map