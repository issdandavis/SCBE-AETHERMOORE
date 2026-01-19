"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.buildInversedRelationsMapping = buildInversedRelationsMapping;
const globals_js_1 = require("../../../utils/globals.js");
function buildInversedRelationsMapping(relations) {
    let foundInversedRelations = 0;
    const requestedInversedRelations = new globals_js_1.Map();
    for (const name in relations) {
        const relationsForName = relations[name];
        for (const fieldName in relationsForName) {
            const relation = relationsForName[fieldName];
            if (relation.arity !== 'inverse') {
                continue;
            }
            let existingOnes = (0, globals_js_1.safeMapGet)(requestedInversedRelations, relation.type);
            if (existingOnes === undefined) {
                existingOnes = new globals_js_1.Map();
                (0, globals_js_1.safeMapSet)(requestedInversedRelations, relation.type, existingOnes);
            }
            if ((0, globals_js_1.safeMapHas)(existingOnes, relation.forwardRelationship)) {
                throw new globals_js_1.Error(`Cannot declare multiple inverse relationships for the same forward relationship ${(0, globals_js_1.String)(relation.forwardRelationship)} on type ${(0, globals_js_1.String)(relation.type)}`);
            }
            (0, globals_js_1.safeMapSet)(existingOnes, relation.forwardRelationship, { type: name, property: fieldName });
            foundInversedRelations += 1;
        }
    }
    const inversedRelations = new globals_js_1.Map();
    if (foundInversedRelations === 0) {
        return inversedRelations;
    }
    for (const name in relations) {
        const relationsForName = relations[name];
        const requestedInversedRelationsForName = (0, globals_js_1.safeMapGet)(requestedInversedRelations, name);
        if (requestedInversedRelationsForName === undefined) {
            continue;
        }
        for (const fieldName in relationsForName) {
            const relation = relationsForName[fieldName];
            if (relation.arity === 'inverse') {
                continue;
            }
            const requestedIfAny = (0, globals_js_1.safeMapGet)(requestedInversedRelationsForName, fieldName);
            if (requestedIfAny === undefined) {
                continue;
            }
            if (requestedIfAny.type !== relation.type) {
                throw new globals_js_1.Error(`Inverse relationship ${(0, globals_js_1.String)(requestedIfAny.property)} on type ${(0, globals_js_1.String)(requestedIfAny.type)} references forward relationship ${(0, globals_js_1.String)(fieldName)} but types do not match`);
            }
            (0, globals_js_1.safeMapSet)(inversedRelations, relation, requestedIfAny);
        }
    }
    if (inversedRelations.size !== foundInversedRelations) {
        throw new globals_js_1.Error(`Some inverse relationships could not be matched with their corresponding forward relationships`);
    }
    return inversedRelations;
}
