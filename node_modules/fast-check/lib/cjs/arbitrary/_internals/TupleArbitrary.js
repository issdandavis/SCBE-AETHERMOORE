"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.TupleArbitrary = void 0;
exports.tupleShrink = tupleShrink;
const Stream_js_1 = require("../../stream/Stream.js");
const symbols_js_1 = require("../../check/symbols.js");
const Arbitrary_js_1 = require("../../check/arbitrary/definition/Arbitrary.js");
const Value_js_1 = require("../../check/arbitrary/definition/Value.js");
const globals_js_1 = require("../../utils/globals.js");
const LazyIterableIterator_js_1 = require("../../stream/LazyIterableIterator.js");
const safeArrayIsArray = Array.isArray;
const safeObjectDefineProperty = Object.defineProperty;
function tupleMakeItCloneable(vs, values) {
    return safeObjectDefineProperty(vs, symbols_js_1.cloneMethod, {
        value: () => {
            const cloned = [];
            for (let idx = 0; idx !== values.length; ++idx) {
                (0, globals_js_1.safePush)(cloned, values[idx].value);
            }
            tupleMakeItCloneable(cloned, values);
            return cloned;
        },
    });
}
function tupleWrapper(values) {
    let cloneable = false;
    const vs = [];
    const ctxs = [];
    for (let idx = 0; idx !== values.length; ++idx) {
        const v = values[idx];
        cloneable = cloneable || v.hasToBeCloned;
        (0, globals_js_1.safePush)(vs, v.value);
        (0, globals_js_1.safePush)(ctxs, v.context);
    }
    if (cloneable) {
        tupleMakeItCloneable(vs, values);
    }
    return new Value_js_1.Value(vs, ctxs);
}
function tupleShrink(arbs, value, context) {
    const shrinks = [];
    const safeContext = safeArrayIsArray(context) ? context : [];
    for (let idx = 0; idx !== arbs.length; ++idx) {
        (0, globals_js_1.safePush)(shrinks, (0, LazyIterableIterator_js_1.makeLazy)(() => arbs[idx]
            .shrink(value[idx], safeContext[idx])
            .map((v) => {
            const nextValues = (0, globals_js_1.safeMap)(value, (v, idx) => new Value_js_1.Value((0, symbols_js_1.cloneIfNeeded)(v), safeContext[idx]));
            return [...(0, globals_js_1.safeSlice)(nextValues, 0, idx), v, ...(0, globals_js_1.safeSlice)(nextValues, idx + 1)];
        })
            .map(tupleWrapper)));
    }
    return Stream_js_1.Stream.nil().join(...shrinks);
}
class TupleArbitrary extends Arbitrary_js_1.Arbitrary {
    constructor(arbs) {
        super();
        this.arbs = arbs;
        for (let idx = 0; idx !== arbs.length; ++idx) {
            const arb = arbs[idx];
            if (arb == null || arb.generate == null)
                throw new Error(`Invalid parameter encountered at index ${idx}: expecting an Arbitrary`);
        }
    }
    generate(mrng, biasFactor) {
        const mapped = [];
        for (let idx = 0; idx !== this.arbs.length; ++idx) {
            (0, globals_js_1.safePush)(mapped, this.arbs[idx].generate(mrng, biasFactor));
        }
        return tupleWrapper(mapped);
    }
    canShrinkWithoutContext(value) {
        if (!safeArrayIsArray(value) || value.length !== this.arbs.length) {
            return false;
        }
        for (let index = 0; index !== this.arbs.length; ++index) {
            if (!this.arbs[index].canShrinkWithoutContext(value[index])) {
                return false;
            }
        }
        return true;
    }
    shrink(value, context) {
        return tupleShrink(this.arbs, value, context);
    }
}
exports.TupleArbitrary = TupleArbitrary;
