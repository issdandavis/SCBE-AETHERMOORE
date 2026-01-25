import { CloneArbitrary } from './_internals/CloneArbitrary.js';
/**@__NO_SIDE_EFFECTS__*/function clone(arb, numValues) {
    return new CloneArbitrary(arb, numValues);
}
export { clone };
