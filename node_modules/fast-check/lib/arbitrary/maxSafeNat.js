import { IntegerArbitrary } from './_internals/IntegerArbitrary.js';
const safeMaxSafeInteger = Number.MAX_SAFE_INTEGER;
export /**@__NO_SIDE_EFFECTS__*/function maxSafeNat() {
    return new IntegerArbitrary(0, safeMaxSafeInteger);
}
