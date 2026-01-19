import { SubarrayArbitrary } from './_internals/SubarrayArbitrary.js';
export /**@__NO_SIDE_EFFECTS__*/function shuffledSubarray(originalArray, constraints = {}) {
    const { minLength = 0, maxLength = originalArray.length } = constraints;
    return new SubarrayArbitrary(originalArray, false, minLength, maxLength);
}
