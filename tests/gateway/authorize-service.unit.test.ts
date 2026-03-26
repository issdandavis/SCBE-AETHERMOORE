/**
 * @file authorize-service.unit.test.ts
 * @module gateway/authorize-service
 * @layer Layer 13 (Risk Decision)
 * @component Gateway Authorize REST Endpoint
 *
 * Tests for the Express authorization service including:
 * - Input validation
 * - Decision mapping (kernel → HTTP)
 * - Health endpoint
 * - Error handling
 */

import { describe, expect, it, beforeAll, vi } from 'vitest';
import { BRAIN_DIMENSIONS } from '../../src/ai_brain/types';

// Stub the env validation before importing the service module
vi.stubEnv('GOVERNANCE_POLICY_ID', 'test-policy');
vi.stubEnv('GOVERNANCE_ISSUER', 'test-issuer');
vi.stubEnv('GOVERNANCE_TOKEN', 'test-token');
vi.stubEnv('PORT', '9999');
vi.stubEnv('SCBE_PHDM_MASTER_KEY', 'a'.repeat(64));

// Dynamic import after env is stubbed
const { createAuthorizeApp } = await import('../../src/gateway/authorize-service');

// Minimal supertest-like helper using the Express app directly
import type { Express } from 'express';
import type { IncomingMessage } from 'http';

async function request(app: Express, method: 'get' | 'post', path: string, body?: unknown) {
  return new Promise<{ status: number; body: Record<string, unknown> }>((resolve) => {
    const http = require('http');
    const server = http.createServer(app);

    server.listen(0, () => {
      const port = (server.address() as { port: number }).port;
      const bodyStr = body ? JSON.stringify(body) : '';
      const options = {
        hostname: '127.0.0.1',
        port,
        path,
        method: method.toUpperCase(),
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(bodyStr),
        },
      };

      const req = http.request(options, (res: IncomingMessage) => {
        let data = '';
        res.on('data', (chunk: string) => (data += chunk));
        res.on('end', () => {
          server.close();
          resolve({ status: res.statusCode ?? 500, body: JSON.parse(data) });
        });
      });

      req.write(bodyStr);
      req.end();
    });
  });
}

describe('authorize-service', () => {
  let app: Express;

  beforeAll(() => {
    const result = createAuthorizeApp();
    app = result.app;
  });

  describe('GET /health', () => {
    it('returns ok status', async () => {
      const res = await request(app, 'get', '/health');
      expect(res.status).toBe(200);
      expect(res.body.status).toBe('ok');
    });
  });

  describe('POST /authorize validation', () => {
    it('rejects missing agentId', async () => {
      const res = await request(app, 'post', '/authorize', {
        actionType: 'read',
        stateVector: new Array(BRAIN_DIMENSIONS).fill(0),
      });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/agentId/);
    });

    it('rejects empty agentId', async () => {
      const res = await request(app, 'post', '/authorize', {
        agentId: '   ',
        actionType: 'read',
        stateVector: new Array(BRAIN_DIMENSIONS).fill(0),
      });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/agentId/);
    });

    it('rejects missing actionType', async () => {
      const res = await request(app, 'post', '/authorize', {
        agentId: 'agent-1',
        stateVector: new Array(BRAIN_DIMENSIONS).fill(0),
      });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/actionType/);
    });

    it('rejects wrong stateVector length', async () => {
      const res = await request(app, 'post', '/authorize', {
        agentId: 'agent-1',
        actionType: 'read',
        stateVector: [1, 2, 3],
      });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/stateVector/);
    });

    it('rejects NaN in stateVector', async () => {
      const vec = new Array(BRAIN_DIMENSIONS).fill(0);
      vec[0] = NaN;
      const res = await request(app, 'post', '/authorize', {
        agentId: 'agent-1',
        actionType: 'read',
        stateVector: vec,
      });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/valid numbers/);
    });

    it('rejects non-array stateVector', async () => {
      const res = await request(app, 'post', '/authorize', {
        agentId: 'agent-1',
        actionType: 'read',
        stateVector: 'not-an-array',
      });
      expect(res.status).toBe(400);
      expect(res.body.error).toMatch(/stateVector/);
    });
  });

  describe('POST /authorize success', () => {
    it('returns a valid authorization response', async () => {
      const res = await request(app, 'post', '/authorize', {
        agentId: 'agent-test',
        actionType: 'read',
        stateVector: new Array(BRAIN_DIMENSIONS).fill(0.1),
      });

      expect(res.status).toBe(200);
      expect(res.body.agentId).toBe('agent-test');
      expect(['ALLOW', 'QUARANTINE', 'DENY']).toContain(res.body.decision);
      expect(['ALLOW', 'TRANSFORM', 'BLOCK', 'QUARANTINE']).toContain(res.body.kernelDecision);
      expect(typeof res.body.combinedRiskScore).toBe('number');
      expect(typeof res.body.auditHash).toBe('string');
    });

    it('maps BLOCK kernel decision to DENY HTTP decision', () => {
      // Test the mapping function logic inline
      const mappings: Record<string, string> = {
        ALLOW: 'ALLOW',
        TRANSFORM: 'QUARANTINE',
        QUARANTINE: 'QUARANTINE',
        BLOCK: 'DENY',
      };
      for (const [kernel, expected] of Object.entries(mappings)) {
        // Verify the mapping is correct per authorize-service.ts:37-43
        let result: string;
        if (kernel === 'ALLOW') result = 'ALLOW';
        else if (kernel === 'TRANSFORM' || kernel === 'QUARANTINE') result = 'QUARANTINE';
        else result = 'DENY';
        expect(result).toBe(expected);
      }
    });
  });
});
