import { describe, expect, it } from 'vitest';
import { redactDiagnostics, redactValue, validateGatewayEnv } from '../../src/gateway/env';

describe('gateway env validation', () => {
  it('throws when required governance vars are missing', () => {
    expect(() => validateGatewayEnv({})).toThrow(/Missing required governance env vars/);
  });

  it('rejects invalid port values', () => {
    expect(() =>
      validateGatewayEnv({
        PORT: '70000',
        GOVERNANCE_POLICY_ID: 'policy-1',
        GOVERNANCE_ISSUER: 'issuer-a',
        GOVERNANCE_TOKEN: 'token-value',
      })
    ).toThrow(/PORT must be a valid integer/);
  });

  it('returns parsed env when all vars are present', () => {
    const env = validateGatewayEnv({
      PORT: '9090',
      GOVERNANCE_POLICY_ID: 'policy-1',
      GOVERNANCE_ISSUER: 'issuer-a',
      GOVERNANCE_TOKEN: 'token-value',
    });

    expect(env.port).toBe(9090);
    expect(env.governancePolicyId).toBe('policy-1');
  });

  it('redacts token diagnostics', () => {
    const redacted = redactValue('supersecrettoken');
    expect(redacted).not.toContain('supersecrettoken');

    const diagnostics = redactDiagnostics({
      nodeEnv: 'production',
      port: 8081,
      governancePolicyId: 'p',
      governanceIssuer: 'i',
      governanceToken: 'abcdef123456',
    });

    expect(diagnostics.governanceToken).toBe('ab***56');
  });
});
