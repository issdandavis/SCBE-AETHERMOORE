import { initialPoolForEntityGraph } from './_internals/InitialPoolForEntityGraphArbitrary.js';
import { unlinkedToLinkedEntitiesMapper } from './_internals/mappers/UnlinkedToLinkedEntities.js';
import { onTheFlyLinksForEntityGraph } from './_internals/OnTheFlyLinksForEntityGraphArbitrary.js';
import { unlinkedEntitiesForEntityGraph } from './_internals/UnlinkedEntitiesForEntityGraph.js';
const safeObjectCreate = Object.create;
const safeObjectKeys = Object.keys;
export /**@__NO_SIDE_EFFECTS__*/function entityGraph(arbitraries, relations, constraints = {}) {
    const allKeys = safeObjectKeys(arbitraries);
    const initialPoolConstraints = constraints.initialPoolConstraints || safeObjectCreate(null);
    const unicityConstraints = constraints.unicityConstraints || safeObjectCreate(null);
    const unlinkedContraints = { noNullPrototype: constraints.noNullPrototype };
    return (initialPoolForEntityGraph(allKeys, initialPoolConstraints).chain((defaultEntities) => onTheFlyLinksForEntityGraph(relations, defaultEntities).chain((producedLinks) => unlinkedEntitiesForEntityGraph(arbitraries, (name) => producedLinks[name].length, (name) => unicityConstraints[name], unlinkedContraints).map((unlinkedEntities) => unlinkedToLinkedEntitiesMapper(unlinkedEntities, producedLinks)))));
}
