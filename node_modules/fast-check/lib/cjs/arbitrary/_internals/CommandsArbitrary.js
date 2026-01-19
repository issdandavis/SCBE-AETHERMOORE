"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CommandsArbitrary = void 0;
const Arbitrary_js_1 = require("../../check/arbitrary/definition/Arbitrary.js");
const Value_js_1 = require("../../check/arbitrary/definition/Value.js");
const CommandsIterable_js_1 = require("../../check/model/commands/CommandsIterable.js");
const CommandWrapper_js_1 = require("../../check/model/commands/CommandWrapper.js");
const ReplayPath_js_1 = require("../../check/model/ReplayPath.js");
const LazyIterableIterator_js_1 = require("../../stream/LazyIterableIterator.js");
const Stream_js_1 = require("../../stream/Stream.js");
const oneof_js_1 = require("../oneof.js");
const RestrictedIntegerArbitraryBuilder_js_1 = require("./builders/RestrictedIntegerArbitraryBuilder.js");
class CommandsArbitrary extends Arbitrary_js_1.Arbitrary {
    constructor(commandArbs, maxGeneratedCommands, maxCommands, sourceReplayPath, disableReplayLog) {
        super();
        this.sourceReplayPath = sourceReplayPath;
        this.disableReplayLog = disableReplayLog;
        this.oneCommandArb = (0, oneof_js_1.oneof)(...commandArbs).map((c) => new CommandWrapper_js_1.CommandWrapper(c));
        this.lengthArb = (0, RestrictedIntegerArbitraryBuilder_js_1.restrictedIntegerArbitraryBuilder)(0, maxGeneratedCommands, maxCommands);
        this.replayPath = [];
        this.replayPathPosition = 0;
    }
    metadataForReplay() {
        return this.disableReplayLog ? '' : `replayPath=${JSON.stringify(ReplayPath_js_1.ReplayPath.stringify(this.replayPath))}`;
    }
    buildValueFor(items, shrunkOnce) {
        const commands = items.map((item) => item.value_);
        const context = { shrunkOnce, items };
        return new Value_js_1.Value(new CommandsIterable_js_1.CommandsIterable(commands, () => this.metadataForReplay()), context);
    }
    generate(mrng) {
        const size = this.lengthArb.generate(mrng, undefined);
        const sizeValue = size.value;
        const items = Array(sizeValue);
        for (let idx = 0; idx !== sizeValue; ++idx) {
            const item = this.oneCommandArb.generate(mrng, undefined);
            items[idx] = item;
        }
        this.replayPathPosition = 0;
        return this.buildValueFor(items, false);
    }
    canShrinkWithoutContext(value) {
        return false;
    }
    filterOnExecution(itemsRaw) {
        const items = [];
        for (const c of itemsRaw) {
            if (c.value_.hasRan) {
                this.replayPath.push(true);
                items.push(c);
            }
            else
                this.replayPath.push(false);
        }
        return items;
    }
    filterOnReplay(itemsRaw) {
        return itemsRaw.filter((c, idx) => {
            const state = this.replayPath[this.replayPathPosition + idx];
            if (state === undefined)
                throw new Error(`Too short replayPath`);
            if (!state && c.value_.hasRan)
                throw new Error(`Mismatch between replayPath and real execution`);
            return state;
        });
    }
    filterForShrinkImpl(itemsRaw) {
        if (this.replayPathPosition === 0) {
            this.replayPath = this.sourceReplayPath !== null ? ReplayPath_js_1.ReplayPath.parse(this.sourceReplayPath) : [];
        }
        const items = this.replayPathPosition < this.replayPath.length
            ? this.filterOnReplay(itemsRaw)
            : this.filterOnExecution(itemsRaw);
        this.replayPathPosition += itemsRaw.length;
        return items;
    }
    shrink(_value, context) {
        if (context === undefined) {
            return Stream_js_1.Stream.nil();
        }
        const safeContext = context;
        const shrunkOnce = safeContext.shrunkOnce;
        const itemsRaw = safeContext.items;
        const items = this.filterForShrinkImpl(itemsRaw);
        if (items.length === 0) {
            return Stream_js_1.Stream.nil();
        }
        const rootShrink = shrunkOnce
            ? Stream_js_1.Stream.nil()
            : new Stream_js_1.Stream([[]][Symbol.iterator]());
        const nextShrinks = [];
        for (let numToKeep = 0; numToKeep !== items.length; ++numToKeep) {
            nextShrinks.push((0, LazyIterableIterator_js_1.makeLazy)(() => {
                const fixedStart = items.slice(0, numToKeep);
                return this.lengthArb
                    .shrink(items.length - 1 - numToKeep, undefined)
                    .map((l) => fixedStart.concat(items.slice(items.length - (l.value + 1))));
            }));
        }
        for (let itemAt = 0; itemAt !== items.length; ++itemAt) {
            nextShrinks.push((0, LazyIterableIterator_js_1.makeLazy)(() => this.oneCommandArb
                .shrink(items[itemAt].value_, items[itemAt].context)
                .map((v) => items.slice(0, itemAt).concat([v], items.slice(itemAt + 1)))));
        }
        return rootShrink.join(...nextShrinks).map((shrinkables) => {
            return this.buildValueFor(shrinkables.map((c) => new Value_js_1.Value(c.value_.clone(), c.context)), true);
        });
    }
}
exports.CommandsArbitrary = CommandsArbitrary;
