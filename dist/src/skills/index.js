"use strict";
/**
 * @file index.ts
 * @module skills
 * @layer L13 (Decision Layer)
 * @component Skills Module
 * @version 1.0.0
 *
 * Skills are reusable capabilities for automating common tasks.
 * Each skill transforms inputs into actionable outputs.
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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.smartTruncate = exports.parseNotionContent = exports.generateHashtags = exports.generateBestTweet = exports.generateTweets = exports.socialContent = void 0;
__exportStar(require("./socialContent"), exports);
var socialContent_1 = require("./socialContent");
Object.defineProperty(exports, "socialContent", { enumerable: true, get: function () { return __importDefault(socialContent_1).default; } });
// Re-export commonly used functions at top level
var socialContent_2 = require("./socialContent");
Object.defineProperty(exports, "generateTweets", { enumerable: true, get: function () { return socialContent_2.generateTweets; } });
Object.defineProperty(exports, "generateBestTweet", { enumerable: true, get: function () { return socialContent_2.generateBestTweet; } });
Object.defineProperty(exports, "generateHashtags", { enumerable: true, get: function () { return socialContent_2.generateHashtags; } });
Object.defineProperty(exports, "parseNotionContent", { enumerable: true, get: function () { return socialContent_2.parseNotionContent; } });
Object.defineProperty(exports, "smartTruncate", { enumerable: true, get: function () { return socialContent_2.smartTruncate; } });
//# sourceMappingURL=index.js.map