"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.scheduler = scheduler;
exports.schedulerFor = schedulerFor;
const BuildSchedulerFor_js_1 = require("./_internals/helpers/BuildSchedulerFor.js");
const SchedulerArbitrary_js_1 = require("./_internals/SchedulerArbitrary.js");
/**@__NO_SIDE_EFFECTS__*/function scheduler(constraints) {
    const { act = (f) => f() } = constraints || {};
    return new SchedulerArbitrary_js_1.SchedulerArbitrary(act);
}
function schedulerFor(customOrderingOrConstraints, constraintsOrUndefined) {
    const { act = (f) => f() } = Array.isArray(customOrderingOrConstraints)
        ? constraintsOrUndefined || {}
        : customOrderingOrConstraints || {};
    if (Array.isArray(customOrderingOrConstraints)) {
        return (0, BuildSchedulerFor_js_1.buildSchedulerFor)(act, customOrderingOrConstraints);
    }
    return function (_strs, ...ordering) {
        return (0, BuildSchedulerFor_js_1.buildSchedulerFor)(act, ordering);
    };
}
