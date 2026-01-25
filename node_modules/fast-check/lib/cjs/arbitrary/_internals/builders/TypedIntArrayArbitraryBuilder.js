"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.typedIntArrayArbitraryArbitraryBuilder = typedIntArrayArbitraryArbitraryBuilder;
const array_js_1 = require("../../array.js");
function typedIntArrayArbitraryArbitraryBuilder(constraints, defaultMin, defaultMax, TypedArrayClass, arbitraryBuilder) {
    const generatorName = TypedArrayClass.name;
    const { min = defaultMin, max = defaultMax, ...arrayConstraints } = constraints;
    if (min > max) {
        throw new Error(`Invalid range passed to ${generatorName}: min must be lower than or equal to max`);
    }
    if (min < defaultMin) {
        throw new Error(`Invalid min value passed to ${generatorName}: min must be greater than or equal to ${defaultMin}`);
    }
    if (max > defaultMax) {
        throw new Error(`Invalid max value passed to ${generatorName}: max must be lower than or equal to ${defaultMax}`);
    }
    return (0, array_js_1.array)(arbitraryBuilder({ min, max }), arrayConstraints).map((data) => TypedArrayClass.from(data), (value) => {
        if (!(value instanceof TypedArrayClass))
            throw new Error('Invalid type');
        return [...value];
    });
}
