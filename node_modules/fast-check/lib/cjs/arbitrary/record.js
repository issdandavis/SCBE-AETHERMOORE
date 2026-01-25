"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.record = record;
const PartialRecordArbitraryBuilder_js_1 = require("./_internals/builders/PartialRecordArbitraryBuilder.js");
/**@__NO_SIDE_EFFECTS__*/function record(recordModel, constraints) {
    const noNullPrototype = constraints !== undefined && !!constraints.noNullPrototype;
    if (constraints == null) {
        return (0, PartialRecordArbitraryBuilder_js_1.buildPartialRecordArbitrary)(recordModel, undefined, noNullPrototype);
    }
    const requireDeletedKeys = 'requiredKeys' in constraints && constraints.requiredKeys !== undefined;
    if (!requireDeletedKeys) {
        return (0, PartialRecordArbitraryBuilder_js_1.buildPartialRecordArbitrary)(recordModel, undefined, noNullPrototype);
    }
    const requiredKeys = ('requiredKeys' in constraints ? constraints.requiredKeys : undefined) || [];
    for (let idx = 0; idx !== requiredKeys.length; ++idx) {
        const descriptor = Object.getOwnPropertyDescriptor(recordModel, requiredKeys[idx]);
        if (descriptor === undefined) {
            throw new Error(`requiredKeys cannot reference keys that have not been defined in recordModel`);
        }
        if (!descriptor.enumerable) {
            throw new Error(`requiredKeys cannot reference keys that have are enumerable in recordModel`);
        }
    }
    return (0, PartialRecordArbitraryBuilder_js_1.buildPartialRecordArbitrary)(recordModel, requiredKeys, noNullPrototype);
}
