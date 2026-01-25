import { Uint16Array } from '../utils/globals.js';
import { integer } from './integer.js';
import { typedIntArrayArbitraryArbitraryBuilder } from './_internals/builders/TypedIntArrayArbitraryBuilder.js';
export /**@__NO_SIDE_EFFECTS__*/function uint16Array(constraints = {}) {
    return typedIntArrayArbitraryArbitraryBuilder(constraints, 0, 65535, Uint16Array, integer);
}
