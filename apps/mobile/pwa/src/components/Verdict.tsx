type VerdictKind = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';

export function Verdict({ v }: { v: VerdictKind }) {
  return <span className={`verdict ${v}`}>{v}</span>;
}
