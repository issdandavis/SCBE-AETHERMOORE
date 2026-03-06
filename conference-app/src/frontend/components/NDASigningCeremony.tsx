/**
 * @file NDASigningCeremony.tsx
 * @module conference/frontend/components
 *
 * NDA signing ceremony component. Presents the NDA terms,
 * collects acknowledgment, and submits the signed NDA.
 *
 * In production, this would integrate with DocuSign/CLM.
 * For MVP, it renders the NDA template inline and captures consent.
 */

import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';

interface Props {
  onSigned: () => void;
  projectId?: string | null;
}

const PLATFORM_NDA_TEXT = `
MUTUAL NON-DISCLOSURE AGREEMENT

This Mutual Non-Disclosure Agreement ("Agreement") is entered into as of the date
of electronic acceptance by and between the Disclosing Party and Receiving Party
(collectively, the "Parties").

1. CONFIDENTIAL INFORMATION
   "Confidential Information" means any non-public information disclosed by either
   Party, including but not limited to: business plans, financial data, technical
   specifications, source code, product roadmaps, investor materials, funding terms,
   cap table information, and governance audit results.

2. OBLIGATIONS
   The Receiving Party shall:
   (a) Hold all Confidential Information in strict confidence;
   (b) Not disclose Confidential Information to any third party without prior
       written consent;
   (c) Use Confidential Information solely for evaluating potential investment
       or business relationships;
   (d) Return or destroy Confidential Information upon request.

3. EXCEPTIONS
   This Agreement does not apply to information that:
   (a) Is or becomes publicly available through no fault of the Receiving Party;
   (b) Was already known to the Receiving Party prior to disclosure;
   (c) Is independently developed without use of Confidential Information;
   (d) Is required to be disclosed by law or regulation.

4. TERM
   This Agreement shall remain in effect for two (2) years from the date of
   acceptance.

5. GOVERNANCE
   All materials accessed through this platform are subject to SCBE-AETHERMOORE
   governance scoring. Access to specific materials may be restricted based on
   governance decisions (ALLOW/QUARANTINE/DENY). All access events are logged
   to an immutable HYDRA audit ledger.

6. GOVERNING LAW
   This Agreement shall be governed by and construed in accordance with applicable
   federal and state laws.
`.trim();

export default function NDASigningCeremony({ onSigned, projectId }: Props) {
  const { post } = useApi();
  const [scrolledToBottom, setScrolledToBottom] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [signing, setSigning] = useState(false);
  const [signed, setSigned] = useState(false);

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 20) {
      setScrolledToBottom(true);
    }
  };

  const handleSign = async () => {
    setSigning(true);
    const res = await post('/ndas/sign', { projectId: projectId ?? null });
    if (res.success) {
      setSigned(true);
      setTimeout(onSigned, 1500);
    }
    setSigning(false);
  };

  if (signed) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: 48 }}>
        <div style={{ fontSize: '2rem', marginBottom: 16, color: 'var(--accent-green)' }}>NDA Signed</div>
        <p style={{ color: 'var(--text-secondary)' }}>
          Your agreement has been recorded. You now have access to confidential materials.
        </p>
        <div className="governance-ribbon" style={{ justifyContent: 'center', marginTop: 16 }}>
          <span className="governance-stat">status: <span className="value">SIGNED</span></span>
          <span className="governance-stat">scope: <span className="value">{projectId ? 'PROJECT' : 'PLATFORM'}</span></span>
          <span className="governance-stat">ledger: <span className="value">HYDRA-RECORDED</span></span>
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ maxWidth: 680, margin: '0 auto' }}>
      <h3 style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)', marginBottom: 16 }}>
        {projectId ? 'Project NDA' : 'Platform NDA'} — Signing Ceremony
      </h3>

      <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 16 }}>
        Please read the following agreement carefully. You must scroll to the bottom
        before signing.
      </p>

      {/* NDA text area with scroll tracking */}
      <div
        onScroll={handleScroll}
        style={{
          background: 'var(--bg-primary)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: 20,
          maxHeight: 320,
          overflowY: 'auto',
          fontFamily: 'var(--font-mono)',
          fontSize: '0.78rem',
          lineHeight: 1.8,
          color: 'var(--text-secondary)',
          whiteSpace: 'pre-wrap',
          marginBottom: 20,
        }}
      >
        {PLATFORM_NDA_TEXT}
      </div>

      {!scrolledToBottom && (
        <p style={{ color: 'var(--accent-amber)', fontSize: '0.8rem', marginBottom: 12 }}>
          Scroll to the bottom of the agreement to continue.
        </p>
      )}

      {/* Acknowledgment checkbox */}
      <label
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: 10,
          cursor: scrolledToBottom ? 'pointer' : 'not-allowed',
          opacity: scrolledToBottom ? 1 : 0.4,
          marginBottom: 20,
        }}
      >
        <input
          type="checkbox"
          checked={acknowledged}
          disabled={!scrolledToBottom}
          onChange={e => setAcknowledged(e.target.checked)}
          style={{ marginTop: 4, accentColor: 'var(--accent-green)' }}
        />
        <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
          I have read and agree to the terms of this Non-Disclosure Agreement.
          I understand that all access is logged to the HYDRA governance ledger.
        </span>
      </label>

      {/* Sign button */}
      <button
        className="btn-success"
        disabled={!acknowledged || signing}
        onClick={handleSign}
        style={{ width: '100%', opacity: acknowledged ? 1 : 0.4 }}
      >
        {signing ? 'Signing...' : 'Sign NDA Electronically'}
      </button>

      <p style={{ color: 'var(--text-muted)', fontSize: '0.72rem', marginTop: 12, textAlign: 'center' }}>
        By clicking "Sign NDA Electronically" you agree this constitutes your electronic signature.
      </p>
    </div>
  );
}
