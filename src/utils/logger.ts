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
 * Log level priority for filtering
 */
const LOG_LEVELS: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
};

/**
 * Get configured log level from environment
 */
function getConfiguredLevel(): LogLevel {
  const envLevel = process.env.SCBE_LOG_LEVEL?.toLowerCase();
  if (envLevel && envLevel in LOG_LEVELS) {
    return envLevel as LogLevel;
  }
  return process.env.NODE_ENV === 'production' ? 'info' : 'debug';
}

/**
 * Format log entry for output
 */
function formatLogEntry(entry: LogEntry): string {
  const contextStr = entry.context ? ` ${JSON.stringify(entry.context)}` : '';
  return `[${entry.timestamp}] ${entry.level.toUpperCase()} ${entry.message}${contextStr}`;
}

/**
 * Check if logging is enabled for this level
 */
function isLevelEnabled(level: LogLevel): boolean {
  const configuredLevel = getConfiguredLevel();
  return LOG_LEVELS[level] >= LOG_LEVELS[configuredLevel];
}

/**
 * Create a log entry
 */
function createLogEntry(level: LogLevel, message: string, context?: LogContext): LogEntry {
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
function output(entry: LogEntry): void {
  const formatted = formatLogEntry(entry);
  if (entry.level === 'error') {
    process.stderr.write(formatted + '\n');
  } else {
    process.stdout.write(formatted + '\n');
  }
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
export const logger: Logger = {
  /**
   * Log debug level message
   */
  debug(message: string, context?: LogContext): void {
    if (isLevelEnabled('debug')) {
      output(createLogEntry('debug', message, context));
    }
  },

  /**
   * Log info level message
   */
  info(message: string, context?: LogContext): void {
    if (isLevelEnabled('info')) {
      output(createLogEntry('info', message, context));
    }
  },

  /**
   * Log warning level message
   */
  warn(message: string, context?: LogContext): void {
    if (isLevelEnabled('warn')) {
      output(createLogEntry('warn', message, context));
    }
  },

  /**
   * Log error level message
   */
  error(message: string, context?: LogContext): void {
    if (isLevelEnabled('error')) {
      output(createLogEntry('error', message, context));
    }
  },

  /**
   * Create a child logger with preset context
   */
  child(baseContext: LogContext): Logger {
    return {
      debug: (message: string, context?: LogContext) =>
        logger.debug(message, { ...baseContext, ...context }),
      info: (message: string, context?: LogContext) =>
        logger.info(message, { ...baseContext, ...context }),
      warn: (message: string, context?: LogContext) =>
        logger.warn(message, { ...baseContext, ...context }),
      error: (message: string, context?: LogContext) =>
        logger.error(message, { ...baseContext, ...context }),
      child: (additionalContext: LogContext) =>
        logger.child({ ...baseContext, ...additionalContext }),
    };
  },
};

/**
 * Metrics-specific logger that outputs in a metrics-friendly format
 */
export const metricsLogger = {
  /**
   * Log a timing metric
   */
  timing(name: string, valueMs: number, tags?: Record<string, string | number | boolean>): void {
    if (!isLevelEnabled('info')) return;
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
  incr(name: string, value = 1, tags?: Record<string, string | number | boolean>): void {
    if (!isLevelEnabled('info')) return;
    const tagStr = tags
      ? Object.entries(tags)
          .map(([k, v]) => `${k}=${v}`)
          .join(' ')
      : '';
    process.stdout.write(`[metric] ${name}=${value} ${tagStr}\n`.trim() + '\n');
  },
};
