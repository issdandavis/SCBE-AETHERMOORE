import { describe, expect, it } from 'vitest';
import { parseHfAgentPrompt, parseHfPairCommand } from '../../ai-ide/src/data/hfAgentPair';

describe('parseHfPairCommand', () => {
  it('parses pair install commands', () => {
    expect(parseHfPairCommand('@hf-pair install')).toEqual({
      action: 'install',
      agentId: null,
    });
  });

  it('defaults agent heads to launch', () => {
    expect(parseHfPairCommand('@hf-coder')).toEqual({
      action: 'launch',
      agentId: 'hf-coder',
    });
  });

  it('rejects non-control prompts', () => {
    expect(parseHfPairCommand('@hf-coder build a toolbar')).toBeNull();
  });
});

describe('parseHfAgentPrompt', () => {
  it('extracts explicit coder prompts', () => {
    expect(parseHfAgentPrompt('@hf-coder review this file')).toEqual({
      agentId: 'hf-coder',
      prompt: 'review this file',
    });
  });

  it('leaves normal prompts untouched', () => {
    expect(parseHfAgentPrompt('explain the current file')).toEqual({
      agentId: null,
      prompt: 'explain the current file',
    });
  });
});
