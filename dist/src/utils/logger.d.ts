/**
 * @file utils/logger.ts
 * @module utils/logger
 * @description Structured logging utility for SCBE-AETHERMOORE
 * @version 3.0.0
 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error';
export interface LogContext {
    [key: string]: unknown;
}
export interface LogEntry {
    timestamp: string;
    level: LogLevel;
    message: string;
    context?: LogContext;
}
/**
 * Logger interface type
 */
export interface Logger {
    debug(message: string, context?: LogContext): void;
    info(message: string, context?: LogContext): void;
    warn(message: string, context?: LogContext): void;
    error(message: string, context?: LogContext): void;
    child(baseContext: LogContext): Logger;
}
/**
 * Logger instance for structured logging
 *
 * Usage:
 * ```typescript
 * import { logger } from './utils/logger';
 *
 * logger.info('Processing envelope', { kid: 'key-123', phase: 'encrypt' });
 * logger.error('Decryption failed', { error: err.message, envelope_id: '...' });
 * ```
 */
export declare const logger: Logger;
/**
 * Metrics-specific logger that outputs in a metrics-friendly format
 */
export declare const metricsLogger: {
    /**
     * Log a timing metric
     */
    timing(name: string, valueMs: number, tags?: Record<string, string | number | boolean>): void;
    /**
     * Log a counter increment
     */
    incr(name: string, value?: number, tags?: Record<string, string | number | boolean>): void;
};
//# sourceMappingURL=logger.d.ts.map