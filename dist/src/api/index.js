"use strict";
/**
 * SCBE API Module
 * ===============
 * REST API endpoints for SCBE-AETHERMOORE
 *
 * Endpoints:
 * - POST /api/authorize   - 14-layer authorization
 * - GET  /api/realms      - Realm centers
 * - POST /api/envelope    - Create RWP envelope
 * - POST /api/verify      - Verify RWP envelope
 * - GET  /api/status      - System health
 * - POST /api/fleet/task  - Fleet task submission
 *
 * @module api
 */
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __exportStar = (this && this.__exportStar) || function(m, exports) {
    for (var p in m) if (p !== "default" && !Object.prototype.hasOwnProperty.call(exports, p)) __createBinding(exports, m, p);
};
Object.defineProperty(exports, "__esModule", { value: true });
__exportStar(require("./routes.js"), exports);
//# sourceMappingURL=index.js.map