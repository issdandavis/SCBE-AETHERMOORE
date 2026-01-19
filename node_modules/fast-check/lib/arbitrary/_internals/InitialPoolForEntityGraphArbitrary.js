import { array } from '../array.js';
import { tuple } from '../tuple.js';
import { constant } from '../constant.js';
import { safeFlat, Error as SError } from '../../utils/globals.js';
function canHaveAtLeastOneItem(keys, constraints) {
    for (const key of keys) {
        const constraintsOnKey = constraints[key] || {};
        if (constraintsOnKey.maxLength === undefined || constraintsOnKey.maxLength > 0) {
            return true;
        }
    }
    return false;
}
export function initialPoolForEntityGraph(keys, constraints) {
    if (keys.length === 0) {
        return constant([]);
    }
    if (!canHaveAtLeastOneItem(keys, constraints)) {
        throw new SError('Contraints on pool must accept at least one entity, maxLength cannot sum to 0');
    }
    const arbitraries = keys.map((key) => array(constant(key), constraints[key]));
    return (tuple(...arbitraries)
        .map((values) => safeFlat(values))
        .filter((names) => names.length > 0));
}
