"use strict";
/**
 * Six Tongues GeoSeal Integration
 *
 * Provides TypeScript wrapper for the Python six-tongues-geoseal CLI
 * Handles process spawning, error handling, and data streaming
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.SixTonguesIntegration = void 0;
exports.getSixTongues = getSixTongues;
exports.encode = encode;
exports.decode = decode;
exports.geoseal = geoseal;
const child_process_1 = require("child_process");
const fs_1 = require("fs");
const path_1 = __importDefault(require("path"));
class SixTonguesIntegration {
    config;
    cliReady = false;
    constructor(config = {}) {
        this.config = {
            pythonPath: config.pythonPath || 'python3',
            cliPath: config.cliPath || path_1.default.join(__dirname, '../../packages/six-tongues-geoseal/aethermoore.py'),
            timeout: config.timeout || 30000,
        };
    }
    /**
     * Check if Python and numpy are available
     */
    async checkEnvironment() {
        const checks = {
            python: false,
            numpy: false,
            cli: false,
        };
        try {
            // Check Python
            await this.execCommand(this.config.pythonPath, ['--version']);
            checks.python = true;
            // Check numpy
            const numpyCheck = await this.execCommand(this.config.pythonPath, ['-c', 'import numpy']);
            checks.numpy = numpyCheck.success;
            // Check CLI file exists
            try {
                await fs_1.promises.access(this.config.cliPath);
                checks.cli = true;
            }
            catch {
                checks.cli = false;
            }
        }
        catch (error) {
            // Python not available
        }
        this.cliReady = checks.python && checks.numpy && checks.cli;
        return checks;
    }
    /**
     * Initialize and verify the integration
     */
    async initialize() {
        const checks = await this.checkEnvironment();
        if (!checks.python) {
            throw new Error('Python 3 is not available. Please install Python 3.x');
        }
        if (!checks.numpy) {
            throw new Error('numpy is not installed. Run: pip install numpy');
        }
        if (!checks.cli) {
            throw new Error(`Six Tongues CLI not found at: ${this.config.cliPath}`);
        }
        return this.cliReady;
    }
    /**
     * Encode text using Six Tongues tokenization
     */
    async encode(options) {
        if (!this.cliReady) {
            await this.initialize();
        }
        const args = ['encode', '--text', options.text];
        if (options.context) {
            args.push('--context', options.context);
        }
        return this.runCLI(args);
    }
    /**
     * Decode text from Six Tongues encoding
     */
    async decode(options) {
        if (!this.cliReady) {
            await this.initialize();
        }
        const args = ['decode', '--encoded', options.encodedText];
        if (options.context) {
            args.push('--context', options.context);
        }
        return this.runCLI(args);
    }
    /**
     * Apply GeoSeal context-aware encryption
     */
    async geoseal(options) {
        if (!this.cliReady) {
            await this.initialize();
        }
        const args = ['geoseal', '--data', options.data];
        if (options.location) {
            args.push('--lat', options.location.lat.toString());
            args.push('--lon', options.location.lon.toString());
        }
        if (options.timestamp) {
            args.push('--timestamp', options.timestamp.toString());
        }
        return this.runCLI(args);
    }
    /**
     * Execute Python CLI with arguments
     */
    async runCLI(args) {
        return this.execCommand(this.config.pythonPath, [this.config.cliPath, ...args]);
    }
    /**
     * Execute command and capture output
     */
    async execCommand(command, args) {
        return new Promise((resolve) => {
            let stdout = '';
            let stderr = '';
            const proc = (0, child_process_1.spawn)(command, args, {
                stdio: ['pipe', 'pipe', 'pipe'],
            });
            const timeout = setTimeout(() => {
                proc.kill();
                resolve({
                    success: false,
                    error: 'Command timeout',
                    stderr: 'Process killed due to timeout',
                });
            }, this.config.timeout);
            proc.stdout?.on('data', (data) => {
                stdout += data.toString();
            });
            proc.stderr?.on('data', (data) => {
                stderr += data.toString();
            });
            proc.on('error', (error) => {
                clearTimeout(timeout);
                resolve({
                    success: false,
                    error: error.message,
                    stderr,
                });
            });
            proc.on('close', (code) => {
                clearTimeout(timeout);
                if (code === 0) {
                    try {
                        const data = JSON.parse(stdout);
                        resolve({
                            success: true,
                            data,
                        });
                    }
                    catch {
                        resolve({
                            success: true,
                            data: stdout.trim(),
                        });
                    }
                }
                else {
                    resolve({
                        success: false,
                        error: `Process exited with code ${code}`,
                        stderr,
                    });
                }
            });
        });
    }
}
exports.SixTonguesIntegration = SixTonguesIntegration;
/**
 * Create a singleton instance for convenience
 */
let defaultInstance = null;
function getSixTongues(config) {
    if (!defaultInstance) {
        defaultInstance = new SixTonguesIntegration(config);
    }
    return defaultInstance;
}
/**
 * Convenience functions using default instance
 */
async function encode(text, context) {
    return getSixTongues().encode({ text, context });
}
async function decode(encodedText, context) {
    return getSixTongues().decode({ encodedText, context });
}
async function geoseal(data, location, timestamp) {
    return getSixTongues().geoseal({ data, location, timestamp });
}
//# sourceMappingURL=six-tongues.js.map