import { Arbitrary } from '../../check/arbitrary/definition/Arbitrary.js';
import { Value } from '../../check/arbitrary/definition/Value.js';
import { cloneMethod } from '../../check/symbols.js';
import { Stream } from '../../stream/Stream.js';
import { safeJoin, safePush } from '../../utils/globals.js';
import { asyncStringify, asyncToStringMethod, stringify, toStringMethod } from '../../utils/stringify.js';
const safeObjectDefineProperties = Object.defineProperties;
function prettyPrint(numSeen, seenValuesStrings) {
    const seenSegment = seenValuesStrings !== undefined ? `${safeJoin(seenValuesStrings, ',')}…` : `${numSeen} emitted`;
    return `Stream(${seenSegment})`;
}
export class StreamArbitrary extends Arbitrary {
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
                        safePush(seenValues, value);
                    }
                    yield value;
                }
            };
            const s = new Stream(g(this.arb, mrng.clone()));
            return safeObjectDefineProperties(s, {
                toString: {
                    value: () => prettyPrint(numSeenValues, seenValues !== null ? seenValues.map(stringify) : undefined),
                },
                [toStringMethod]: {
                    value: () => prettyPrint(numSeenValues, seenValues !== null ? seenValues.map(stringify) : undefined),
                },
                [asyncToStringMethod]: {
                    value: async () => prettyPrint(numSeenValues, seenValues !== null ? await Promise.all(seenValues.map(asyncStringify)) : undefined),
                },
                [cloneMethod]: { value: enrichedProducer, enumerable: true },
            });
        };
        return new Value(enrichedProducer(), undefined);
    }
    canShrinkWithoutContext(value) {
        return false;
    }
    shrink(_value, _context) {
        return Stream.nil();
    }
}
