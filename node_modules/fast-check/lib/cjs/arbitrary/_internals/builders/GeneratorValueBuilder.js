"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildGeneratorValue = buildGeneratorValue;
const Value_js_1 = require("../../../check/arbitrary/definition/Value.js");
const symbols_js_1 = require("../../../check/symbols.js");
const globals_js_1 = require("../../../utils/globals.js");
const stringify_js_1 = require("../../../utils/stringify.js");
const safeObjectAssign = Object.assign;
function buildGeneratorValue(mrng, biasFactor, computePreBuiltValues, arbitraryCache) {
    const preBuiltValues = computePreBuiltValues();
    let localMrng = mrng.clone();
    const context = { mrng: mrng.clone(), biasFactor, history: [] };
    const valueFunction = (arb) => {
        const preBuiltValue = preBuiltValues[context.history.length];
        if (preBuiltValue !== undefined && preBuiltValue.arb === arb) {
            const value = preBuiltValue.value;
            (0, globals_js_1.safePush)(context.history, { arb, value, context: preBuiltValue.context, mrng: preBuiltValue.mrng });
            localMrng = preBuiltValue.mrng.clone();
            return value;
        }
        const g = arb.generate(localMrng, biasFactor);
        (0, globals_js_1.safePush)(context.history, { arb, value: g.value_, context: g.context, mrng: localMrng.clone() });
        return g.value;
    };
    const memoedValueFunction = (arb, ...args) => {
        return valueFunction(arbitraryCache(arb, args));
    };
    const valueMethods = {
        values() {
            return (0, globals_js_1.safeMap)(context.history, (c) => c.value);
        },
        [symbols_js_1.cloneMethod]() {
            return buildGeneratorValue(mrng, biasFactor, computePreBuiltValues, arbitraryCache).value;
        },
        [stringify_js_1.toStringMethod]() {
            return (0, stringify_js_1.stringify)((0, globals_js_1.safeMap)(context.history, (c) => c.value));
        },
    };
    const value = safeObjectAssign(memoedValueFunction, valueMethods);
    return new Value_js_1.Value(value, context);
}
