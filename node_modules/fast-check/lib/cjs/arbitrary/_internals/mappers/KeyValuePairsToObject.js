"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.keyValuePairsToObjectMapper = keyValuePairsToObjectMapper;
exports.keyValuePairsToObjectUnmapper = keyValuePairsToObjectUnmapper;
const globals_js_1 = require("../../../utils/globals.js");
const safeObjectCreate = Object.create;
const safeObjectDefineProperty = Object.defineProperty;
const safeObjectGetOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
const safeObjectGetPrototypeOf = Object.getPrototypeOf;
const safeReflectOwnKeys = Reflect.ownKeys;
function keyValuePairsToObjectMapper(definition) {
    const obj = definition[1] ? safeObjectCreate(null) : {};
    for (const keyValue of definition[0]) {
        safeObjectDefineProperty(obj, keyValue[0], {
            enumerable: true,
            configurable: true,
            writable: true,
            value: keyValue[1],
        });
    }
    return obj;
}
function isValidPropertyNameFilter(descriptor) {
    return (descriptor !== undefined &&
        !!descriptor.configurable &&
        !!descriptor.enumerable &&
        !!descriptor.writable &&
        descriptor.get === undefined &&
        descriptor.set === undefined);
}
function keyValuePairsToObjectUnmapper(value) {
    if (typeof value !== 'object' || value === null) {
        throw new globals_js_1.Error('Incompatible instance received: should be a non-null object');
    }
    const hasNullPrototype = safeObjectGetPrototypeOf(value) === null;
    const hasObjectPrototype = 'constructor' in value && value.constructor === Object;
    if (!hasNullPrototype && !hasObjectPrototype) {
        throw new globals_js_1.Error('Incompatible instance received: should be of exact type Object');
    }
    const propertyDescriptors = (0, globals_js_1.safeMap)(safeReflectOwnKeys(value), (key) => [
        key,
        safeObjectGetOwnPropertyDescriptor(value, key),
    ]);
    if (!(0, globals_js_1.safeEvery)(propertyDescriptors, ([, descriptor]) => isValidPropertyNameFilter(descriptor))) {
        throw new globals_js_1.Error('Incompatible instance received: should contain only c/e/w properties without get/set');
    }
    return [(0, globals_js_1.safeMap)(propertyDescriptors, ([key, descriptor]) => [key, descriptor.value]), hasNullPrototype];
}
