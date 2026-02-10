"use strict";
/**
 * @file index.ts
 * @module fleet/polly-pads/modes
 * @layer L13
 * @component Polly Pad Specialist Modes
 * @version 1.0.0
 *
 * Exports all 6 specialist modes and shared types.
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
exports.MissionPlanningMode = exports.CommunicationsMode = exports.ScienceMode = exports.SystemsMode = exports.NavigationMode = exports.EngineeringMode = exports.BaseMode = void 0;
exports.createMode = createMode;
exports.createAllModes = createAllModes;
// Types
__exportStar(require("./types"), exports);
// Base class
var base_mode_1 = require("./base-mode");
Object.defineProperty(exports, "BaseMode", { enumerable: true, get: function () { return base_mode_1.BaseMode; } });
// Tech specialist modes
var engineering_1 = require("./engineering");
Object.defineProperty(exports, "EngineeringMode", { enumerable: true, get: function () { return engineering_1.EngineeringMode; } });
var navigation_1 = require("./navigation");
Object.defineProperty(exports, "NavigationMode", { enumerable: true, get: function () { return navigation_1.NavigationMode; } });
var systems_1 = require("./systems");
Object.defineProperty(exports, "SystemsMode", { enumerable: true, get: function () { return systems_1.SystemsMode; } });
// Non-tech specialist modes
var science_1 = require("./science");
Object.defineProperty(exports, "ScienceMode", { enumerable: true, get: function () { return science_1.ScienceMode; } });
var communications_1 = require("./communications");
Object.defineProperty(exports, "CommunicationsMode", { enumerable: true, get: function () { return communications_1.CommunicationsMode; } });
var mission_planning_1 = require("./mission-planning");
Object.defineProperty(exports, "MissionPlanningMode", { enumerable: true, get: function () { return mission_planning_1.MissionPlanningMode; } });
const engineering_2 = require("./engineering");
const navigation_2 = require("./navigation");
const systems_2 = require("./systems");
const science_2 = require("./science");
const communications_2 = require("./communications");
const mission_planning_2 = require("./mission-planning");
/**
 * Factory: create a mode instance by name.
 */
function createMode(mode) {
    switch (mode) {
        case 'engineering':
            return new engineering_2.EngineeringMode();
        case 'navigation':
            return new navigation_2.NavigationMode();
        case 'systems':
            return new systems_2.SystemsMode();
        case 'science':
            return new science_2.ScienceMode();
        case 'communications':
            return new communications_2.CommunicationsMode();
        case 'mission_planning':
            return new mission_planning_2.MissionPlanningMode();
    }
}
/**
 * Create all 6 mode instances as a map.
 */
function createAllModes() {
    const modes = new Map();
    const modeNames = [
        'engineering',
        'navigation',
        'systems',
        'science',
        'communications',
        'mission_planning',
    ];
    for (const name of modeNames) {
        modes.set(name, createMode(name));
    }
    return modes;
}
//# sourceMappingURL=index.js.map