"use strict";
/**
 * Agentic Coder Platform
 *
 * A collaborative AI coding platform with 6 built-in specialized agents
 * that can work together in groups of 1-3 on coding tasks.
 *
 * Built-in Agents (Sacred Tongue aligned):
 * 1. Architect (KO) - System design and architecture
 * 2. Coder (AV) - Code generation and implementation
 * 3. Reviewer (RU) - Code review and quality assurance
 * 4. Tester (CA) - Test generation and execution
 * 5. Security (UM) - Security analysis and hardening
 * 6. Deployer (DR) - Deployment and DevOps
 *
 * @module agentic
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
__exportStar(require("./agents"), exports);
__exportStar(require("./collaboration"), exports);
__exportStar(require("./platform"), exports);
__exportStar(require("./task-group"), exports);
__exportStar(require("./types"), exports);
__exportStar(require("./distributed-workflow"), exports);
//# sourceMappingURL=index.js.map