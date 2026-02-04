/**
 * Six Tongues GeoSeal Integration
 *
 * Provides TypeScript wrapper for the Python six-tongues-geoseal CLI
 * Handles process spawning, error handling, and data streaming
 */

import { spawn, ChildProcess } from 'child_process';
import { promises as fs } from 'fs';
import path from 'path';

export interface SixTonguesConfig {
  pythonPath?: string;
  cliPath?: string;
  timeout?: number;
}

export interface EncodeOptions {
  text: string;
  context?: string;
}

export interface DecodeOptions {
  encodedText: string;
  context?: string;
}

export interface GeoSealOptions {
  data: string;
  location?: { lat: number; lon: number };
  timestamp?: number;
}

export interface SixTonguesResult {
  success: boolean;
  data?: any;
  error?: string;
  stderr?: string;
}

export class SixTonguesIntegration {
  private config: Required<SixTonguesConfig>;
  private cliReady: boolean = false;

  constructor(config: SixTonguesConfig = {}) {
    this.config = {
      pythonPath: config.pythonPath || 'python3',
      cliPath:
        config.cliPath || path.join(__dirname, '../../packages/six-tongues-geoseal/aethermoore.py'),
      timeout: config.timeout || 30000,
    };
  }

  /**
   * Check if Python and numpy are available
   */
  async checkEnvironment(): Promise<{ python: boolean; numpy: boolean; cli: boolean }> {
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
        await fs.access(this.config.cliPath);
        checks.cli = true;
      } catch {
        checks.cli = false;
      }
    } catch (error) {
      // Python not available
    }

    this.cliReady = checks.python && checks.numpy && checks.cli;
    return checks;
  }

  /**
   * Initialize and verify the integration
   */
  async initialize(): Promise<boolean> {
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
  async encode(options: EncodeOptions): Promise<SixTonguesResult> {
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
  async decode(options: DecodeOptions): Promise<SixTonguesResult> {
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
  async geoseal(options: GeoSealOptions): Promise<SixTonguesResult> {
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
  private async runCLI(args: string[]): Promise<SixTonguesResult> {
    return this.execCommand(this.config.pythonPath, [this.config.cliPath, ...args]);
  }

  /**
   * Execute command and capture output
   */
  private async execCommand(command: string, args: string[]): Promise<SixTonguesResult> {
    return new Promise((resolve) => {
      let stdout = '';
      let stderr = '';

      const proc: ChildProcess = spawn(command, args, {
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
          } catch {
            resolve({
              success: true,
              data: stdout.trim(),
            });
          }
        } else {
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

/**
 * Create a singleton instance for convenience
 */
let defaultInstance: SixTonguesIntegration | null = null;

export function getSixTongues(config?: SixTonguesConfig): SixTonguesIntegration {
  if (!defaultInstance) {
    defaultInstance = new SixTonguesIntegration(config);
  }
  return defaultInstance;
}

/**
 * Convenience functions using default instance
 */
export async function encode(text: string, context?: string): Promise<SixTonguesResult> {
  return getSixTongues().encode({ text, context });
}

export async function decode(encodedText: string, context?: string): Promise<SixTonguesResult> {
  return getSixTongues().decode({ encodedText, context });
}

export async function geoseal(
  data: string,
  location?: { lat: number; lon: number },
  timestamp?: number
): Promise<SixTonguesResult> {
  return getSixTongues().geoseal({ data, location, timestamp });
}
