import { uniqueArray } from './uniqueArray.js';
import { arrayToSetMapper, arrayToSetUnmapper } from './_internals/mappers/ArrayToSet.js';
export /**@__NO_SIDE_EFFECTS__*/function set(arb, constraints = {}) {
    return uniqueArray(arb, {
        minLength: constraints.minLength,
        maxLength: constraints.maxLength,
        size: constraints.size,
        depthIdentifier: constraints.depthIdentifier,
        comparator: 'SameValueZero',
    }).map(arrayToSetMapper, arrayToSetUnmapper);
}
