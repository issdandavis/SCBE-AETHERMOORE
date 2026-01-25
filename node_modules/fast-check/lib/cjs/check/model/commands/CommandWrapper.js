"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.CommandWrapper = void 0;
const stringify_js_1 = require("../../../utils/stringify.js");
const symbols_js_1 = require("../../symbols.js");
class CommandWrapper {
    constructor(cmd) {
        this.cmd = cmd;
        this.hasRan = false;
        if ((0, stringify_js_1.hasToStringMethod)(cmd)) {
            const method = cmd[stringify_js_1.toStringMethod];
            this[stringify_js_1.toStringMethod] = function toStringMethod() {
                return method.call(cmd);
            };
        }
        if ((0, stringify_js_1.hasAsyncToStringMethod)(cmd)) {
            const method = cmd[stringify_js_1.asyncToStringMethod];
            this[stringify_js_1.asyncToStringMethod] =
                function asyncToStringMethod() {
                    return method.call(cmd);
                };
        }
    }
    check(m) {
        return this.cmd.check(m);
    }
    run(m, r) {
        this.hasRan = true;
        return this.cmd.run(m, r);
    }
    clone() {
        if ((0, symbols_js_1.hasCloneMethod)(this.cmd))
            return new CommandWrapper(this.cmd[symbols_js_1.cloneMethod]());
        return new CommandWrapper(this.cmd);
    }
    toString() {
        return this.cmd.toString();
    }
}
exports.CommandWrapper = CommandWrapper;
