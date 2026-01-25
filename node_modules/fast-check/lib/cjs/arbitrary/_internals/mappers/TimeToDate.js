"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.timeToDateMapper = timeToDateMapper;
exports.timeToDateUnmapper = timeToDateUnmapper;
exports.timeToDateMapperWithNaN = timeToDateMapperWithNaN;
exports.timeToDateUnmapperWithNaN = timeToDateUnmapperWithNaN;
const globals_js_1 = require("../../../utils/globals.js");
const safeNaN = Number.NaN;
const safeNumberIsNaN = Number.isNaN;
function timeToDateMapper(time) {
    return new globals_js_1.Date(time);
}
function timeToDateUnmapper(value) {
    if (!(value instanceof globals_js_1.Date) || value.constructor !== globals_js_1.Date) {
        throw new globals_js_1.Error('Not a valid value for date unmapper');
    }
    return (0, globals_js_1.safeGetTime)(value);
}
function timeToDateMapperWithNaN(valueForNaN) {
    return (time) => {
        return time === valueForNaN ? new globals_js_1.Date(safeNaN) : timeToDateMapper(time);
    };
}
function timeToDateUnmapperWithNaN(valueForNaN) {
    return (value) => {
        const time = timeToDateUnmapper(value);
        return safeNumberIsNaN(time) ? valueForNaN : time;
    };
}
