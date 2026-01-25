import { BigInt, BigInt64Array } from '../utils/globals.js';
import { bigInt } from './bigInt.js';
import { typedIntArrayArbitraryArbitraryBuilder } from './_internals/builders/TypedIntArrayArbitraryBuilder.js';
export /**@__NO_SIDE_EFFECTS__*/function bigInt64Array(constraints = {}) {
    return typedIntArrayArbitraryArbitraryBuilder(constraints, BigInt('-9223372036854775808'), BigInt('9223372036854775807'), BigInt64Array, bigInt);
}
