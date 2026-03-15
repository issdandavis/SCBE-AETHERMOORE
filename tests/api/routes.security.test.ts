import { describe, expect, it } from 'vitest';
import { handleCreateEnvelope, handleVerifyEnvelope } from '../../src/api/routes.js';

describe('API envelope security', () => {
  it('verifies an envelope created with the same password', async () => {
    const created = await handleCreateEnvelope({
      plaintext: 'SCBE runtime governance',
      password: 'correct horse battery staple',
      aad: { scope: 'test' },
    });

    const verified = await handleVerifyEnvelope({
      envelope: created.envelope,
      password: 'correct horse battery staple',
    });

    expect(verified.valid).toBe(true);
    expect(verified.plaintext).toBe('SCBE runtime governance');
    expect(verified.details.macValid).toBe(true);
  });

  it('rejects verification with the wrong password', async () => {
    const created = await handleCreateEnvelope({
      plaintext: 'SCBE runtime governance',
      password: 'correct horse battery staple',
    });

    const verified = await handleVerifyEnvelope({
      envelope: created.envelope,
      password: 'wrong password',
    });

    expect(verified.valid).toBe(false);
    expect(verified.error).toBe('MAC verification failed');
  });
});
