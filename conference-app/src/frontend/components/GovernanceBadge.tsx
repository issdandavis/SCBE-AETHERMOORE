import React from 'react';
import type { GovernanceDecision } from '../../shared/types/index.js';

interface Props {
  decision: GovernanceDecision;
}

const BADGE_CLASS: Record<GovernanceDecision, string> = {
  ALLOW: 'badge-allow',
  QUARANTINE: 'badge-quarantine',
  ESCALATE: 'badge-escalate',
  DENY: 'badge-deny',
};

export default function GovernanceBadge({ decision }: Props) {
  return <span className={`badge ${BADGE_CLASS[decision]}`}>{decision}</span>;
}
