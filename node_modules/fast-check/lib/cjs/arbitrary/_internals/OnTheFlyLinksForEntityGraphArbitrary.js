"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.onTheFlyLinksForEntityGraph = onTheFlyLinksForEntityGraph;
const Arbitrary_js_1 = require("../../check/arbitrary/definition/Arbitrary.js");
const Value_js_1 = require("../../check/arbitrary/definition/Value.js");
const Stream_js_1 = require("../../stream/Stream.js");
const globals_js_1 = require("../../utils/globals.js");
const constant_js_1 = require("../constant.js");
const integer_js_1 = require("../integer.js");
const noBias_js_1 = require("../noBias.js");
const option_js_1 = require("../option.js");
const uniqueArray_js_1 = require("../uniqueArray.js");
const BuildInversedRelationsMapping_js_1 = require("./helpers/BuildInversedRelationsMapping.js");
const DepthContext_js_1 = require("./helpers/DepthContext.js");
const safeObjectCreate = Object.create;
function produceLinkUnitaryIndexArbitrary(strategy, currentIndexIfSameType, countInTargetType) {
    switch (strategy) {
        case 'exclusive':
            return (0, constant_js_1.constant)(countInTargetType);
        case 'successor': {
            const min = currentIndexIfSameType !== undefined ? currentIndexIfSameType + 1 : 0;
            return (0, noBias_js_1.noBias)((0, integer_js_1.integer)({ min, max: countInTargetType }));
        }
        case 'any':
            return (0, noBias_js_1.noBias)((0, integer_js_1.integer)({ min: 0, max: countInTargetType }));
    }
}
function computeLinkIndex(arity, strategy, currentIndexIfSameType, countInTargetType, currentEntityDepth, mrng, biasFactor) {
    const linkArbitrary = produceLinkUnitaryIndexArbitrary(strategy, currentIndexIfSameType, countInTargetType);
    switch (arity) {
        case '0-1':
            return (0, option_js_1.option)(linkArbitrary, { nil: undefined, depthIdentifier: currentEntityDepth }).generate(mrng, biasFactor)
                .value;
        case '1':
            return linkArbitrary.generate(mrng, biasFactor).value;
        case 'many': {
            let randomUnicity = 0;
            const values = (0, option_js_1.option)((0, uniqueArray_js_1.uniqueArray)(linkArbitrary, {
                depthIdentifier: currentEntityDepth,
                selector: (v) => (v === countInTargetType ? v + ++randomUnicity : v),
                minLength: 1,
            }), { nil: [], depthIdentifier: currentEntityDepth }).generate(mrng, biasFactor).value;
            let offset = 0;
            return (0, globals_js_1.safeMap)(values, (v) => (v === countInTargetType ? v + offset++ : v));
        }
    }
}
class OnTheFlyLinksForEntityGraphArbitrary extends Arbitrary_js_1.Arbitrary {
    constructor(relations, defaultEntities) {
        super();
        this.relations = relations;
        this.defaultEntities = defaultEntities;
        const nonExclusiveEntities = new globals_js_1.Set();
        const exclusiveEntities = new globals_js_1.Set();
        for (const name in relations) {
            const relationsForName = relations[name];
            for (const fieldName in relationsForName) {
                const relation = relationsForName[fieldName];
                if (relation.arity === 'inverse') {
                    continue;
                }
                if (relation.strategy === 'exclusive') {
                    if ((0, globals_js_1.safeHas)(nonExclusiveEntities, relation.type)) {
                        throw new globals_js_1.Error(`Cannot mix exclusive with other strategies for type ${(0, globals_js_1.String)(relation.type)}`);
                    }
                    (0, globals_js_1.safeAdd)(exclusiveEntities, relation.type);
                }
                else {
                    if ((0, globals_js_1.safeHas)(exclusiveEntities, relation.type)) {
                        throw new globals_js_1.Error(`Cannot mix exclusive with other strategies for type ${(0, globals_js_1.String)(relation.type)}`);
                    }
                    (0, globals_js_1.safeAdd)(nonExclusiveEntities, relation.type);
                }
                if (relation.strategy === 'successor' && relation.type !== name) {
                    throw new globals_js_1.Error(`Cannot mix types for the strategy successor`);
                }
                if (relation.strategy === 'successor' && relation.arity === '1') {
                    throw new globals_js_1.Error(`Cannot use an arity of 1 for the strategy successor`);
                }
            }
        }
        this.inversedRelations = (0, BuildInversedRelationsMapping_js_1.buildInversedRelationsMapping)(relations);
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
            (0, globals_js_1.safePush)(toBeProducedEntities, { type: name, indexInType: producedLinks[name].length, depth: 0 });
            (0, globals_js_1.safePush)(producedLinks[name], this.createEmptyLinksInstanceFor(name));
        }
        let lastTreatedEntities = -1;
        while (++lastTreatedEntities < toBeProducedEntities.length) {
            const currentEntity = toBeProducedEntities[lastTreatedEntities];
            const currentRelations = this.relations[currentEntity.type];
            const currentProducedLinks = producedLinks[currentEntity.type];
            const currentLinks = currentProducedLinks[currentEntity.indexInType];
            const currentEntityDepth = (0, DepthContext_js_1.createDepthIdentifier)();
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
                        (0, globals_js_1.safePush)(toBeProducedEntities, { type: targetType, indexInType: link, depth: currentEntity.depth + 1 });
                        (0, globals_js_1.safePush)(producedLinksInTargetType, this.createEmptyLinksInstanceFor(targetType));
                    }
                    const inversed = (0, globals_js_1.safeMapGet)(this.inversedRelations, relation);
                    if (inversed !== undefined) {
                        const knownInversedLinks = producedLinksInTargetType[link][inversed.property].index;
                        (0, globals_js_1.safePush)(knownInversedLinks, currentEntity.indexInType);
                    }
                }
            }
        }
        toBeProducedEntities.length = 0;
        return new Value_js_1.Value(producedLinks, undefined);
    }
    canShrinkWithoutContext(value) {
        return false;
    }
    shrink(_value, _context) {
        return Stream_js_1.Stream.nil();
    }
}
function onTheFlyLinksForEntityGraph(relations, defaultEntities) {
    return new OnTheFlyLinksForEntityGraphArbitrary(relations, defaultEntities);
}
