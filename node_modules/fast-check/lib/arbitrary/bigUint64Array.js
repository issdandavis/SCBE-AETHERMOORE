import { BigInt, BigUint64Array } from '../utils/globals.js';
import { bigInt } from './bigInt.js';
import { typedIntArrayArbitraryArbitraryBuilder } from './_internals/builders/TypedIntArrayArbitraryBuilder.js';
export /**@__NO_SIDE_EFFECTS__*/function bigUint64Array(constraints = {}) {
    return typedIntArrayArbitraryArbitraryBuilder(constraints, BigInt(0), BigInt('18446744073709551615'), BigUint64Array, bigInt);
}
