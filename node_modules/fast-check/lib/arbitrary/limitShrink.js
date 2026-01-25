import { LimitedShrinkArbitrary } from './_internals/LimitedShrinkArbitrary.js';
export /**@__NO_SIDE_EFFECTS__*/function limitShrink(arbitrary, maxShrinks) {
    return new LimitedShrinkArbitrary(arbitrary, maxShrinks);
}
