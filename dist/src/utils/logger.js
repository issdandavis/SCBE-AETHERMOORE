"use strict";
/**
 * @file utils/logger.ts
 * @module utils/logger
 * @description Structured logging utility for SCBE-AETHERMOORE
 * @version 3.0.0
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.metricsLogger = exports.logger = void 0;
/**
 * Log level priority for filtering
 */
const LOG_LEVELS = {
    debug: 0,
    info: 1,
    warn: 2,
    error: 3,
};
/**
 * Get configured log level from environment
 */
function getConfiguredLevel() {
    const envLevel = process.env.SCBE_LOG_LEVEL?.toLowerCase();
    if (envLevel && envLevel in LOG_LEVELS) {
        return envLevel;
    }
    return process.env.NODE_ENV === 'production' ? 'info' : 'debug';
}
/**
 * Format log entry for output
 */
function formatLogEntry(entry) {
    const contextStr = entry.context ? ` ${JSON.stringify(entry.context)}` : '';
    return `[${entry.timestamp}] ${entry.level.toUpperCase()} ${entry.message}${contextStr}`;
}
/**
 * Check if logging is enabled for this level
 */
function isLevelEnabled(level) {
    const configuredLevel = getConfiguredLevel();
    return LOG_LEVELS[level] >= LOG_LEVELS[configuredLevel];
}
/**
 * Create a log entry
 */
function createLogEntry(level, message, context) {
    return {
        timestamp: new Date().toISOString(),
        level,
        message,
        context,
    };
}
/**
 * Output log entry to appropriate stream
 */
function output(entry) {
    const formatted = formatLogEntry(entry);
    if (entry.level === 'error') {
        process.stderr.write(formatted + '\n');
    }
    else {
        process.stdout.write(formatted + '\n');
    }
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
exports.logger = {
    /**
     * Log debug level message
     */
    debug(message, context) {
        if (isLevelEnabled('debug')) {
            output(createLogEntry('debug', message, context));
        }
    },
    /**
     * Log info level message
     */
    info(message, context) {
        if (isLevelEnabled('info')) {
            output(createLogEntry('info', message, context));
        }
    },
    /**
     * Log warning level message
     */
    warn(message, context) {
        if (isLevelEnabled('warn')) {
            output(createLogEntry('warn', message, context));
        }
    },
    /**
     * Log error level message
     */
    error(message, context) {
        if (isLevelEnabled('error')) {
            output(createLogEntry('error', message, context));
        }
    },
    /**
     * Create a child logger with preset context
     */
    child(baseContext) {
        return {
            debug: (message, context) => exports.logger.debug(message, { ...baseContext, ...context }),
            info: (message, context) => exports.logger.info(message, { ...baseContext, ...context }),
            warn: (message, context) => exports.logger.warn(message, { ...baseContext, ...context }),
            error: (message, context) => exports.logger.error(message, { ...baseContext, ...context }),
            child: (additionalContext) => exports.logger.child({ ...baseContext, ...additionalContext }),
        };
    },
};
/**
 * Metrics-specific logger that outputs in a metrics-friendly format
 */
exports.metricsLogger = {
    /**
     * Log a timing metric
     */
    timing(name, valueMs, tags) {
        if (!isLevelEnabled('info'))
            return;
        const tagStr = tags
            ? Object.entries(tags)
                .map(([k, v]) => `${k}=${v}`)
                .join(' ')
            : '';
        process.stdout.write(`[metric] ${name}=${valueMs} ${tagStr}\n`.trim() + '\n');
    },
    /**
     * Log a counter increment
     */
    incr(name, value = 1, tags) {
        if (!isLevelEnabled('info'))
            return;
        const tagStr = tags
            ? Object.entries(tags)
                .map(([k, v]) => `${k}=${v}`)
                .join(' ')
            : '';
        process.stdout.write(`[metric] ${name}=${value} ${tagStr}\n`.trim() + '\n');
    },
};
//# sourceMappingURL=logger.js.map