"use strict";
/**
 * Governance API Server
 *
 * Express server exposing the /govern endpoint and related APIs.
 *
 * @module api/server
 */
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.createApp = createApp;
exports.startServer = startServer;
const express_1 = __importDefault(require("express"));
const crypto_1 = require("crypto");
const govern_js_1 = require("./govern.js");
// ============================================================================
// In-Memory Audit Log (replace with database in production)
// ============================================================================
const auditLog = [];
const MAX_AUDIT_ENTRIES = 10000;
function addAuditEntry(entry) {
    auditLog.unshift(entry);
    if (auditLog.length > MAX_AUDIT_ENTRIES) {
        auditLog.pop();
    }
}
// ============================================================================
// Middleware
// ============================================================================
/** Request logging */
function requestLogger(req, res, next) {
    const start = Date.now();
    res.on('finish', () => {
        const duration = Date.now() - start;
        console.log(`${req.method} ${req.path} ${res.statusCode} ${duration}ms`);
    });
    next();
}
/** API key validation */
function apiKeyAuth(req, res, next) {
    const apiKey = req.headers['x-scbe-api-key'];
    // In production, validate against stored keys
    // For now, accept any non-empty key or allow local requests
    if (!apiKey && req.ip !== '127.0.0.1' && req.ip !== '::1') {
        res.status(401).json({
            error: 'Unauthorized',
            message: 'Missing X-SCBE-API-Key header',
        });
        return;
    }
    next();
}
/** Rate limiting (simple in-memory implementation) */
const rateLimits = new Map();
const RATE_LIMIT_WINDOW_MS = 60000;
const RATE_LIMIT_MAX_REQUESTS = 100;
function rateLimit(req, res, next) {
    const key = req.ip || 'unknown';
    const now = Date.now();
    let limit = rateLimits.get(key);
    if (!limit || now > limit.resetAt) {
        limit = { count: 0, resetAt: now + RATE_LIMIT_WINDOW_MS };
        rateLimits.set(key, limit);
    }
    limit.count++;
    if (limit.count > RATE_LIMIT_MAX_REQUESTS) {
        res.status(429).json({
            error: 'Too Many Requests',
            message: `Rate limit exceeded. Try again in ${Math.ceil((limit.resetAt - now) / 1000)} seconds`,
        });
        return;
    }
    res.setHeader('X-RateLimit-Limit', RATE_LIMIT_MAX_REQUESTS.toString());
    res.setHeader('X-RateLimit-Remaining', (RATE_LIMIT_MAX_REQUESTS - limit.count).toString());
    res.setHeader('X-RateLimit-Reset', Math.ceil(limit.resetAt / 1000).toString());
    next();
}
// ============================================================================
// Routes
// ============================================================================
function createApp() {
    const app = (0, express_1.default)();
    // Middleware
    app.use(express_1.default.json());
    app.use(requestLogger);
    app.use(rateLimit);
    // Health check (no auth required)
    app.get('/health', (_req, res) => {
        res.json({ status: 'healthy', timestamp: new Date().toISOString() });
    });
    app.get('/ready', (_req, res) => {
        res.json({ status: 'ready', timestamp: new Date().toISOString() });
    });
    // API routes (auth required)
    app.use('/v1', apiKeyAuth);
    /**
     * POST /v1/govern
     * Main governance decision endpoint
     */
    app.post('/v1/govern', (req, res) => {
        const start = Date.now();
        try {
            const request = req.body;
            // Validate required fields
            if (!request.actor?.id || !request.actor?.type) {
                res.status(400).json({
                    error: 'Bad Request',
                    message: 'Missing required field: actor.id or actor.type',
                });
                return;
            }
            if (!request.resource?.type || !request.resource?.id) {
                res.status(400).json({
                    error: 'Bad Request',
                    message: 'Missing required field: resource.type or resource.id',
                });
                return;
            }
            if (!request.intent) {
                res.status(400).json({
                    error: 'Bad Request',
                    message: 'Missing required field: intent',
                });
                return;
            }
            if (!request.nonce) {
                res.status(400).json({
                    error: 'Bad Request',
                    message: 'Missing required field: nonce',
                });
                return;
            }
            // Execute governance decision
            const response = (0, govern_js_1.govern)(request);
            // Audit log
            const processingTime = Date.now() - start;
            addAuditEntry({
                id: response.audit_id,
                timestamp: response.timestamp,
                request,
                response,
                processing_time_ms: processingTime,
                ip_address: req.ip,
            });
            res.json(response);
        }
        catch (error) {
            console.error('Governance error:', error);
            res.status(500).json({
                error: 'Internal Server Error',
                message: 'Governance engine error',
            });
        }
    });
    /**
     * POST /v1/govern/batch
     * Batch governance decisions
     */
    app.post('/v1/govern/batch', (req, res) => {
        try {
            const { requests } = req.body;
            if (!Array.isArray(requests) || requests.length === 0) {
                res.status(400).json({
                    error: 'Bad Request',
                    message: 'Missing or empty requests array',
                });
                return;
            }
            if (requests.length > 100) {
                res.status(400).json({
                    error: 'Bad Request',
                    message: 'Batch size exceeds maximum of 100',
                });
                return;
            }
            const decisions = requests.map((request) => {
                try {
                    return (0, govern_js_1.govern)(request);
                }
                catch {
                    return {
                        decision: 'DENY',
                        request_id: (0, crypto_1.randomUUID)(),
                        timestamp: new Date().toISOString(),
                        rationale: 'Request processing failed',
                        policy_ids: [],
                        risk_score: 1.0,
                        harmonic_cost: Infinity,
                        audit_id: (0, crypto_1.randomUUID)(),
                    };
                }
            });
            res.json({ decisions });
        }
        catch (error) {
            console.error('Batch governance error:', error);
            res.status(500).json({
                error: 'Internal Server Error',
                message: 'Batch processing error',
            });
        }
    });
    /**
     * GET /v1/policies
     * List active governance policies
     */
    app.get('/v1/policies', (_req, res) => {
        res.json((0, govern_js_1.listPolicies)());
    });
    /**
     * GET /v1/audit
     * Get governance audit log
     */
    app.get('/v1/audit', (req, res) => {
        const { since, actor_id, decision, limit = '100' } = req.query;
        let entries = [...auditLog];
        // Filter by timestamp
        if (since && typeof since === 'string') {
            const sinceDate = new Date(since).getTime();
            entries = entries.filter((e) => new Date(e.timestamp).getTime() >= sinceDate);
        }
        // Filter by actor
        if (actor_id && typeof actor_id === 'string') {
            entries = entries.filter((e) => e.request.actor.id === actor_id);
        }
        // Filter by decision
        if (decision && typeof decision === 'string') {
            entries = entries.filter((e) => e.response.decision === decision);
        }
        // Limit results
        const limitNum = Math.min(parseInt(limit) || 100, 1000);
        entries = entries.slice(0, limitNum);
        res.json(entries);
    });
    /**
     * GET /v1/audit/:id
     * Get specific audit entry
     */
    app.get('/v1/audit/:id', (req, res) => {
        const entry = auditLog.find((e) => e.id === req.params.id);
        if (!entry) {
            res.status(404).json({
                error: 'Not Found',
                message: 'Audit entry not found',
            });
            return;
        }
        res.json(entry);
    });
    /**
     * GET /v1/stats
     * Get governance statistics
     */
    app.get('/v1/stats', (_req, res) => {
        const decisions = {
            ALLOW: 0,
            DENY: 0,
            ESCALATE: 0,
            QUARANTINE: 0,
        };
        let totalRisk = 0;
        let totalProcessingTime = 0;
        for (const entry of auditLog) {
            decisions[entry.response.decision]++;
            totalRisk += entry.response.risk_score;
            totalProcessingTime += entry.processing_time_ms;
        }
        const count = auditLog.length || 1;
        res.json({
            total_requests: auditLog.length,
            decisions,
            average_risk_score: totalRisk / count,
            average_processing_time_ms: totalProcessingTime / count,
            active_policies: (0, govern_js_1.listPolicies)().filter((p) => p.enabled).length,
        });
    });
    return app;
}
/**
 * Start the server
 */
function startServer(port = 8080) {
    const app = createApp();
    app.listen(port, () => {
        console.log(`🛡️  SCBE Governance API running on http://localhost:${port}`);
        console.log(`   POST /v1/govern       - Request governance decision`);
        console.log(`   POST /v1/govern/batch - Batch governance decisions`);
        console.log(`   GET  /v1/policies     - List active policies`);
        console.log(`   GET  /v1/audit        - Get audit log`);
        console.log(`   GET  /v1/stats        - Get statistics`);
    });
}
// Run if executed directly
if (process.argv[1]?.endsWith('server.ts') || process.argv[1]?.endsWith('server.js')) {
    const port = parseInt(process.env.PORT || '8080');
    startServer(port);
}
//# sourceMappingURL=server.js.map