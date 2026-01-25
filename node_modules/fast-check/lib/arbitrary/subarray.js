import { SubarrayArbitrary } from './_internals/SubarrayArbitrary.js';
export /**@__NO_SIDE_EFFECTS__*/function subarray(originalArray, constraints = {}) {
    const { minLength = 0, maxLength = originalArray.length } = constraints;
    return new SubarrayArbitrary(originalArray, true, minLength, maxLength);
}
