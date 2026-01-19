import { IntegerArbitrary } from './_internals/IntegerArbitrary.js';
const safeMinSafeInteger = Number.MIN_SAFE_INTEGER;
const safeMaxSafeInteger = Number.MAX_SAFE_INTEGER;
export /**@__NO_SIDE_EFFECTS__*/function maxSafeInteger() {
    return new IntegerArbitrary(safeMinSafeInteger, safeMaxSafeInteger);
}
