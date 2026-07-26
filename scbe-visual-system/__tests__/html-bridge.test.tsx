import React, { act } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  HANDOFF_PACKET,
  HANDOFF_PACKET_SCHEMA,
  HtmlBridgeApp,
  STATE_VECTOR_REQUEST,
} from '../components/apps/HtmlBridgeApp';

type ReactTestGlobal = typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean };

const getButton = (container: HTMLElement, label: string) => {
  const button = Array.from(container.querySelectorAll('button')).find(
    (candidate) => candidate.textContent?.trim() === label
  );
  if (!button) throw new Error(`Button not found: ${label}`);
  return button;
};

describe('HtmlBridgeApp', () => {
  let container: HTMLDivElement;
  let root: Root;

  beforeEach(async () => {
    (globalThis as ReactTestGlobal).IS_REACT_ACT_ENVIRONMENT = true;
    container = document.createElement('div');
    document.body.appendChild(container);
    root = createRoot(container);
    await act(async () => {
      root.render(<HtmlBridgeApp />);
    });
  });

  afterEach(async () => {
    await act(async () => {
      root.unmount();
    });
    container.remove();
    vi.restoreAllMocks();
  });

  it('emits the canonical documented packet schema', () => {
    const parsedPacket = JSON.parse(HANDOFF_PACKET);

    expect(parsedPacket).toEqual(HANDOFF_PACKET_SCHEMA);
    expect(Object.keys(parsedPacket)).toEqual([
      'packet',
      'version',
      'source',
      'principle',
      'rubix_faces',
      'copy_targets',
      'governance_checks',
      'state_vector_request',
      'website_app',
      'registry_tile',
    ]);
    expect(parsedPacket.copy_targets).toEqual(['prompt', 'handoff_packet']);
  });

  it('fails closed until the trusted runtime constructs the 9D state', () => {
    expect(STATE_VECTOR_REQUEST.status).toBe('runtime_required');
    expect(STATE_VECTOR_REQUEST.dimensions).toHaveLength(9);
    expect(STATE_VECTOR_REQUEST.dimensions.slice(0, 2).map(({ status }) => status)).toEqual([
      'evidence_bound',
      'evidence_bound',
    ]);
    expect(
      STATE_VECTOR_REQUEST.dimensions.slice(2).every(({ status }) => status === 'runtime_required')
    ).toBe(true);
    expect(STATE_VECTOR_REQUEST.governance_decision).toBe('not_evaluated');
    expect(STATE_VECTOR_REQUEST).not.toHaveProperty('xi');
    expect(container.textContent).toContain('9D state preflight');
    expect(container.textContent).toContain('Runtime evaluation required');
  });
  it('copies the handoff packet and announces success', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    await act(async () => {
      getButton(container, 'Copy packet').click();
      await Promise.resolve();
    });

    expect(writeText).toHaveBeenCalledWith(HANDOFF_PACKET);
    expect(container.querySelector('[role="status"]')?.textContent).toContain(
      'Handoff packet copied for cross-system use.'
    );
  });

  it('expands the canonical packet for manual copying when clipboard access fails', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('Clipboard blocked'));
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    });

    await act(async () => {
      getButton(container, 'Copy packet').click();
      await Promise.resolve();
    });

    expect(container.querySelector('[role="alert"]')?.textContent).toContain(
      'Clipboard unavailable. Select the handoff packet below and copy it manually.'
    );
    expect(container.querySelector('details')?.open).toBe(true);
    expect(container.querySelector('details code')?.textContent).toBe(HANDOFF_PACKET);
  });
});
