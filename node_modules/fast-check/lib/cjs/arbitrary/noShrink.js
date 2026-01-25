"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.noShrink = noShrink;
const Arbitrary_js_1 = require("../check/arbitrary/definition/Arbitrary.js");
const Stream_js_1 = require("../stream/Stream.js");
const stableObjectGetPrototypeOf = Object.getPrototypeOf;
class NoShrinkArbitrary extends Arbitrary_js_1.Arbitrary {
    constructor(arb) {
        super();
        this.arb = arb;
    }
    generate(mrng, biasFactor) {
        return this.arb.generate(mrng, biasFactor);
    }
    canShrinkWithoutContext(value) {
        return this.arb.canShrinkWithoutContext(value);
    }
    shrink(_value, _context) {
        return Stream_js_1.Stream.nil();
    }
}
/**@__NO_SIDE_EFFECTS__*/function noShrink(arb) {
    if (stableObjectGetPrototypeOf(arb) === NoShrinkArbitrary.prototype &&
        arb.generate === NoShrinkArbitrary.prototype.generate &&
        arb.canShrinkWithoutContext === NoShrinkArbitrary.prototype.canShrinkWithoutContext &&
        arb.shrink === NoShrinkArbitrary.prototype.shrink) {
        return arb;
    }
    return new NoShrinkArbitrary(arb);
}
