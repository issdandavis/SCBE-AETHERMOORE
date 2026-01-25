"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.unlinkedToLinkedEntitiesMapper = unlinkedToLinkedEntitiesMapper;
const globals_js_1 = require("../../../utils/globals.js");
const stringify_js_1 = require("../../../utils/stringify.js");
const safeObjectAssign = Object.assign;
const safeObjectCreate = Object.create;
const safeObjectDefineProperty = Object.defineProperty;
const safeObjectGetPrototypeOf = Object.getPrototypeOf;
const safeObjectPrototype = Object.prototype;
function withTargetStringifiedValue(stringifiedValue) {
    return safeObjectDefineProperty(safeObjectCreate(null), stringify_js_1.toStringMethod, {
        configurable: false,
        enumerable: false,
        writable: false,
        value: () => stringifiedValue,
    });
}
function withReferenceStringifiedValue(type, index) {
    return withTargetStringifiedValue(`<${(0, globals_js_1.String)(type)}#${index}>`);
}
function unlinkedToLinkedEntitiesMapper(unlinkedEntities, producedLinks) {
    const linkedEntities = safeObjectCreate(safeObjectPrototype);
    for (const name in unlinkedEntities) {
        const unlinkedEntitiesForName = unlinkedEntities[name];
        const linkedEntitiesForName = [];
        for (const unlinkedEntity of unlinkedEntitiesForName) {
            const linkedEntity = safeObjectAssign(safeObjectCreate(safeObjectGetPrototypeOf(unlinkedEntity)), unlinkedEntity);
            linkedEntitiesForName.push(linkedEntity);
        }
        linkedEntities[name] = linkedEntitiesForName;
    }
    for (const name in producedLinks) {
        const entityLinks = producedLinks[name];
        for (let entityIndex = 0; entityIndex !== entityLinks.length; ++entityIndex) {
            const entityLinksForInstance = entityLinks[entityIndex];
            const linkedInstance = linkedEntities[name][entityIndex];
            for (const prop in entityLinksForInstance) {
                const propValue = entityLinksForInstance[prop];
                linkedInstance[prop] =
                    propValue.index === undefined
                        ? undefined
                        : typeof propValue.index === 'number'
                            ? linkedEntities[propValue.type][propValue.index]
                            : (0, globals_js_1.safeMap)(propValue.index, (index) => linkedEntities[propValue.type][index]);
            }
            safeObjectDefineProperty(linkedInstance, stringify_js_1.toStringMethod, {
                configurable: false,
                enumerable: false,
                writable: false,
                value: () => {
                    const unlinkedEntity = unlinkedEntities[name][entityIndex];
                    const entity = safeObjectAssign(safeObjectCreate(safeObjectGetPrototypeOf(unlinkedEntity)), unlinkedEntity);
                    for (const prop in entityLinksForInstance) {
                        const propValue = entityLinksForInstance[prop];
                        entity[prop] = (propValue.index === undefined
                            ? undefined
                            : typeof propValue.index === 'number'
                                ? withReferenceStringifiedValue(propValue.type, propValue.index)
                                : (0, globals_js_1.safeMap)(propValue.index, (index) => withReferenceStringifiedValue(propValue.type, index)));
                    }
                    return (0, stringify_js_1.stringify)(entity);
                },
            });
        }
    }
    return linkedEntities;
}
