import { Arbitrary } from '../../check/arbitrary/definition/Arbitrary.js';
import { Value } from '../../check/arbitrary/definition/Value.js';
import { Stream } from '../../stream/Stream.js';
import { safeAdd, safeHas, safeMap, safeMapGet, safePush, Set as SSet, Error as SError, String as SString, } from '../../utils/globals.js';
import { constant } from '../constant.js';
import { integer } from '../integer.js';
import { noBias } from '../noBias.js';
import { option } from '../option.js';
import { uniqueArray } from '../uniqueArray.js';
import { buildInversedRelationsMapping } from './helpers/BuildInversedRelationsMapping.js';
import { createDepthIdentifier } from './helpers/DepthContext.js';
const safeObjectCreate = Object.create;
function produceLinkUnitaryIndexArbitrary(strategy, currentIndexIfSameType, countInTargetType) {
    switch (strategy) {
        case 'exclusive':
            return constant(countInTargetType);
        case 'successor': {
            const min = currentIndexIfSameType !== undefined ? currentIndexIfSameType + 1 : 0;
            return noBias(integer({ min, max: countInTargetType }));
        }
        case 'any':
            return noBias(integer({ min: 0, max: countInTargetType }));
    }
}
function computeLinkIndex(arity, strategy, currentIndexIfSameType, countInTargetType, currentEntityDepth, mrng, biasFactor) {
    const linkArbitrary = produceLinkUnitaryIndexArbitrary(strategy, currentIndexIfSameType, countInTargetType);
    switch (arity) {
        case '0-1':
            return option(linkArbitrary, { nil: undefined, depthIdentifier: currentEntityDepth }).generate(mrng, biasFactor)
                .value;
        case '1':
            return linkArbitrary.generate(mrng, biasFactor).value;
        case 'many': {
            let randomUnicity = 0;
            const values = option(uniqueArray(linkArbitrary, {
                depthIdentifier: currentEntityDepth,
                selector: (v) => (v === countInTargetType ? v + ++randomUnicity : v),
                minLength: 1,
            }), { nil: [], depthIdentifier: currentEntityDepth }).generate(mrng, biasFactor).value;
            let offset = 0;
            return safeMap(values, (v) => (v === countInTargetType ? v + offset++ : v));
        }
    }
}
class OnTheFlyLinksForEntityGraphArbitrary extends Arbitrary {
    constructor(relations, defaultEntities) {
        super();
        this.relations = relations;
        this.defaultEntities = defaultEntities;
        const nonExclusiveEntities = new SSet();
        const exclusiveEntities = new SSet();
        for (const name in relations) {
            const relationsForName = relations[name];
            for (const fieldName in relationsForName) {
                const relation = relationsForName[fieldName];
                if (relation.arity === 'inverse') {
                    continue;
                }
                if (relation.strategy === 'exclusive') {
                    if (safeHas(nonExclusiveEntities, relation.type)) {
                        throw new SError(`Cannot mix exclusive with other strategies for type ${SString(relation.type)}`);
                    }
                    safeAdd(exclusiveEntities, relation.type);
                }
                else {
                    if (safeHas(exclusiveEntities, relation.type)) {
                        throw new SError(`Cannot mix exclusive with other strategies for type ${SString(relation.type)}`);
                    }
                    safeAdd(nonExclusiveEntities, relation.type);
                }
                if (relation.strategy === 'successor' && relation.type !== name) {
                    throw new SError(`Cannot mix types for the strategy successor`);
                }
                if (relation.strategy === 'successor' && relation.arity === '1') {
                    throw new SError(`Cannot use an arity of 1 for the strategy successor`);
                }
            }
        }
        this.inversedRelations = buildInversedRelationsMapping(relations);
    }
    createEmptyLinksInstanceFor(targetType) {
        const emptyLinksInstance = safeObjectCreate(null);
        const relationsForType = this.relations[targetType];
        for (const name in relationsForType) {
            const relation = relationsForType[name];
            if (relation.arity === 'inverse') {
                emptyLinksInstance[name] = { type: relation.type, index: [] };
            }
        }
        return emptyLinksInstance;
    }
    generate(mrng, biasFactor) {
        const producedLinks = safeObjectCreate(null);
        for (const name in this.relations) {
            producedLinks[name] = [];
        }
        const toBeProducedEntities = [];
        for (const name of this.defaultEntities) {
            safePush(toBeProducedEntities, { type: name, indexInType: producedLinks[name].length, depth: 0 });
            safePush(producedLinks[name], this.createEmptyLinksInstanceFor(name));
        }
        let lastTreatedEntities = -1;
        while (++lastTreatedEntities < toBeProducedEntities.length) {
            const currentEntity = toBeProducedEntities[lastTreatedEntities];
            const currentRelations = this.relations[currentEntity.type];
            const currentProducedLinks = producedLinks[currentEntity.type];
            const currentLinks = currentProducedLinks[currentEntity.indexInType];
            const currentEntityDepth = createDepthIdentifier();
            currentEntityDepth.depth = currentEntity.depth;
            for (const name in currentRelations) {
                const relation = currentRelations[name];
                if (relation.arity === 'inverse') {
                    continue;
                }
                const targetType = relation.type;
                const producedLinksInTargetType = producedLinks[targetType];
                const countInTargetType = producedLinksInTargetType.length;
                const linkOrLinks = computeLinkIndex(relation.arity, relation.strategy || 'any', targetType === currentEntity.type ? currentEntity.indexInType : undefined, producedLinksInTargetType.length, currentEntityDepth, mrng, biasFactor);
                currentLinks[name] = { type: targetType, index: linkOrLinks };
                const links = linkOrLinks === undefined ? [] : typeof linkOrLinks === 'number' ? [linkOrLinks] : linkOrLinks;
                for (const link of links) {
                    if (link >= countInTargetType) {
                        safePush(toBeProducedEntities, { type: targetType, indexInType: link, depth: currentEntity.depth + 1 });
                        safePush(producedLinksInTargetType, this.createEmptyLinksInstanceFor(targetType));
                    }
                    const inversed = safeMapGet(this.inversedRelations, relation);
                    if (inversed !== undefined) {
                        const knownInversedLinks = producedLinksInTargetType[link][inversed.property].index;
                        safePush(knownInversedLinks, currentEntity.indexInType);
                    }
                }
            }
        }
        toBeProducedEntities.length = 0;
        return new Value(producedLinks, undefined);
    }
    canShrinkWithoutContext(value) {
        return false;
    }
    shrink(_value, _context) {
        return Stream.nil();
    }
}
export function onTheFlyLinksForEntityGraph(relations, defaultEntities) {
    return new OnTheFlyLinksForEntityGraphArbitrary(relations, defaultEntities);
}
