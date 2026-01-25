"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.StreamArbitrary = void 0;
const Arbitrary_js_1 = require("../../check/arbitrary/definition/Arbitrary.js");
const Value_js_1 = require("../../check/arbitrary/definition/Value.js");
const symbols_js_1 = require("../../check/symbols.js");
const Stream_js_1 = require("../../stream/Stream.js");
const globals_js_1 = require("../../utils/globals.js");
const stringify_js_1 = require("../../utils/stringify.js");
const safeObjectDefineProperties = Object.defineProperties;
function prettyPrint(numSeen, seenValuesStrings) {
    const seenSegment = seenValuesStrings !== undefined ? `${(0, globals_js_1.safeJoin)(seenValuesStrings, ',')}…` : `${numSeen} emitted`;
    return `Stream(${seenSegment})`;
}
class StreamArbitrary extends Arbitrary_js_1.Arbitrary {
    constructor(arb, history) {
        super();
        this.arb = arb;
        this.history = history;
    }
    generate(mrng, biasFactor) {
        const appliedBiasFactor = biasFactor !== undefined && mrng.nextInt(1, biasFactor) === 1 ? biasFactor : undefined;
        const enrichedProducer = () => {
            const seenValues = this.history ? [] : null;
            let numSeenValues = 0;
            const g = function* (arb, clonedMrng) {
                while (true) {
                    const value = arb.generate(clonedMrng, appliedBiasFactor).value;
                    numSeenValues++;
                    if (seenValues !== null) {
                        (0, globals_js_1.safePush)(seenValues, value);
                    }
                    yield value;
                }
            };
            const s = new Stream_js_1.Stream(g(this.arb, mrng.clone()));
            return safeObjectDefineProperties(s, {
                toString: {
                    value: () => prettyPrint(numSeenValues, seenValues !== null ? seenValues.map(stringify_js_1.stringify) : undefined),
                },
                [stringify_js_1.toStringMethod]: {
                    value: () => prettyPrint(numSeenValues, seenValues !== null ? seenValues.map(stringify_js_1.stringify) : undefined),
                },
                [stringify_js_1.asyncToStringMethod]: {
                    value: async () => prettyPrint(numSeenValues, seenValues !== null ? await Promise.all(seenValues.map(stringify_js_1.asyncStringify)) : undefined),
                },
                [symbols_js_1.cloneMethod]: { value: enrichedProducer, enumerable: true },
            });
        };
        return new Value_js_1.Value(enrichedProducer(), undefined);
    }
    canShrinkWithoutContext(value) {
        return false;
    }
    shrink(_value, _context) {
        return Stream_js_1.Stream.nil();
    }
}
exports.StreamArbitrary = StreamArbitrary;
