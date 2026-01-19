import { StreamArbitrary } from './_internals/StreamArbitrary.js';
/**@__NO_SIDE_EFFECTS__*/function infiniteStream(arb, constraints) {
    const history = constraints !== undefined && typeof constraints === 'object' && 'noHistory' in constraints
        ? !constraints.noHistory
        : true;
    return new StreamArbitrary(arb, history);
}
export { infiniteStream };
