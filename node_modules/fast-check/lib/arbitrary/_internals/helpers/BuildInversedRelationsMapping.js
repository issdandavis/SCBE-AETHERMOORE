import { Error as SError, String as SString, Map as SMap, safeMapGet, safeMapSet, safeMapHas, } from '../../../utils/globals.js';
export function buildInversedRelationsMapping(relations) {
    let foundInversedRelations = 0;
    const requestedInversedRelations = new SMap();
    for (const name in relations) {
        const relationsForName = relations[name];
        for (const fieldName in relationsForName) {
            const relation = relationsForName[fieldName];
            if (relation.arity !== 'inverse') {
                continue;
            }
            let existingOnes = safeMapGet(requestedInversedRelations, relation.type);
            if (existingOnes === undefined) {
                existingOnes = new SMap();
                safeMapSet(requestedInversedRelations, relation.type, existingOnes);
            }
            if (safeMapHas(existingOnes, relation.forwardRelationship)) {
                throw new SError(`Cannot declare multiple inverse relationships for the same forward relationship ${SString(relation.forwardRelationship)} on type ${SString(relation.type)}`);
            }
            safeMapSet(existingOnes, relation.forwardRelationship, { type: name, property: fieldName });
            foundInversedRelations += 1;
        }
    }
    const inversedRelations = new SMap();
    if (foundInversedRelations === 0) {
        return inversedRelations;
    }
    for (const name in relations) {
        const relationsForName = relations[name];
        const requestedInversedRelationsForName = safeMapGet(requestedInversedRelations, name);
        if (requestedInversedRelationsForName === undefined) {
            continue;
        }
        for (const fieldName in relationsForName) {
            const relation = relationsForName[fieldName];
            if (relation.arity === 'inverse') {
                continue;
            }
            const requestedIfAny = safeMapGet(requestedInversedRelationsForName, fieldName);
            if (requestedIfAny === undefined) {
                continue;
            }
            if (requestedIfAny.type !== relation.type) {
                throw new SError(`Inverse relationship ${SString(requestedIfAny.property)} on type ${SString(requestedIfAny.type)} references forward relationship ${SString(fieldName)} but types do not match`);
            }
            safeMapSet(inversedRelations, relation, requestedIfAny);
        }
    }
    if (inversedRelations.size !== foundInversedRelations) {
        throw new SError(`Some inverse relationships could not be matched with their corresponding forward relationships`);
    }
    return inversedRelations;
}
