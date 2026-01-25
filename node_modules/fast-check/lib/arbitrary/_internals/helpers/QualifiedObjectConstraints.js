import { boolean } from '../../boolean.js';
import { constant } from '../../constant.js';
import { double } from '../../double.js';
import { maxSafeInteger } from '../../maxSafeInteger.js';
import { oneof } from '../../oneof.js';
import { string } from '../../string.js';
import { boxedArbitraryBuilder } from '../builders/BoxedArbitraryBuilder.js';
function defaultValues(constraints, stringArbitrary) {
    return [
        boolean(),
        maxSafeInteger(),
        double(),
        stringArbitrary(constraints),
        oneof(stringArbitrary(constraints), constant(null), constant(undefined)),
    ];
}
function boxArbitraries(arbs) {
    return arbs.map((arb) => boxedArbitraryBuilder(arb));
}
function boxArbitrariesIfNeeded(arbs, boxEnabled) {
    return boxEnabled ? boxArbitraries(arbs).concat(arbs) : arbs;
}
export function toQualifiedObjectConstraints(settings = {}) {
    const valueConstraints = {
        size: settings.size,
        unit: 'stringUnit' in settings ? settings.stringUnit : settings.withUnicodeString ? 'binary' : undefined,
    };
    return {
        key: settings.key !== undefined ? settings.key : string(valueConstraints),
        values: boxArbitrariesIfNeeded(settings.values !== undefined ? settings.values : defaultValues(valueConstraints, string), settings.withBoxedValues === true),
        depthSize: settings.depthSize,
        maxDepth: settings.maxDepth,
        maxKeys: settings.maxKeys,
        size: settings.size,
        withSet: settings.withSet === true,
        withMap: settings.withMap === true,
        withObjectString: settings.withObjectString === true,
        withNullPrototype: settings.withNullPrototype === true,
        withBigInt: settings.withBigInt === true,
        withDate: settings.withDate === true,
        withTypedArray: settings.withTypedArray === true,
        withSparseArray: settings.withSparseArray === true,
    };
}
