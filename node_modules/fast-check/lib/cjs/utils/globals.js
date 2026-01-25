"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.Symbol = exports.Map = exports.encodeURIComponent = exports.Uint32Array = exports.Uint16Array = exports.Uint8ClampedArray = exports.Uint8Array = exports.Set = exports.String = exports.Number = exports.Int32Array = exports.Int16Array = exports.Int8Array = exports.Float64Array = exports.Float32Array = exports.Error = exports.Date = exports.Boolean = exports.BigUint64Array = exports.BigInt64Array = exports.BigInt = exports.Array = void 0;
exports.safeForEach = safeForEach;
exports.safeIndexOf = safeIndexOf;
exports.safeJoin = safeJoin;
exports.safeMap = safeMap;
exports.safeFlat = safeFlat;
exports.safeFilter = safeFilter;
exports.safePush = safePush;
exports.safePop = safePop;
exports.safeSplice = safeSplice;
exports.safeSlice = safeSlice;
exports.safeSort = safeSort;
exports.safeEvery = safeEvery;
exports.safeGetTime = safeGetTime;
exports.safeToISOString = safeToISOString;
exports.safeAdd = safeAdd;
exports.safeHas = safeHas;
exports.safeSet = safeSet;
exports.safeGet = safeGet;
exports.safeMapSet = safeMapSet;
exports.safeMapGet = safeMapGet;
exports.safeMapHas = safeMapHas;
exports.safeSplit = safeSplit;
exports.safeStartsWith = safeStartsWith;
exports.safeEndsWith = safeEndsWith;
exports.safeSubstring = safeSubstring;
exports.safeToLowerCase = safeToLowerCase;
exports.safeToUpperCase = safeToUpperCase;
exports.safePadStart = safePadStart;
exports.safeCharCodeAt = safeCharCodeAt;
exports.safeNormalize = safeNormalize;
exports.safeReplace = safeReplace;
exports.safeNumberToString = safeNumberToString;
exports.safeHasOwnProperty = safeHasOwnProperty;
exports.safeToString = safeToString;
exports.safeErrorToString = safeErrorToString;
const apply_js_1 = require("./apply.js");
const SArray = Array;
exports.Array = SArray;
const SBigInt = BigInt;
exports.BigInt = SBigInt;
const SBigInt64Array = BigInt64Array;
exports.BigInt64Array = SBigInt64Array;
const SBigUint64Array = BigUint64Array;
exports.BigUint64Array = SBigUint64Array;
const SBoolean = Boolean;
exports.Boolean = SBoolean;
const SDate = Date;
exports.Date = SDate;
const SError = Error;
exports.Error = SError;
const SFloat32Array = Float32Array;
exports.Float32Array = SFloat32Array;
const SFloat64Array = Float64Array;
exports.Float64Array = SFloat64Array;
const SInt8Array = Int8Array;
exports.Int8Array = SInt8Array;
const SInt16Array = Int16Array;
exports.Int16Array = SInt16Array;
const SInt32Array = Int32Array;
exports.Int32Array = SInt32Array;
const SNumber = Number;
exports.Number = SNumber;
const SString = String;
exports.String = SString;
const SSet = Set;
exports.Set = SSet;
const SUint8Array = Uint8Array;
exports.Uint8Array = SUint8Array;
const SUint8ClampedArray = Uint8ClampedArray;
exports.Uint8ClampedArray = SUint8ClampedArray;
const SUint16Array = Uint16Array;
exports.Uint16Array = SUint16Array;
const SUint32Array = Uint32Array;
exports.Uint32Array = SUint32Array;
const SencodeURIComponent = encodeURIComponent;
exports.encodeURIComponent = SencodeURIComponent;
const SMap = Map;
exports.Map = SMap;
const SSymbol = Symbol;
exports.Symbol = SSymbol;
const untouchedForEach = Array.prototype.forEach;
const untouchedIndexOf = Array.prototype.indexOf;
const untouchedJoin = Array.prototype.join;
const untouchedMap = Array.prototype.map;
const untouchedFlat = Array.prototype.flat;
const untouchedFilter = Array.prototype.filter;
const untouchedPush = Array.prototype.push;
const untouchedPop = Array.prototype.pop;
const untouchedSplice = Array.prototype.splice;
const untouchedSlice = Array.prototype.slice;
const untouchedSort = Array.prototype.sort;
const untouchedEvery = Array.prototype.every;
function extractForEach(instance) {
    try {
        return instance.forEach;
    }
    catch {
        return undefined;
    }
}
function extractIndexOf(instance) {
    try {
        return instance.indexOf;
    }
    catch {
        return undefined;
    }
}
function extractJoin(instance) {
    try {
        return instance.join;
    }
    catch {
        return undefined;
    }
}
function extractMap(instance) {
    try {
        return instance.map;
    }
    catch {
        return undefined;
    }
}
function extractFlat(instance) {
    try {
        return instance.flat;
    }
    catch {
        return undefined;
    }
}
function extractFilter(instance) {
    try {
        return instance.filter;
    }
    catch {
        return undefined;
    }
}
function extractPush(instance) {
    try {
        return instance.push;
    }
    catch {
        return undefined;
    }
}
function extractPop(instance) {
    try {
        return instance.pop;
    }
    catch {
        return undefined;
    }
}
function extractSplice(instance) {
    try {
        return instance.splice;
    }
    catch {
        return undefined;
    }
}
function extractSlice(instance) {
    try {
        return instance.slice;
    }
    catch {
        return undefined;
    }
}
function extractSort(instance) {
    try {
        return instance.sort;
    }
    catch {
        return undefined;
    }
}
function extractEvery(instance) {
    try {
        return instance.every;
    }
    catch {
        return undefined;
    }
}
function safeForEach(instance, fn) {
    if (extractForEach(instance) === untouchedForEach) {
        return instance.forEach(fn);
    }
    return (0, apply_js_1.safeApply)(untouchedForEach, instance, [fn]);
}
function safeIndexOf(instance, ...args) {
    if (extractIndexOf(instance) === untouchedIndexOf) {
        return instance.indexOf(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedIndexOf, instance, args);
}
function safeJoin(instance, ...args) {
    if (extractJoin(instance) === untouchedJoin) {
        return instance.join(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedJoin, instance, args);
}
function safeMap(instance, fn) {
    if (extractMap(instance) === untouchedMap) {
        return instance.map(fn);
    }
    return (0, apply_js_1.safeApply)(untouchedMap, instance, [fn]);
}
function safeFlat(instance, depth) {
    if (extractFlat(instance) === untouchedFlat) {
        [].flat();
        return instance.flat(depth);
    }
    return (0, apply_js_1.safeApply)(untouchedFlat, instance, [depth]);
}
function safeFilter(instance, predicate) {
    if (extractFilter(instance) === untouchedFilter) {
        return instance.filter(predicate);
    }
    return (0, apply_js_1.safeApply)(untouchedFilter, instance, [predicate]);
}
function safePush(instance, ...args) {
    if (extractPush(instance) === untouchedPush) {
        return instance.push(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedPush, instance, args);
}
function safePop(instance) {
    if (extractPop(instance) === untouchedPop) {
        return instance.pop();
    }
    return (0, apply_js_1.safeApply)(untouchedPop, instance, []);
}
function safeSplice(instance, ...args) {
    if (extractSplice(instance) === untouchedSplice) {
        return instance.splice(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedSplice, instance, args);
}
function safeSlice(instance, ...args) {
    if (extractSlice(instance) === untouchedSlice) {
        return instance.slice(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedSlice, instance, args);
}
function safeSort(instance, ...args) {
    if (extractSort(instance) === untouchedSort) {
        return instance.sort(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedSort, instance, args);
}
function safeEvery(instance, ...args) {
    if (extractEvery(instance) === untouchedEvery) {
        return instance.every(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedEvery, instance, args);
}
const untouchedGetTime = Date.prototype.getTime;
const untouchedToISOString = Date.prototype.toISOString;
function extractGetTime(instance) {
    try {
        return instance.getTime;
    }
    catch {
        return undefined;
    }
}
function extractToISOString(instance) {
    try {
        return instance.toISOString;
    }
    catch {
        return undefined;
    }
}
function safeGetTime(instance) {
    if (extractGetTime(instance) === untouchedGetTime) {
        return instance.getTime();
    }
    return (0, apply_js_1.safeApply)(untouchedGetTime, instance, []);
}
function safeToISOString(instance) {
    if (extractToISOString(instance) === untouchedToISOString) {
        return instance.toISOString();
    }
    return (0, apply_js_1.safeApply)(untouchedToISOString, instance, []);
}
const untouchedAdd = Set.prototype.add;
const untouchedHas = Set.prototype.has;
function extractAdd(instance) {
    try {
        return instance.add;
    }
    catch {
        return undefined;
    }
}
function extractHas(instance) {
    try {
        return instance.has;
    }
    catch (err) {
        return undefined;
    }
}
function safeAdd(instance, value) {
    if (extractAdd(instance) === untouchedAdd) {
        return instance.add(value);
    }
    return (0, apply_js_1.safeApply)(untouchedAdd, instance, [value]);
}
function safeHas(instance, value) {
    if (extractHas(instance) === untouchedHas) {
        return instance.has(value);
    }
    return (0, apply_js_1.safeApply)(untouchedHas, instance, [value]);
}
const untouchedSet = WeakMap.prototype.set;
const untouchedGet = WeakMap.prototype.get;
function extractSet(instance) {
    try {
        return instance.set;
    }
    catch (err) {
        return undefined;
    }
}
function extractGet(instance) {
    try {
        return instance.get;
    }
    catch (err) {
        return undefined;
    }
}
function safeSet(instance, key, value) {
    if (extractSet(instance) === untouchedSet) {
        return instance.set(key, value);
    }
    return (0, apply_js_1.safeApply)(untouchedSet, instance, [key, value]);
}
function safeGet(instance, key) {
    if (extractGet(instance) === untouchedGet) {
        return instance.get(key);
    }
    return (0, apply_js_1.safeApply)(untouchedGet, instance, [key]);
}
const untouchedMapSet = Map.prototype.set;
const untouchedMapGet = Map.prototype.get;
const untouchedMapHas = Map.prototype.has;
function extractMapSet(instance) {
    try {
        return instance.set;
    }
    catch (err) {
        return undefined;
    }
}
function extractMapGet(instance) {
    try {
        return instance.get;
    }
    catch (err) {
        return undefined;
    }
}
function extractMapHas(instance) {
    try {
        return instance.has;
    }
    catch (err) {
        return undefined;
    }
}
function safeMapSet(instance, key, value) {
    if (extractMapSet(instance) === untouchedMapSet) {
        return instance.set(key, value);
    }
    return (0, apply_js_1.safeApply)(untouchedMapSet, instance, [key, value]);
}
function safeMapGet(instance, key) {
    if (extractMapGet(instance) === untouchedMapGet) {
        return instance.get(key);
    }
    return (0, apply_js_1.safeApply)(untouchedMapGet, instance, [key]);
}
function safeMapHas(instance, key) {
    if (extractMapHas(instance) === untouchedMapHas) {
        return instance.has(key);
    }
    return (0, apply_js_1.safeApply)(untouchedMapHas, instance, [key]);
}
const untouchedSplit = String.prototype.split;
const untouchedStartsWith = String.prototype.startsWith;
const untouchedEndsWith = String.prototype.endsWith;
const untouchedSubstring = String.prototype.substring;
const untouchedToLowerCase = String.prototype.toLowerCase;
const untouchedToUpperCase = String.prototype.toUpperCase;
const untouchedPadStart = String.prototype.padStart;
const untouchedCharCodeAt = String.prototype.charCodeAt;
const untouchedNormalize = String.prototype.normalize;
const untouchedReplace = String.prototype.replace;
function extractSplit(instance) {
    try {
        return instance.split;
    }
    catch {
        return undefined;
    }
}
function extractStartsWith(instance) {
    try {
        return instance.startsWith;
    }
    catch {
        return undefined;
    }
}
function extractEndsWith(instance) {
    try {
        return instance.endsWith;
    }
    catch {
        return undefined;
    }
}
function extractSubstring(instance) {
    try {
        return instance.substring;
    }
    catch {
        return undefined;
    }
}
function extractToLowerCase(instance) {
    try {
        return instance.toLowerCase;
    }
    catch {
        return undefined;
    }
}
function extractToUpperCase(instance) {
    try {
        return instance.toUpperCase;
    }
    catch {
        return undefined;
    }
}
function extractPadStart(instance) {
    try {
        return instance.padStart;
    }
    catch {
        return undefined;
    }
}
function extractCharCodeAt(instance) {
    try {
        return instance.charCodeAt;
    }
    catch {
        return undefined;
    }
}
function extractNormalize(instance) {
    try {
        return instance.normalize;
    }
    catch (err) {
        return undefined;
    }
}
function extractReplace(instance) {
    try {
        return instance.replace;
    }
    catch {
        return undefined;
    }
}
function safeSplit(instance, ...args) {
    if (extractSplit(instance) === untouchedSplit) {
        return instance.split(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedSplit, instance, args);
}
function safeStartsWith(instance, ...args) {
    if (extractStartsWith(instance) === untouchedStartsWith) {
        return instance.startsWith(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedStartsWith, instance, args);
}
function safeEndsWith(instance, ...args) {
    if (extractEndsWith(instance) === untouchedEndsWith) {
        return instance.endsWith(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedEndsWith, instance, args);
}
function safeSubstring(instance, ...args) {
    if (extractSubstring(instance) === untouchedSubstring) {
        return instance.substring(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedSubstring, instance, args);
}
function safeToLowerCase(instance) {
    if (extractToLowerCase(instance) === untouchedToLowerCase) {
        return instance.toLowerCase();
    }
    return (0, apply_js_1.safeApply)(untouchedToLowerCase, instance, []);
}
function safeToUpperCase(instance) {
    if (extractToUpperCase(instance) === untouchedToUpperCase) {
        return instance.toUpperCase();
    }
    return (0, apply_js_1.safeApply)(untouchedToUpperCase, instance, []);
}
function safePadStart(instance, ...args) {
    if (extractPadStart(instance) === untouchedPadStart) {
        return instance.padStart(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedPadStart, instance, args);
}
function safeCharCodeAt(instance, index) {
    if (extractCharCodeAt(instance) === untouchedCharCodeAt) {
        return instance.charCodeAt(index);
    }
    return (0, apply_js_1.safeApply)(untouchedCharCodeAt, instance, [index]);
}
function safeNormalize(instance, form) {
    if (extractNormalize(instance) === untouchedNormalize) {
        return instance.normalize(form);
    }
    return (0, apply_js_1.safeApply)(untouchedNormalize, instance, [form]);
}
function safeReplace(instance, pattern, replacement) {
    if (extractReplace(instance) === untouchedReplace) {
        return instance.replace(pattern, replacement);
    }
    return (0, apply_js_1.safeApply)(untouchedReplace, instance, [pattern, replacement]);
}
const untouchedNumberToString = Number.prototype.toString;
function extractNumberToString(instance) {
    try {
        return instance.toString;
    }
    catch {
        return undefined;
    }
}
function safeNumberToString(instance, ...args) {
    if (extractNumberToString(instance) === untouchedNumberToString) {
        return instance.toString(...args);
    }
    return (0, apply_js_1.safeApply)(untouchedNumberToString, instance, args);
}
const untouchedHasOwnProperty = Object.prototype.hasOwnProperty;
const untouchedToString = Object.prototype.toString;
function safeHasOwnProperty(instance, v) {
    return (0, apply_js_1.safeApply)(untouchedHasOwnProperty, instance, [v]);
}
function safeToString(instance) {
    return (0, apply_js_1.safeApply)(untouchedToString, instance, []);
}
const untouchedErrorToString = Error.prototype.toString;
function safeErrorToString(instance) {
    return (0, apply_js_1.safeApply)(untouchedErrorToString, instance, []);
}
