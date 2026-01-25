"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.LimitedShrinkArbitrary = void 0;
const Arbitrary_js_1 = require("../../check/arbitrary/definition/Arbitrary.js");
const Value_js_1 = require("../../check/arbitrary/definition/Value.js");
const Stream_js_1 = require("../../stream/Stream.js");
const ZipIterableIterators_js_1 = require("./helpers/ZipIterableIterators.js");
function* iotaFrom(startValue) {
    let value = startValue;
    while (true) {
        yield value;
        ++value;
    }
}
class LimitedShrinkArbitrary extends Arbitrary_js_1.Arbitrary {
    constructor(arb, maxShrinks) {
        super();
        this.arb = arb;
        this.maxShrinks = maxShrinks;
    }
    generate(mrng, biasFactor) {
        const value = this.arb.generate(mrng, biasFactor);
        return this.valueMapper(value, 0);
    }
    canShrinkWithoutContext(value) {
        return this.arb.canShrinkWithoutContext(value);
    }
    shrink(value, context) {
        if (this.isSafeContext(context)) {
            return this.safeShrink(value, context.originalContext, context.length);
        }
        return this.safeShrink(value, undefined, 0);
    }
    safeShrink(value, originalContext, currentLength) {
        const remaining = this.maxShrinks - currentLength;
        if (remaining <= 0) {
            return Stream_js_1.Stream.nil();
        }
        return new Stream_js_1.Stream((0, ZipIterableIterators_js_1.zipIterableIterators)(this.arb.shrink(value, originalContext), iotaFrom(currentLength + 1)))
            .take(remaining)
            .map((valueAndLength) => this.valueMapper(valueAndLength[0], valueAndLength[1]));
    }
    valueMapper(v, newLength) {
        const context = { originalContext: v.context, length: newLength };
        return new Value_js_1.Value(v.value, context);
    }
    isSafeContext(context) {
        return (context != null &&
            typeof context === 'object' &&
            'originalContext' in context &&
            'length' in context);
    }
}
exports.LimitedShrinkArbitrary = LimitedShrinkArbitrary;
