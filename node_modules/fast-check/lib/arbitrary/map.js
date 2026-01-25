import { tuple } from './tuple.js';
import { uniqueArray } from './uniqueArray.js';
import { arrayToMapMapper, arrayToMapUnmapper } from './_internals/mappers/ArrayToMap.js';
function mapKeyExtractor(entry) {
    return entry[0];
}
export /**@__NO_SIDE_EFFECTS__*/function map(keyArb, valueArb, constraints = {}) {
    return uniqueArray(tuple(keyArb, valueArb), {
        minLength: constraints.minKeys,
        maxLength: constraints.maxKeys,
        size: constraints.size,
        selector: mapKeyExtractor,
        depthIdentifier: constraints.depthIdentifier,
        comparator: 'SameValueZero',
    }).map(arrayToMapMapper, arrayToMapUnmapper);
}
