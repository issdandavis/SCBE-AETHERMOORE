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

// ═══════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════

const PHI = 1.6180339887498949;

/** Status of a URL in the frontier */
export type URLStatus =
  | 'queued'
  | 'claimed'
  | 'crawling'
  | 'completed'
  | 'failed'
  | 'blocked';

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
export const DEFAULT_FRONTIER_CONFIG: FrontierConfig = {
  maxSize: 100_000,
  maxDepth: 5,
  maxRetries: 2,
  domainRateLimitMs: 2_000,
  claimTimeoutMs: 60_000,
  blockedDomains: [],
  seedPriorityBoost: 10.0,
};

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

// ═══════════════════════════════════════════════════════════════
// URL Utilities
// ═══════════════════════════════════════════════════════════════

/** Extract domain from URL */
export function extractDomain(url: string): string {
  try {
    const parsed = new URL(url);
    return parsed.hostname;
  } catch {
    // Fallback: extract between :// and first /
    const match = url.match(/^(?:https?:\/\/)?([^/?#]+)/);
    return match ? match[1] : url;
  }
}

/** Canonicalize URL (remove fragments, trailing slashes, normalize protocol) */
export function canonicalizeUrl(url: string): string {
  try {
    const parsed = new URL(url);
    // Remove fragment
    parsed.hash = '';
    // Normalize path (remove trailing slash unless root)
    if (parsed.pathname.length > 1 && parsed.pathname.endsWith('/')) {
      parsed.pathname = parsed.pathname.slice(0, -1);
    }
    // Sort query parameters
    const params = new URLSearchParams(parsed.search);
    const sorted = new URLSearchParams([...params.entries()].sort());
    parsed.search = sorted.toString();
    return parsed.toString();
  } catch {
    return url;
  }
}

// ═══════════════════════════════════════════════════════════════
// CrawlFrontier
// ═══════════════════════════════════════════════════════════════

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
export class CrawlFrontier {
  private config: FrontierConfig;
  private entries: Map<string, FrontierEntry> = new Map();
  private seen: Set<string> = new Set();
  private domainLastCrawled: Map<string, number> = new Map();
  private blockedPatterns: RegExp[];
  private stats: FrontierStats = {
    totalAdded: 0,
    totalCompleted: 0,
    totalFailed: 0,
    totalBlocked: 0,
    queued: 0,
    claimed: 0,
    crawling: 0,
    uniqueDomains: 0,
    averageDepth: 0,
  };

  constructor(config: Partial<FrontierConfig> = {}) {
    this.config = { ...DEFAULT_FRONTIER_CONFIG, ...config };
    this.blockedPatterns = this.config.blockedDomains.map((d) => new RegExp(d, 'i'));
  }

  /**
   * Add seed URLs to the frontier (depth 0, boosted priority).
   */
  addSeedUrls(urls: string[]): number {
    let added = 0;
    for (const url of urls) {
      if (this.addUrl(url, 0, undefined, this.config.seedPriorityBoost)) {
        added++;
      }
    }
    return added;
  }

  /**
   * Add a discovered URL to the frontier.
   *
   * @param url - URL to add
   * @param depth - Link depth from seed
   * @param parentUrl - URL that discovered this one
   * @param priorityBoost - Optional priority multiplier
   * @returns true if added, false if duplicate/blocked/full
   */
  addUrl(url: string, depth: number, parentUrl?: string, priorityBoost: number = 1.0): boolean {
    const canonical = canonicalizeUrl(url);

    // Dedup
    if (this.seen.has(canonical)) return false;

    // Depth limit
    if (depth > this.config.maxDepth) return false;

    // Size limit
    if (this.entries.size >= this.config.maxSize) return false;

    // Domain blocking
    const domain = extractDomain(canonical);
    if (this.isBlocked(domain)) {
      this.stats.totalBlocked++;
      return false;
    }

    // Compute priority: higher is better
    // φ^(-depth) ensures seed URLs have highest priority
    const basePriority = Math.pow(PHI, -depth);
    const priority = basePriority * priorityBoost;

    const entry: FrontierEntry = {
      url: canonical,
      domain,
      depth,
      priority,
      status: 'queued',
      parentUrl,
      retries: 0,
      maxRetries: this.config.maxRetries,
      addedAt: Date.now(),
    };

    this.entries.set(canonical, entry);
    this.seen.add(canonical);
    this.stats.totalAdded++;
    this.updateStats();
    return true;
  }

  /**
   * Claim the next URL for crawling.
   * Returns the highest-priority queued URL whose domain isn't rate-limited.
   *
   * @param agentId - Agent claiming the URL
   * @returns FrontierEntry or null if nothing available
   */
  claim(agentId: string): FrontierEntry | null {
    // First, recover stale claims
    this.recoverStaleClaims();

    const now = Date.now();
    let best: FrontierEntry | null = null;

    for (const entry of this.entries.values()) {
      if (entry.status !== 'queued') continue;

      // Domain rate limit check
      const lastCrawled = this.domainLastCrawled.get(entry.domain);
      if (lastCrawled && now - lastCrawled < this.config.domainRateLimitMs) continue;

      // Pick highest priority
      if (!best || entry.priority > best.priority) {
        best = entry;
      }
    }

    if (!best) return null;

    // Claim it
    best.status = 'claimed';
    best.claimedBy = agentId;
    best.claimedAt = now;
    this.domainLastCrawled.set(best.domain, now);
    this.updateStats();

    return best;
  }

  /**
   * Mark a URL as being actively crawled.
   */
  markCrawling(url: string, agentId: string): boolean {
    const canonical = canonicalizeUrl(url);
    const entry = this.entries.get(canonical);
    if (!entry || entry.claimedBy !== agentId) return false;
    entry.status = 'crawling';
    this.updateStats();
    return true;
  }

  /**
   * Mark a URL as completed and submit discovered URLs.
   *
   * @param url - Completed URL
   * @param agentId - Agent that crawled it
   * @param discoveredUrls - URLs found on the page
   * @returns Number of new URLs added to frontier
   */
  complete(url: string, agentId: string, discoveredUrls: string[] = []): number {
    const canonical = canonicalizeUrl(url);
    const entry = this.entries.get(canonical);
    if (!entry) return 0;

    entry.status = 'completed';
    entry.completedAt = Date.now();
    this.stats.totalCompleted++;
    this.updateStats();

    // Add discovered URLs at depth + 1
    let added = 0;
    for (const discovered of discoveredUrls) {
      if (this.addUrl(discovered, entry.depth + 1, canonical)) {
        added++;
      }
    }

    return added;
  }

  /**
   * Mark a URL as failed. Retries if under limit.
   *
   * @param url - Failed URL
   * @param agentId - Agent that failed
   * @param error - Error description
   * @returns true if requeued for retry, false if permanently failed
   */
  fail(url: string, agentId: string, error: string): boolean {
    const canonical = canonicalizeUrl(url);
    const entry = this.entries.get(canonical);
    if (!entry) return false;

    entry.retries++;
    entry.error = error;
    entry.claimedBy = undefined;
    entry.claimedAt = undefined;

    if (entry.retries <= entry.maxRetries) {
      entry.status = 'queued';
      entry.priority *= 0.5; // Halve priority on retry
      this.updateStats();
      return true;
    }

    entry.status = 'failed';
    this.stats.totalFailed++;
    this.updateStats();
    return false;
  }

  /**
   * Block a domain at runtime.
   */
  blockDomain(pattern: string): void {
    this.blockedPatterns.push(new RegExp(pattern, 'i'));
    // Mark queued entries from this domain as blocked
    for (const entry of this.entries.values()) {
      if (entry.status === 'queued' && this.isBlocked(entry.domain)) {
        entry.status = 'blocked';
        this.stats.totalBlocked++;
      }
    }
    this.updateStats();
  }

  /**
   * Release a claimed URL back to the queue.
   */
  release(url: string, agentId: string): boolean {
    const canonical = canonicalizeUrl(url);
    const entry = this.entries.get(canonical);
    if (!entry || entry.claimedBy !== agentId) return false;
    entry.status = 'queued';
    entry.claimedBy = undefined;
    entry.claimedAt = undefined;
    this.updateStats();
    return true;
  }

  /**
   * Get a specific entry.
   */
  getEntry(url: string): FrontierEntry | undefined {
    return this.entries.get(canonicalizeUrl(url));
  }

  /**
   * Get all entries with a given status.
   */
  getByStatus(status: URLStatus): FrontierEntry[] {
    return [...this.entries.values()].filter((e) => e.status === status);
  }

  /**
   * Check if a URL has been seen.
   */
  hasSeen(url: string): boolean {
    return this.seen.has(canonicalizeUrl(url));
  }

  /**
   * Get frontier statistics.
   */
  getStats(): FrontierStats {
    return { ...this.stats };
  }

  /**
   * Get the total size of the frontier.
   */
  get size(): number {
    return this.entries.size;
  }

  /**
   * Check if the frontier has queued URLs.
   */
  get hasWork(): boolean {
    for (const entry of this.entries.values()) {
      if (entry.status === 'queued') return true;
    }
    return false;
  }

  // ─────────────────────────────────────────────────────────
  // Private
  // ─────────────────────────────────────────────────────────

  private isBlocked(domain: string): boolean {
    return this.blockedPatterns.some((p) => p.test(domain));
  }

  private recoverStaleClaims(): void {
    const now = Date.now();
    for (const entry of this.entries.values()) {
      if (
        (entry.status === 'claimed' || entry.status === 'crawling') &&
        entry.claimedAt &&
        now - entry.claimedAt > this.config.claimTimeoutMs
      ) {
        entry.status = 'queued';
        entry.claimedBy = undefined;
        entry.claimedAt = undefined;
        entry.priority *= 0.8; // Slight priority reduction for timeout
      }
    }
  }

  private updateStats(): void {
    let queued = 0;
    let claimed = 0;
    let crawling = 0;
    let totalDepth = 0;
    const domains = new Set<string>();

    for (const entry of this.entries.values()) {
      if (entry.status === 'queued') queued++;
      if (entry.status === 'claimed') claimed++;
      if (entry.status === 'crawling') crawling++;
      totalDepth += entry.depth;
      domains.add(entry.domain);
    }

    this.stats.queued = queued;
    this.stats.claimed = claimed;
    this.stats.crawling = crawling;
    this.stats.uniqueDomains = domains.size;
    this.stats.averageDepth = this.entries.size > 0 ? totalDepth / this.entries.size : 0;
  }
}
