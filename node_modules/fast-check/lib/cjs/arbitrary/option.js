"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.option = option;
const constant_js_1 = require("./constant.js");
const FrequencyArbitrary_js_1 = require("./_internals/FrequencyArbitrary.js");
const globals_js_1 = require("../utils/globals.js");
/**@__NO_SIDE_EFFECTS__*/function option(arb, constraints = {}) {
    const freq = constraints.freq == null ? 6 : constraints.freq;
    const nilValue = (0, globals_js_1.safeHasOwnProperty)(constraints, 'nil') ? constraints.nil : null;
    const nilArb = (0, constant_js_1.constant)(nilValue);
    const weightedArbs = [
        { arbitrary: nilArb, weight: 1, fallbackValue: { default: nilValue } },
        { arbitrary: arb, weight: freq - 1 },
    ];
    const frequencyConstraints = {
        withCrossShrink: true,
        depthSize: constraints.depthSize,
        maxDepth: constraints.maxDepth,
        depthIdentifier: constraints.depthIdentifier,
    };
    return FrequencyArbitrary_js_1.FrequencyArbitrary.from(weightedArbs, frequencyConstraints, 'fc.option');
}
