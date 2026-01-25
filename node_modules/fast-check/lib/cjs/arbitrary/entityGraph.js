"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.entityGraph = entityGraph;
const InitialPoolForEntityGraphArbitrary_js_1 = require("./_internals/InitialPoolForEntityGraphArbitrary.js");
const UnlinkedToLinkedEntities_js_1 = require("./_internals/mappers/UnlinkedToLinkedEntities.js");
const OnTheFlyLinksForEntityGraphArbitrary_js_1 = require("./_internals/OnTheFlyLinksForEntityGraphArbitrary.js");
const UnlinkedEntitiesForEntityGraph_js_1 = require("./_internals/UnlinkedEntitiesForEntityGraph.js");
const safeObjectCreate = Object.create;
const safeObjectKeys = Object.keys;
/**@__NO_SIDE_EFFECTS__*/function entityGraph(arbitraries, relations, constraints = {}) {
    const allKeys = safeObjectKeys(arbitraries);
    const initialPoolConstraints = constraints.initialPoolConstraints || safeObjectCreate(null);
    const unicityConstraints = constraints.unicityConstraints || safeObjectCreate(null);
    const unlinkedContraints = { noNullPrototype: constraints.noNullPrototype };
    return ((0, InitialPoolForEntityGraphArbitrary_js_1.initialPoolForEntityGraph)(allKeys, initialPoolConstraints).chain((defaultEntities) => (0, OnTheFlyLinksForEntityGraphArbitrary_js_1.onTheFlyLinksForEntityGraph)(relations, defaultEntities).chain((producedLinks) => (0, UnlinkedEntitiesForEntityGraph_js_1.unlinkedEntitiesForEntityGraph)(arbitraries, (name) => producedLinks[name].length, (name) => unicityConstraints[name], unlinkedContraints).map((unlinkedEntities) => (0, UnlinkedToLinkedEntities_js_1.unlinkedToLinkedEntitiesMapper)(unlinkedEntities, producedLinks)))));
}
