import { BigInt } from '../utils/globals.js';
import { constantFrom } from './constantFrom.js';
export /**@__NO_SIDE_EFFECTS__*/function falsy(constraints) {
    if (!constraints || !constraints.withBigInt) {
        return constantFrom(false, null, undefined, 0, '', NaN);
    }
    return constantFrom(false, null, undefined, 0, '', NaN, BigInt(0));
}
