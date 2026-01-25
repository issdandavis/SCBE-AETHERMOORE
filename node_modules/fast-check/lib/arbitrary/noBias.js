import { Arbitrary } from '../check/arbitrary/definition/Arbitrary.js';
const stableObjectGetPrototypeOf = Object.getPrototypeOf;
class NoBiasArbitrary extends Arbitrary {
    constructor(arb) {
        super();
        this.arb = arb;
    }
    generate(mrng, _biasFactor) {
        return this.arb.generate(mrng, undefined);
    }
    canShrinkWithoutContext(value) {
        return this.arb.canShrinkWithoutContext(value);
    }
    shrink(value, context) {
        return this.arb.shrink(value, context);
    }
}
export /**@__NO_SIDE_EFFECTS__*/function noBias(arb) {
    if (stableObjectGetPrototypeOf(arb) === NoBiasArbitrary.prototype &&
        arb.generate === NoBiasArbitrary.prototype.generate &&
        arb.canShrinkWithoutContext === NoBiasArbitrary.prototype.canShrinkWithoutContext &&
        arb.shrink === NoBiasArbitrary.prototype.shrink) {
        return arb;
    }
    return new NoBiasArbitrary(arb);
}
