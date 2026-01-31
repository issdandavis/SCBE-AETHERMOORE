/**
 * Async Non-Blocking Vector Storage for RWP2
 * ==========================================
 *
 * Provides fire-and-forget vector storage that doesn't block
 * the critical RWP v2 signing path.
 *
 * Performance:
 * - Zero added latency to RWP v2 critical path
 * - Background processing with error logging
 * - Eventual consistency for vector index updates
 *
 * @module vector/async-storage
 * @version 1.0.0
 * @since 2026-01-29
 */

import { RWP2MultiEnvelope, Keyring, TongueID } from '../spiralverse/types';
import { signRoundtable } from '../spiralverse/rwp';
import { embed } from './embedder';
import { embedWithCache, HotCache, getDefaultHotCache } from './hot-cache';
import { getIndex } from './vector-index';

/**
 * Simple logger interface
 */
interface Logger {
  error: (message: string, error?: unknown) => void;
  warn: (message: string, details?: unknown) => void;
  info: (message: string, details?: unknown) => void;
  debug: (message: string, details?: unknown) => void;
}

/**
 * Default console logger
 */
const defaultLogger: Logger = {
  error: (message: string, error?: unknown) => console.error(`[vector] ${message}`, error),
  warn: (message: string, details?: unknown) => console.warn(`[vector] ${message}`, details),
  info: (message: string, details?: unknown) => console.info(`[vector] ${message}`, details),
  debug: (message: string, details?: unknown) => console.debug(`[vector] ${message}`, details),
};

/**
 * Configured logger instance
 */
let logger: Logger = defaultLogger;

/**
 * Set custom logger
 *
 * @param customLogger - Logger instance to use
 */
export function setLogger(customLogger: Logger): void {
  logger = customLogger;
}

/**
 * Async vector storage options
 */
export interface AsyncStorageOptions {
  /** Use hot cache for embeddings (default: true) */
  useCache?: boolean;
  /** Custom hot cache instance */
  cache?: HotCache;
  /** Include payload in embedding (default: false, uses AAD only) */
  includePayload?: boolean;
}

/**
 * Embed and store a vector asynchronously (non-blocking)
 *
 * Fire-and-forget pattern that doesn't block the caller.
 * Errors are logged but don't propagate.
 *
 * @param tongue - Tongue/namespace for the index
 * @param aad - Additional authenticated data (used as ID and embedding source)
 * @param docId - Document ID for metadata
 * @param options - Storage options
 *
 * @example
 * ```typescript
 * // Fire-and-forget - returns immediately
 * embedAndStoreAsync('ko', 'agent-123', 'doc-456');
 * ```
 */
export function embedAndStoreAsync(
  tongue: string,
  aad: string,
  docId: string,
  options: AsyncStorageOptions = {}
): void {
  const { useCache = true, cache = getDefaultHotCache() } = options;

  // Fire-and-forget with error handling
  (async () => {
    try {
      const index = getIndex(tongue, { dimension: 384 });

      let vector: Float32Array;
      if (useCache) {
        vector = await embedWithCache(aad, () => embed(aad), cache);
      } else {
        vector = await embed(aad);
      }

      index.add(aad, vector, { docId, timestamp: Date.now() });
      logger.debug(`Stored vector for ${tongue}:${aad}`);
    } catch (err) {
      logger.error('Vector storage failed', err);
    }
  })();
}

/**
 * Sign RWP2 envelope with async vector storage
 *
 * Signs the envelope immediately and fires off vector storage
 * in the background without blocking.
 *
 * @param payload - Payload to sign
 * @param primaryTongue - Primary tongue for the envelope
 * @param aad - Additional authenticated data
 * @param keyring - HMAC keys for signing
 * @param signingTongues - Tongues to sign with
 * @param options - Storage options
 * @returns Signed envelope (returns immediately)
 *
 * @example
 * ```typescript
 * const signed = signRWP2WithVectorAsync(
 *   { action: 'deploy' },
 *   'ko',
 *   'agent-123',
 *   keyring,
 *   ['ko', 'ru']
 * );
 * // Vector storage happens in background
 * ```
 */
export function signRWP2WithVectorAsync<T = any>(
  payload: T,
  primaryTongue: TongueID,
  aad: string,
  keyring: Keyring,
  signingTongues: TongueID[],
  options: AsyncStorageOptions = {}
): RWP2MultiEnvelope<T> {
  // Sign immediately (blocking)
  const signed = signRoundtable(payload, primaryTongue, aad, keyring, signingTongues);

  // Fire-and-forget vector storage (non-blocking)
  const docId = `${signed.ts}-${signed.nonce}`;
  embedAndStoreAsync(primaryTongue, aad, docId, options);

  return signed; // Return instantly
}

/**
 * Batch sign multiple envelopes with async vector storage
 *
 * Signs all envelopes immediately and queues vector storage
 * for background processing.
 *
 * @param envelopes - Array of envelope specifications
 * @param keyring - HMAC keys for signing
 * @param options - Storage options
 * @returns Array of signed envelopes
 *
 * @example
 * ```typescript
 * const signed = batchSignWithVectorAsync([
 *   { payload: { a: 1 }, primaryTongue: 'ko', aad: 'agent-1', signingTongues: ['ko'] },
 *   { payload: { b: 2 }, primaryTongue: 'av', aad: 'agent-2', signingTongues: ['av'] },
 * ], keyring);
 * ```
 */
export function batchSignWithVectorAsync<T = any>(
  envelopes: Array<{
    payload: T;
    primaryTongue: TongueID;
    aad: string;
    signingTongues: TongueID[];
  }>,
  keyring: Keyring,
  options: AsyncStorageOptions = {}
): RWP2MultiEnvelope<T>[] {
  const results: RWP2MultiEnvelope<T>[] = [];

  for (const env of envelopes) {
    const signed = signRWP2WithVectorAsync(
      env.payload,
      env.primaryTongue,
      env.aad,
      keyring,
      env.signingTongues,
      options
    );
    results.push(signed);
  }

  return results;
}

/**
 * Search for similar envelopes by AAD
 *
 * Finds envelopes with similar AAD strings using vector similarity search.
 *
 * @param tongue - Tongue/namespace to search
 * @param aad - AAD to find similar matches for
 * @param k - Number of results (default: 10)
 * @returns Promise resolving to search results
 *
 * @example
 * ```typescript
 * const similar = await findSimilarEnvelopes('ko', 'agent-123', 5);
 * for (const result of similar) {
 *   console.log(`Similar: ${result.id}, Distance: ${result.distance}`);
 * }
 * ```
 */
export async function findSimilarEnvelopes(
  tongue: string,
  aad: string,
  k: number = 10
): Promise<Array<{ id: string; distance: number; metadata?: Record<string, unknown> }>> {
  const index = getIndex(tongue, { dimension: 384 });
  const vector = await embed(aad);
  return index.search(vector, k);
}

/**
 * Preload embeddings for a list of AADs
 *
 * Useful for warming up the cache before a batch operation.
 *
 * @param aads - AAD strings to preload
 * @param cache - Hot cache instance (default: global cache)
 *
 * @example
 * ```typescript
 * await preloadEmbeddings(['agent-1', 'agent-2', 'agent-3']);
 * // Subsequent lookups will be cached
 * ```
 */
export async function preloadEmbeddings(
  aads: string[],
  cache: HotCache = getDefaultHotCache()
): Promise<void> {
  // Import batch embedding
  const { embedBatch } = await import('./embedder');

  // Filter out already cached AADs
  const uncached = aads.filter(aad => !cache.has(aad));

  if (uncached.length === 0) {
    return;
  }

  // Batch embed all uncached AADs
  const vectors = await embedBatch(uncached);

  // Store in cache
  for (let i = 0; i < uncached.length; i++) {
    cache.set(uncached[i], vectors[i]);
  }

  logger.debug(`Preloaded ${uncached.length} embeddings`);
}
