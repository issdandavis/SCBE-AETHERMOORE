import { ConstantArbitrary } from './_internals/ConstantArbitrary.js';
export /**@__NO_SIDE_EFFECTS__*/function constant(value) {
    return new ConstantArbitrary([value]);
}
