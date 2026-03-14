import React from 'react';
import type { LayerScore } from '../../shared/types/index.js';

interface Props {
  layers: LayerScore[];
}

export default function GovernanceLayers({ layers }: Props) {
  return (
    <div style={{ display: 'grid', gap: 4 }}>
      {layers.map(layer => (
        <div
          key={layer.layer}
          style={{
            display: 'grid',
            gridTemplateColumns: '40px 180px 1fr 60px',
            gap: 12,
            alignItems: 'center',
            padding: '6px 10px',
            background: layer.passed ? 'rgba(68, 204, 136, 0.05)' : 'rgba(255, 68, 102, 0.05)',
            borderRadius: 'var(--radius)',
            borderLeft: `3px solid ${layer.passed ? 'var(--accent-green)' : 'var(--accent-red)'}`,
          }}
        >
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            L{layer.layer}
          </span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            {layer.name}
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {layer.note ?? ''}
          </span>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.8rem',
            color: layer.passed ? 'var(--accent-green)' : 'var(--accent-red)',
            textAlign: 'right',
          }}>
            {layer.passed ? 'PASS' : 'FAIL'}
          </span>
        </div>
      ))}
    </div>
  );
}
