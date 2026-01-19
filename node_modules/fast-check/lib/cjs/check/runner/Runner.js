"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.check = check;
exports.assert = assert;
const Stream_js_1 = require("../../stream/Stream.js");
const GlobalParameters_js_1 = require("./configuration/GlobalParameters.js");
const QualifiedParameters_js_1 = require("./configuration/QualifiedParameters.js");
const DecorateProperty_js_1 = require("./DecorateProperty.js");
const RunnerIterator_js_1 = require("./RunnerIterator.js");
const SourceValuesIterator_js_1 = require("./SourceValuesIterator.js");
const Tosser_js_1 = require("./Tosser.js");
const PathWalker_js_1 = require("./utils/PathWalker.js");
const RunDetailsFormatter_js_1 = require("./utils/RunDetailsFormatter.js");
function runIt(property, shrink, sourceValues, verbose, interruptedAsFailure) {
    const runner = new RunnerIterator_js_1.RunnerIterator(sourceValues, shrink, verbose, interruptedAsFailure);
    for (const v of runner) {
        property.runBeforeEach();
        const out = property.run(v);
        property.runAfterEach();
        runner.handleResult(out);
    }
    return runner.runExecution;
}
async function asyncRunIt(property, shrink, sourceValues, verbose, interruptedAsFailure) {
    const runner = new RunnerIterator_js_1.RunnerIterator(sourceValues, shrink, verbose, interruptedAsFailure);
    for (const v of runner) {
        await property.runBeforeEach();
        const out = await property.run(v);
        await property.runAfterEach();
        runner.handleResult(out);
    }
    return runner.runExecution;
}
function check(rawProperty, params) {
    if (rawProperty == null || rawProperty.generate == null)
        throw new Error('Invalid property encountered, please use a valid property');
    if (rawProperty.run == null)
        throw new Error('Invalid property encountered, please use a valid property not an arbitrary');
    const qParams = QualifiedParameters_js_1.QualifiedParameters.read({
        ...(0, GlobalParameters_js_1.readConfigureGlobal)(),
        ...params,
    });
    if (qParams.reporter !== undefined && qParams.asyncReporter !== undefined)
        throw new Error('Invalid parameters encountered, reporter and asyncReporter cannot be specified together');
    if (qParams.asyncReporter !== undefined && !rawProperty.isAsync())
        throw new Error('Invalid parameters encountered, only asyncProperty can be used when asyncReporter specified');
    const property = (0, DecorateProperty_js_1.decorateProperty)(rawProperty, qParams);
    const maxInitialIterations = qParams.path.length === 0 || qParams.path.indexOf(':') === -1 ? qParams.numRuns : -1;
    const maxSkips = qParams.numRuns * qParams.maxSkipsPerRun;
    const shrink = (...args) => property.shrink(...args);
    const initialValues = qParams.path.length === 0
        ? (0, Tosser_js_1.toss)(property, qParams.seed, qParams.randomType, qParams.examples)
        : (0, PathWalker_js_1.pathWalk)(qParams.path, (0, Stream_js_1.stream)((0, Tosser_js_1.lazyToss)(property, qParams.seed, qParams.randomType, qParams.examples)), shrink);
    const sourceValues = new SourceValuesIterator_js_1.SourceValuesIterator(initialValues, maxInitialIterations, maxSkips);
    const finalShrink = !qParams.endOnFailure ? shrink : Stream_js_1.Stream.nil;
    return property.isAsync()
        ? asyncRunIt(property, finalShrink, sourceValues, qParams.verbose, qParams.markInterruptAsFailure).then((e) => e.toRunDetails(qParams.seed, qParams.path, maxSkips, qParams))
        : runIt(property, finalShrink, sourceValues, qParams.verbose, qParams.markInterruptAsFailure).toRunDetails(qParams.seed, qParams.path, maxSkips, qParams);
}
function assert(property, params) {
    const out = check(property, params);
    if (property.isAsync())
        return out.then(RunDetailsFormatter_js_1.asyncReportRunDetails);
    else
        (0, RunDetailsFormatter_js_1.reportRunDetails)(out);
}
