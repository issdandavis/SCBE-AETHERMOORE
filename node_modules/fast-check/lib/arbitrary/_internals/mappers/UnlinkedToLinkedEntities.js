import { safeMap, String as SString } from '../../../utils/globals.js';
import { stringify, toStringMethod } from '../../../utils/stringify.js';
const safeObjectAssign = Object.assign;
const safeObjectCreate = Object.create;
const safeObjectDefineProperty = Object.defineProperty;
const safeObjectGetPrototypeOf = Object.getPrototypeOf;
const safeObjectPrototype = Object.prototype;
function withTargetStringifiedValue(stringifiedValue) {
    return safeObjectDefineProperty(safeObjectCreate(null), toStringMethod, {
        configurable: false,
        enumerable: false,
        writable: false,
        value: () => stringifiedValue,
    });
}
function withReferenceStringifiedValue(type, index) {
    return withTargetStringifiedValue(`<${SString(type)}#${index}>`);
}
export function unlinkedToLinkedEntitiesMapper(unlinkedEntities, producedLinks) {
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
                            : safeMap(propValue.index, (index) => linkedEntities[propValue.type][index]);
            }
            safeObjectDefineProperty(linkedInstance, toStringMethod, {
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
                                : safeMap(propValue.index, (index) => withReferenceStringifiedValue(propValue.type, index)));
                    }
                    return stringify(entity);
                },
            });
        }
    }
    return linkedEntities;
}
