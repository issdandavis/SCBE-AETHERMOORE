/**
 * @file crawl-frontier.ts
 * @module fleet/crawl-frontier
 * @layer Layer 5 (hyperbolic distance), Layer 12 (harmonic scaling)
 * @component URL Frontier for Multi-Agent Browser Crawling
 * @version 1.0.0
 *
 * Priority URL queue with:
 * - Duplicate detection (Set-based, upgradeable to Bloom filter)
 * - Per-domain rate limiting (prevents single-domain storms)
 * - Depth-based priority decay (deeper pages = lower priority)
 * - Domain risk classification (integrates with browser evaluator)
 * - Agent claim/release protocol (prevents double-crawling)
 *
 * Priority formula:
 *   P(url) = basePriority * φ^(-depth) * domainBoost
 *
 * where φ = golden ratio, depth = link distance from seed URLs,
 * and domainBoost ∈ [0.1, 2.0] based on domain safety score.
 */
/** Status of a URL in the frontier */
export type URLStatus = 'queued' | 'claimed' | 'crawling' | 'completed' | 'failed' | 'blocked';
/** A URL entry in the frontier */
export interface FrontierEntry {
    /** Canonical URL */
    readonly url: string;
    /** Domain extracted from URL */
    readonly domain: string;
    /** Link depth from seed URLs */
    readonly depth: number;
    /** Computed priority (higher = crawl sooner) */
    priority: number;
    /** Current status */
    status: URLStatus;
    /** Agent that claimed this URL */
    claimedBy?: string;
    /** When the URL was claimed */
    claimedAt?: number;
    /** When crawling completed */
    completedAt?: number;
    /** Parent URL that discovered this one */
    readonly parentUrl?: string;
    /** Error message if failed */
    error?: string;
    /** Number of retry attempts */
    retries: number;
    /** Maximum retries allowed */
    readonly maxRetries: number;
    /** Timestamp added to frontier */
    readonly addedAt: number;
}
/** Frontier configuration */
export interface FrontierConfig {
    /** Maximum URLs in the frontier */
    maxSize: number;
    /** Maximum crawl depth from seed URLs */
    maxDepth: number;
    /** Maximum retries per URL */
    maxRetries: number;
    /** Per-domain rate limit (minimum ms between crawls to same domain) */
    domainRateLimitMs: number;
    /** Claim timeout (ms) — reclaim if agent doesn't complete in time */
    claimTimeoutMs: number;
    /** Blocked domain patterns (regex strings) */
    blockedDomains: string[];
    /** Seed URL priority boost */
    seedPriorityBoost: number;
}
/** Default frontier configuration */
export declare const DEFAULT_FRONTIER_CONFIG: FrontierConfig;
/** Frontier statistics */
export interface FrontierStats {
    totalAdded: number;
    totalCompleted: number;
    totalFailed: number;
    totalBlocked: number;
    queued: number;
    claimed: number;
    crawling: number;
    uniqueDomains: number;
    averageDepth: number;
}
/** Extract domain from URL */
export declare function extractDomain(url: string): string;
/** Canonicalize URL (remove fragments, trailing slashes, normalize protocol) */
export declare function canonicalizeUrl(url: string): string;
/**
 * Priority URL frontier for multi-agent browser crawling.
 *
 * Agents claim URLs from the frontier, crawl them, and report
 * back discovered URLs and results. The frontier handles dedup,
 * priority, rate limiting, and stale claim recovery.
 *
 * Usage:
 * ```typescript
 * const frontier = new CrawlFrontier();
 * frontier.addSeedUrls(['https://example.com']);
 *
 * // Agent claims next URL
 * const entry = frontier.claim('agent-1');
 * if (entry) {
 *   // ... crawl the URL ...
 *   frontier.complete(entry.url, 'agent-1', ['https://example.com/page1']);
 * }
 * ```
 */
export declare class CrawlFrontier {
    private config;
    private entries;
    private seen;
    private domainLastCrawled;
    private blockedPatterns;
    private stats;
    constructor(config?: Partial<FrontierConfig>);
    /**
     * Add seed URLs to the frontier (depth 0, boosted priority).
     */
    addSeedUrls(urls: string[]): number;
    /**
     * Add a discovered URL to the frontier.
     *
     * @param url - URL to add
     * @param depth - Link depth from seed
     * @param parentUrl - URL that discovered this one
     * @param priorityBoost - Optional priority multiplier
     * @returns true if added, false if duplicate/blocked/full
     */
    addUrl(url: string, depth: number, parentUrl?: string, priorityBoost?: number): boolean;
    /**
     * Claim the next URL for crawling.
     * Returns the highest-priority queued URL whose domain isn't rate-limited.
     *
     * @param agentId - Agent claiming the URL
     * @returns FrontierEntry or null if nothing available
     */
    claim(agentId: string): FrontierEntry | null;
    /**
     * Mark a URL as being actively crawled.
     */
    markCrawling(url: string, agentId: string): boolean;
    /**
     * Mark a URL as completed and submit discovered URLs.
     *
     * @param url - Completed URL
     * @param agentId - Agent that crawled it
     * @param discoveredUrls - URLs found on the page
     * @returns Number of new URLs added to frontier
     */
    complete(url: string, agentId: string, discoveredUrls?: string[]): number;
    /**
     * Mark a URL as failed. Retries if under limit.
     *
     * @param url - Failed URL
     * @param agentId - Agent that failed
     * @param error - Error description
     * @returns true if requeued for retry, false if permanently failed
     */
    fail(url: string, agentId: string, error: string): boolean;
    /**
     * Block a domain at runtime.
     */
    blockDomain(pattern: string): void;
    /**
     * Release a claimed URL back to the queue.
     */
    release(url: string, agentId: string): boolean;
    /**
     * Get a specific entry.
     */
    getEntry(url: string): FrontierEntry | undefined;
    /**
     * Get all entries with a given status.
     */
    getByStatus(status: URLStatus): FrontierEntry[];
    /**
     * Check if a URL has been seen.
     */
    hasSeen(url: string): boolean;
    /**
     * Get frontier statistics.
     */
    getStats(): FrontierStats;
    /**
     * Get the total size of the frontier.
     */
    get size(): number;
    /**
     * Check if the frontier has queued URLs.
     */
    get hasWork(): boolean;
    private isBlocked;
    private recoverStaleClaims;
    private updateStats;
}
//# sourceMappingURL=crawl-frontier.d.ts.map