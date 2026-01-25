"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.unlinkedEntitiesForEntityGraph = unlinkedEntitiesForEntityGraph;
const array_js_1 = require("../array.js");
const record_js_1 = require("../record.js");
const uniqueArray_js_1 = require("../uniqueArray.js");
const safeObjectCreate = Object.create;
function unlinkedEntitiesForEntityGraph(arbitraries, countFor, unicityConstraintsFor, constraints) {
    const recordModel = safeObjectCreate(null);
    for (const name in arbitraries) {
        const entityRecordModel = arbitraries[name];
        const entityArbitrary = (0, record_js_1.record)(entityRecordModel, constraints);
        const count = countFor(name);
        const unicityConstraints = unicityConstraintsFor(name);
        const arrayConstraints = { minLength: count, maxLength: count };
        recordModel[name] =
            unicityConstraints !== undefined
                ? (0, uniqueArray_js_1.uniqueArray)(entityArbitrary, { ...arrayConstraints, selector: unicityConstraints })
                : (0, array_js_1.array)(entityArbitrary, arrayConstraints);
    }
    return (0, record_js_1.record)(recordModel);
}
