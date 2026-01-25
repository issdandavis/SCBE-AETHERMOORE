import { Int8Array } from '../utils/globals.js';
import { integer } from './integer.js';
import { typedIntArrayArbitraryArbitraryBuilder } from './_internals/builders/TypedIntArrayArbitraryBuilder.js';
export /**@__NO_SIDE_EFFECTS__*/function int8Array(constraints = {}) {
    return typedIntArrayArbitraryArbitraryBuilder(constraints, -128, 127, Int8Array, integer);
}
