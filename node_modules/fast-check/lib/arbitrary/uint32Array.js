import { Uint32Array } from '../utils/globals.js';
import { integer } from './integer.js';
import { typedIntArrayArbitraryArbitraryBuilder } from './_internals/builders/TypedIntArrayArbitraryBuilder.js';
export /**@__NO_SIDE_EFFECTS__*/function uint32Array(constraints = {}) {
    return typedIntArrayArbitraryArbitraryBuilder(constraints, 0, 0xffffffff, Uint32Array, integer);
}
