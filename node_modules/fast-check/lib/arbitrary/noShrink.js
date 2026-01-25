import { Arbitrary } from '../check/arbitrary/definition/Arbitrary.js';
import { Stream } from '../stream/Stream.js';
const stableObjectGetPrototypeOf = Object.getPrototypeOf;
class NoShrinkArbitrary extends Arbitrary {
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
        return Stream.nil();
    }
}
export /**@__NO_SIDE_EFFECTS__*/function noShrink(arb) {
    if (stableObjectGetPrototypeOf(arb) === NoShrinkArbitrary.prototype &&
        arb.generate === NoShrinkArbitrary.prototype.generate &&
        arb.canShrinkWithoutContext === NoShrinkArbitrary.prototype.canShrinkWithoutContext &&
        arb.shrink === NoShrinkArbitrary.prototype.shrink) {
        return arb;
    }
    return new NoShrinkArbitrary(arb);
}
