import { array } from '../array.js';
import { record } from '../record.js';
import { uniqueArray } from '../uniqueArray.js';
const safeObjectCreate = Object.create;
export function unlinkedEntitiesForEntityGraph(arbitraries, countFor, unicityConstraintsFor, constraints) {
    const recordModel = safeObjectCreate(null);
    for (const name in arbitraries) {
        const entityRecordModel = arbitraries[name];
        const entityArbitrary = record(entityRecordModel, constraints);
        const count = countFor(name);
        const unicityConstraints = unicityConstraintsFor(name);
        const arrayConstraints = { minLength: count, maxLength: count };
        recordModel[name] =
            unicityConstraints !== undefined
                ? uniqueArray(entityArbitrary, { ...arrayConstraints, selector: unicityConstraints })
                : array(entityArbitrary, arrayConstraints);
    }
    return record(recordModel);
}
