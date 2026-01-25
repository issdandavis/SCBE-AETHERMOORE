"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.date = date;
const globals_js_1 = require("../utils/globals.js");
const integer_js_1 = require("./integer.js");
const TimeToDate_js_1 = require("./_internals/mappers/TimeToDate.js");
const safeNumberIsNaN = Number.isNaN;
/**@__NO_SIDE_EFFECTS__*/function date(constraints = {}) {
    const intMin = constraints.min !== undefined ? (0, globals_js_1.safeGetTime)(constraints.min) : -8640000000000000;
    const intMax = constraints.max !== undefined ? (0, globals_js_1.safeGetTime)(constraints.max) : 8640000000000000;
    const noInvalidDate = constraints.noInvalidDate;
    if (safeNumberIsNaN(intMin))
        throw new Error('fc.date min must be valid instance of Date');
    if (safeNumberIsNaN(intMax))
        throw new Error('fc.date max must be valid instance of Date');
    if (intMin > intMax)
        throw new Error('fc.date max must be greater or equal to min');
    if (noInvalidDate) {
        return (0, integer_js_1.integer)({ min: intMin, max: intMax }).map(TimeToDate_js_1.timeToDateMapper, TimeToDate_js_1.timeToDateUnmapper);
    }
    const valueForNaN = intMax + 1;
    return (0, integer_js_1.integer)({ min: intMin, max: intMax + 1 }).map((0, TimeToDate_js_1.timeToDateMapperWithNaN)(valueForNaN), (0, TimeToDate_js_1.timeToDateUnmapperWithNaN)(valueForNaN));
}
