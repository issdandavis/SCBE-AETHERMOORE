import { TupleArbitrary } from './_internals/TupleArbitrary.js';
export /**@__NO_SIDE_EFFECTS__*/function tuple(...arbs) {
    return new TupleArbitrary(arbs);
}
