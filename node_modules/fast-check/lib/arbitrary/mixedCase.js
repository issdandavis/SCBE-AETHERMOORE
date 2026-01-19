import { safeToUpperCase, safeToLowerCase } from '../utils/globals.js';
import { MixedCaseArbitrary } from './_internals/MixedCaseArbitrary.js';
function defaultToggleCase(rawChar) {
    const upper = safeToUpperCase(rawChar);
    if (upper !== rawChar)
        return upper;
    return safeToLowerCase(rawChar);
}
export /**@__NO_SIDE_EFFECTS__*/function mixedCase(stringArb, constraints) {
    const toggleCase = (constraints && constraints.toggleCase) || defaultToggleCase;
    const untoggleAll = constraints && constraints.untoggleAll;
    return new MixedCaseArbitrary(stringArb, toggleCase, untoggleAll);
}
