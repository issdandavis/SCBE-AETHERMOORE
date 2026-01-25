"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.SubarrayArbitrary = void 0;
const Arbitrary_js_1 = require("../../check/arbitrary/definition/Arbitrary.js");
const Value_js_1 = require("../../check/arbitrary/definition/Value.js");
const LazyIterableIterator_js_1 = require("../../stream/LazyIterableIterator.js");
const Stream_js_1 = require("../../stream/Stream.js");
const globals_js_1 = require("../../utils/globals.js");
const IsSubarrayOf_js_1 = require("./helpers/IsSubarrayOf.js");
const IntegerArbitrary_js_1 = require("./IntegerArbitrary.js");
const safeMathFloor = Math.floor;
const safeMathLog = Math.log;
const safeArrayIsArray = Array.isArray;
class SubarrayArbitrary extends Arbitrary_js_1.Arbitrary {
    constructor(originalArray, isOrdered, minLength, maxLength) {
        super();
        this.originalArray = originalArray;
        this.isOrdered = isOrdered;
        this.minLength = minLength;
        this.maxLength = maxLength;
        if (minLength < 0 || minLength > originalArray.length)
            throw new Error('fc.*{s|S}ubarrayOf expects the minimal length to be between 0 and the size of the original array');
        if (maxLength < 0 || maxLength > originalArray.length)
            throw new Error('fc.*{s|S}ubarrayOf expects the maximal length to be between 0 and the size of the original array');
        if (minLength > maxLength)
            throw new Error('fc.*{s|S}ubarrayOf expects the minimal length to be inferior or equal to the maximal length');
        this.lengthArb = new IntegerArbitrary_js_1.IntegerArbitrary(minLength, maxLength);
        this.biasedLengthArb =
            minLength !== maxLength
                ? new IntegerArbitrary_js_1.IntegerArbitrary(minLength, minLength + safeMathFloor(safeMathLog(maxLength - minLength) / safeMathLog(2)))
                : this.lengthArb;
    }
    generate(mrng, biasFactor) {
        const lengthArb = biasFactor !== undefined && mrng.nextInt(1, biasFactor) === 1 ? this.biasedLengthArb : this.lengthArb;
        const size = lengthArb.generate(mrng, undefined);
        const sizeValue = size.value;
        const remainingElements = (0, globals_js_1.safeMap)(this.originalArray, (_v, idx) => idx);
        const ids = [];
        for (let index = 0; index !== sizeValue; ++index) {
            const selectedIdIndex = mrng.nextInt(0, remainingElements.length - 1);
            (0, globals_js_1.safePush)(ids, remainingElements[selectedIdIndex]);
            (0, globals_js_1.safeSplice)(remainingElements, selectedIdIndex, 1);
        }
        if (this.isOrdered) {
            (0, globals_js_1.safeSort)(ids, (a, b) => a - b);
        }
        return new Value_js_1.Value((0, globals_js_1.safeMap)(ids, (i) => this.originalArray[i]), size.context);
    }
    canShrinkWithoutContext(value) {
        if (!safeArrayIsArray(value)) {
            return false;
        }
        if (!this.lengthArb.canShrinkWithoutContext(value.length)) {
            return false;
        }
        return (0, IsSubarrayOf_js_1.isSubarrayOf)(this.originalArray, value);
    }
    shrink(value, context) {
        if (value.length === 0) {
            return Stream_js_1.Stream.nil();
        }
        return this.lengthArb
            .shrink(value.length, context)
            .map((newSize) => {
            return new Value_js_1.Value((0, globals_js_1.safeSlice)(value, value.length - newSize.value), newSize.context);
        })
            .join(value.length > this.minLength
            ? (0, LazyIterableIterator_js_1.makeLazy)(() => this.shrink((0, globals_js_1.safeSlice)(value, 1), undefined)
                .filter((newValue) => this.minLength <= newValue.value.length + 1)
                .map((newValue) => new Value_js_1.Value([value[0], ...newValue.value], undefined)))
            : Stream_js_1.Stream.nil());
    }
}
exports.SubarrayArbitrary = SubarrayArbitrary;
