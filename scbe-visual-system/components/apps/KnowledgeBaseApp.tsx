/**
 * SCBE Knowledge Base - Unified Documentation & Learning System
 *
 * Everything links back to the core SCBE axioms. This app provides:
 * - Full axiom documentation with visual explanations
 * - Interactive tutorials on hyperbolic geometry, harmonic resonance
 * - Quick reference for developers, operators, and auditors
 * - Live connections to system state (shows current health via axioms)
 *
 * "Think inside and outside the box at the same time
 *  while looking at a problem on the horizon and behind you"
 *
 * @license Apache-2.0
 * @patent USPTO #63/961,403
 */
import React, { useState } from 'react';
import {
  BookOpen, Search, ChevronRight, Layers, Waves, Hexagon,
  Atom, Shield, Key, Lock, Activity, Target, Sparkles,
  Code, FileText, GraduationCap, Lightbulb, ArrowRight,
  ExternalLink, Copy, Check, Zap, GitBranch
} from 'lucide-react';

type Category = 'axioms' | 'sacred_tongues' | 'architecture' | 'tutorials' | 'api';

interface DocEntry {
  id: string;
  title: string;
  category: Category;
  icon: React.FC<{ size: number; className?: string }>;
  summary: string;
  content: string;
  codeExample?: string;
  relatedAxioms?: number[];
}

const KNOWLEDGE_BASE: DocEntry[] = [
  // AXIOMS
  {
    id: 'axiom-1',
    title: 'Axiom 1: Positivity of Cost',
    category: 'axioms',
    icon: Target,
    summary: 'All authentication costs are strictly positive.',
    content: `**Statement**: L(x, t) > 0 for all states x and times t.

**Why It Matters**: There is no "free" authentication. Every verification requires resource commitment from requesters, preventing spam attacks and ensuring accountability.

**Mathematical Form**:
\`\`\`
For all states x ∈ ℝⁿ and times t ∈ ℝ:
L(x, t) > 0
\`\`\`

**Real-World Application**: When an agent requests verification, they must "pay" with computational work. This cost scales with the sensitivity of the operation.`,
    relatedAxioms: [2, 3, 5]
  },
  {
    id: 'axiom-2',
    title: 'Axiom 2: Monotonicity of Deviation',
    category: 'axioms',
    icon: Activity,
    summary: 'Increased deviation strictly increases cost.',
    content: `**Statement**: dL/dd_l > 0 for all deviations d_l ≥ 0.

**Why It Matters**: Any departure from trusted behavior is penalized. The further from ideal, the higher the cost. This creates a natural "gravity" pulling the system toward the trusted state.

**Mathematical Form**:
\`\`\`
∂L/∂d_l > 0 for all l
\`\`\`

**Visual Intuition**: Imagine a bowl - the trusted state is at the bottom. Rolling up any side (deviating) requires increasing energy.`,
    relatedAxioms: [1, 3, 6]
  },
  {
    id: 'axiom-3',
    title: 'Axiom 3: Convexity of Cost Surface',
    category: 'axioms',
    icon: Layers,
    summary: 'Unique global minimum - no local minima traps.',
    content: `**Statement**: d²L/dd_l² > 0 for all deviations.

**Why It Matters**: There exists exactly ONE optimal (trusted) state. Gradient descent always reaches the global optimum - attackers cannot hide in local minima.

**Mathematical Form**:
\`\`\`
∂²L/∂d_l² > 0 (strict convexity)
\`\`\`

**Security Implication**: Attackers cannot create "fake" trusted states. The geometry guarantees convergence to the true optimum.`,
    relatedAxioms: [2, 6]
  },
  {
    id: 'axiom-7',
    title: 'Axiom 7: Harmonic Resonance',
    category: 'axioms',
    icon: Waves,
    summary: 'All 6 Sacred Tongue gates must resonate in harmony.',
    content: `**Statement**: Auth_valid iff for all l ∈ {1,...,6}: Gate_l.status == RESONANT

**Why It Matters**: Security is holistic. Compromising ONE gate breaks the entire chord. This prevents attackers from isolating vulnerabilities.

**The Six Gates**:
1. **KO (Kor'aelin)**: Control & Intent
2. **AV (Avali)**: I/O & Messaging
3. **RU (Runethic)**: Policy & Constraints
4. **CA (Cassisivadan)**: Logic & Computation
5. **UM (Umbroth)**: Security & Secrets
6. **DR (Draumric)**: Types & Schema

**Golden Ratio Weighting** (Axiom 10):
\`\`\`
w_l = φ^(l-1) where φ = (1 + √5)/2 ≈ 1.618
\`\`\``,
    codeExample: `// Check harmonic resonance
const isValid = SACRED_GATES.every(
  gate => gate.status === 'RESONANT'
);`,
    relatedAxioms: [10, 12]
  },
  {
    id: 'axiom-9',
    title: 'Axiom 9: Hyperbolic Geometry',
    category: 'axioms',
    icon: Hexagon,
    summary: 'Authentication in Poincaré ball model.',
    content: `**Statement**: Authentication trajectories exist in hyperbolic space.

**Why It Matters**: Exponential growth of volume with radius provides NATURAL separation of trust levels. Trusted entities cluster at the center; threats are pushed to the boundary.

**Poincaré Ball Distance**:
\`\`\`
d(u, v) = arcosh(1 + 2||u-v||² / ((1-||u||²)(1-||v||²)))
\`\`\`

**Key Properties**:
- Points near center (trusted) have small distances
- Points near boundary (untrusted) have large distances
- Volume grows EXPONENTIALLY with radius

**Security Application**: Attack paths create measurable deviations in this geometry. No training data required - detection is mathematical.`,
    codeExample: `// Hyperbolic distance calculation
function hyperbolicDistance(u: number[], v: number[]): number {
  const normU = Math.sqrt(u.reduce((s, x) => s + x*x, 0));
  const normV = Math.sqrt(v.reduce((s, x) => s + x*x, 0));
  const diff = u.map((x, i) => x - v[i]);
  const normDiff = Math.sqrt(diff.reduce((s, x) => s + x*x, 0));

  const denom = (1 - normU*normU) * (1 - normV*normV);
  return Math.acosh(1 + (2 * normDiff*normDiff) / denom);
}`,
    relatedAxioms: [12]
  },
  {
    id: 'axiom-12',
    title: 'Axiom 12: Topological Attack Detection',
    category: 'axioms',
    icon: GitBranch,
    summary: 'Attacks leave geometric signatures.',
    content: `**Statement**: For any ROP/JOP attack path P, exists topological invariant I such that I(P) ≠ I(P_valid).

**Why It Matters**: Control-flow attacks (ROP, JOP, code reuse) create DETECTABLE deviations in manifold topology. No machine learning needed - detection is pure mathematics.

**Detection Rate**: ≥ 92% (Theorem 4)

**How It Works**:
1. Valid execution paths form a specific topology
2. Attack paths have different topological invariants
3. The invariant mismatch is ALWAYS detectable

**Combined with Axiom 9**: Hyperbolic geometry amplifies these deviations, making attacks even easier to spot.`,
    relatedAxioms: [7, 9]
  },
  {
    id: 'axiom-8',
    title: 'Axiom 8: Quantum Resistance',
    category: 'axioms',
    icon: Atom,
    summary: 'Security via lattice hardness (LWE/SVP).',
    content: `**Statement**: Security reduces to hardness of lattice problems.

**Mathematical Guarantee**:
\`\`\`
Transference bound: T ≥ 2^188.9
Reduces to: LWE with dimension n ≥ 768
\`\`\`

**Why It Matters**: Resistant to Shor's algorithm. Security holds against QUANTUM adversaries with 128-bit post-quantum security.

**Implementations**:
- **Kyber-768**: Key encapsulation (NIST approved)
- **Dilithium-3**: Digital signatures (NIST approved)`,
    relatedAxioms: [13]
  },
  {
    id: 'axiom-13',
    title: 'Axiom 13: Atomic Rekeying',
    category: 'axioms',
    icon: Key,
    summary: 'Instant, all-or-nothing key rotation on threat.',
    content: `**Statement**: Upon threat detection, cryptographic state rekeys atomically.

**Mathematical Form**:
\`\`\`
If threat_detected:
    (K_old, S_old) → (K_new, S_new) atomically
    No intermediate state exposed
\`\`\`

**Why It Matters**: Attackers cannot exploit partial rekeying. State transitions are all-or-nothing. Even if an attacker triggers rekeying, they learn nothing about the new state.

**Implementation**: Uses quantum-safe key derivation with commit-reveal protocol.`,
    relatedAxioms: [8]
  },

  // SACRED TONGUES
  {
    id: 'tongue-overview',
    title: 'The Six Sacred Tongues',
    category: 'sacred_tongues',
    icon: Sparkles,
    summary: 'Domain separation for secure multi-agent communication.',
    content: `The Six Sacred Tongues provide domain separation for AI-to-AI communication and governance:

| Tongue | Name | Domain | Governance Level |
|--------|------|--------|-----------------|
| **KO** | Kor'aelin | Control & Intent | Kindergarten |
| **AV** | Avali | I/O & Messaging | Elementary |
| **RU** | Runethic | Policy & Constraints | Middle School |
| **CA** | Cassisivadan | Logic & Computation | High School |
| **UM** | Umbroth | Security & Secrets | University |
| **DR** | Draumric | Types & Schema | Doctorate |

**Progression**: Agents earn XP and progress through tiers like students in school. Higher tiers grant more autonomy and access to sensitive operations.

**Multi-Signature**: Critical operations require signatures from multiple tongues (e.g., DR + UM + CA for deployments).`,
    codeExample: `// Multi-signature verification
const requiredTongues = ['DR', 'UM', 'CA'];
const isValid = requiredTongues.every(
  tongue => envelope.signatures[tongue]
);`,
    relatedAxioms: [7, 10]
  },

  // ARCHITECTURE
  {
    id: 'arch-14-layers',
    title: '14-Layer Security Stack',
    category: 'architecture',
    icon: Layers,
    summary: 'Defense-in-depth from input to quantum lattice.',
    content: `The SCBE security stack has 14 layers, each mapped to specific axioms:

| # | Layer | Axiom(s) |
|---|-------|----------|
| 1 | Input Validation | 1, 2 |
| 2 | Authentication | 7 |
| 3 | Authorization | 7, 10 |
| 4 | Session Management | 4 |
| 5 | PQC Encryption | 8 |
| 6 | Integrity Check | 2, 3 |
| 7 | Rate Limiting | 1 |
| 8 | Logging & Audit | 5 |
| 9 | Error Handling | 5 |
| 10 | API Security | 7 |
| 11 | Network Security | 9 |
| 12 | Hyperbolic Boundary | 9 |
| 13 | Harmonic Resonance | 7 |
| 14 | Quantum Lattice | 8, 13 |

**Theorem 5**: Verification overhead ≤ 0.5% of baseline computation.`,
    relatedAxioms: [1, 2, 3, 4, 5, 7, 8, 9, 10, 13]
  },

  // TUTORIALS
  {
    id: 'tutorial-polly-pads',
    title: 'Polly Pads: Agent Workspaces',
    category: 'tutorials',
    icon: GraduationCap,
    summary: 'Personal workspaces that grow like students.',
    content: `**Polly Pads** are personal workspaces for AI agents based on Axiom 11 (Fractional Dimension Flux).

**Dimensional States**:
- **POLLY** (ν ≥ 0.8): Full swarm participation
- **QUASI** (0.5 ≤ ν < 0.8): Partial sync, limited tools
- **DEMI** (0.1 ≤ ν < 0.5): Minimal, read-only
- **COLLAPSED** (ν < 0.1): Offline, archived

**Growth System**:
- Notes: +10 XP
- Sketches: +15 XP
- Tools: +25 XP
- Task completions: +50 XP

**Governance Progression**:
KO (0 XP) → AV (100) → RU (500) → CA (2000) → UM (10000) → DR (50000)

Agents are audited by the system like "kids at school" - their pads reflect their growth and trustworthiness.`,
    codeExample: `// Create a Polly Pad for an agent
const pad = fleet.createPad(agentId, 'Navigator-Bot');

// Add content (earns XP)
fleet.addPadNote(agentId, 'Mission Log', content, ['mission']);
fleet.addPadSketch(agentId, 'Trajectory', svgData, 'diagram');
fleet.addPadTool(agentId, 'Scanner', 'Detection tool', 'script', code);`,
    relatedAxioms: [11]
  },

  // API
  {
    id: 'api-envelope',
    title: 'RWP v3 Envelope Protocol',
    category: 'api',
    icon: Code,
    summary: 'Hybrid spelltext + payload message format.',
    content: `The **Roundtable Wire Protocol v3** uses a hybrid envelope format:

**Envelope Structure**:
\`\`\`typescript
interface SpiralverseEnvelope {
  spelltext: string;     // Human-readable metadata
  payload: string;       // Base64URL encoded action
  signatures: SignatureSet;  // Multi-tongue signatures
  ts: string;           // ISO 8601 timestamp
  nonce: string;        // Replay protection
}
\`\`\`

**Security Features**:
- Domain-separated HMAC signatures
- 5-minute timestamp freshness window
- Nonce-based replay protection
- Multi-signature governance`,
    codeExample: `import { SpiralverseProtocol } from '@spiralverse/core';

const sdk = new SpiralverseProtocol(secrets);

const envelope = sdk.createEnvelope(
  SacredTongue.KO,           // Origin tongue
  [SacredTongue.RU],         // Required tongues
  { action: 'move_arm', params: { x: 10, y: 20 } }
);

const isValid = sdk.verifyEnvelope(envelope, requiredTongues);`,
    relatedAxioms: [7, 8]
  }
];

const CATEGORY_INFO: Record<Category, { label: string; icon: React.FC<{ size: number; className?: string }>; color: string }> = {
  axioms: { label: 'Core Axioms', icon: Target, color: 'text-pink-400' },
  sacred_tongues: { label: 'Sacred Tongues', icon: Sparkles, color: 'text-yellow-400' },
  architecture: { label: 'Architecture', icon: Layers, color: 'text-blue-400' },
  tutorials: { label: 'Tutorials', icon: GraduationCap, color: 'text-green-400' },
  api: { label: 'API Reference', icon: Code, color: 'text-purple-400' }
};

export const KnowledgeBaseApp: React.FC = () => {
  const [selectedCategory, setSelectedCategory] = useState<Category | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<DocEntry | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [copiedCode, setCopiedCode] = useState(false);

  const filteredDocs = KNOWLEDGE_BASE.filter(doc => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return doc.title.toLowerCase().includes(query) ||
             doc.summary.toLowerCase().includes(query) ||
             doc.content.toLowerCase().includes(query);
    }
    if (selectedCategory) {
      return doc.category === selectedCategory;
    }
    return true;
  });

  const copyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  return (
    <div className="h-full w-full bg-zinc-900 flex text-white overflow-hidden">
      {/* Sidebar */}
      <div className="w-64 bg-zinc-800 border-r border-zinc-700 flex flex-col">
        <div className="p-4 border-b border-zinc-700">
          <div className="flex items-center gap-2 mb-4">
            <BookOpen size={20} className="text-emerald-400" />
            <h2 className="font-black">Knowledge Base</h2>
          </div>
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setSelectedCategory(null); }}
              placeholder="Search docs..."
              className="w-full bg-zinc-700 rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
          </div>
        </div>

        <div className="flex-1 overflow-auto p-2">
          <button
            onClick={() => { setSelectedCategory(null); setSearchQuery(''); }}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-2 ${
              !selectedCategory && !searchQuery ? 'bg-zinc-700' : 'hover:bg-zinc-700/50'
            }`}
          >
            All Documents
          </button>

          {(Object.entries(CATEGORY_INFO) as [Category, typeof CATEGORY_INFO['axioms']][]).map(([cat, info]) => {
            const Icon = info.icon;
            const count = KNOWLEDGE_BASE.filter(d => d.category === cat).length;
            return (
              <button
                key={cat}
                onClick={() => { setSelectedCategory(cat); setSearchQuery(''); }}
                className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center justify-between ${
                  selectedCategory === cat ? 'bg-zinc-700' : 'hover:bg-zinc-700/50'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Icon size={14} className={info.color} />
                  <span>{info.label}</span>
                </div>
                <span className="text-xs text-zinc-500">{count}</span>
              </button>
            );
          })}
        </div>

        <div className="p-3 border-t border-zinc-700 text-[10px] text-zinc-500">
          USPTO #63/961,403
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex">
        {/* Document List */}
        <div className="w-80 border-r border-zinc-700 overflow-auto">
          <div className="p-3 border-b border-zinc-700 bg-zinc-800/50">
            <span className="text-xs font-bold uppercase tracking-widest text-zinc-500">
              {searchQuery ? `Search: "${searchQuery}"` :
               selectedCategory ? CATEGORY_INFO[selectedCategory].label : 'All Documents'}
              {' '}({filteredDocs.length})
            </span>
          </div>
          <div className="p-2 space-y-1">
            {filteredDocs.map(doc => {
              const Icon = doc.icon;
              const catInfo = CATEGORY_INFO[doc.category];
              return (
                <button
                  key={doc.id}
                  onClick={() => setSelectedDoc(doc)}
                  className={`w-full text-left p-3 rounded-lg transition-all ${
                    selectedDoc?.id === doc.id ? 'bg-emerald-600/20 border border-emerald-500/50' : 'hover:bg-zinc-800'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <Icon size={16} className={catInfo.color} />
                    <div>
                      <div className="font-bold text-sm">{doc.title}</div>
                      <div className="text-[10px] text-zinc-500 line-clamp-2">{doc.summary}</div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Document View */}
        <div className="flex-1 overflow-auto">
          {selectedDoc ? (
            <div className="p-6 max-w-3xl">
              <div className="flex items-center gap-2 text-xs text-zinc-500 mb-2">
                <span className={CATEGORY_INFO[selectedDoc.category].color}>
                  {CATEGORY_INFO[selectedDoc.category].label}
                </span>
                {selectedDoc.relatedAxioms && (
                  <>
                    <ChevronRight size={12} />
                    <span>Related: {selectedDoc.relatedAxioms.map(a => `Axiom ${a}`).join(', ')}</span>
                  </>
                )}
              </div>

              <h1 className="text-2xl font-black mb-4">{selectedDoc.title}</h1>

              <div className="prose prose-invert prose-sm max-w-none">
                {selectedDoc.content.split('\n\n').map((para, i) => {
                  if (para.startsWith('```')) {
                    const code = para.replace(/```\w*\n?/g, '').trim();
                    return (
                      <div key={i} className="relative my-4">
                        <pre className="bg-zinc-800 rounded-lg p-4 overflow-x-auto text-sm">
                          <code>{code}</code>
                        </pre>
                      </div>
                    );
                  }
                  if (para.startsWith('|')) {
                    // Simple table rendering
                    const rows = para.split('\n').filter(r => r.trim());
                    return (
                      <table key={i} className="w-full my-4 text-sm">
                        <tbody>
                          {rows.map((row, ri) => {
                            if (row.includes('---')) return null;
                            const cells = row.split('|').filter(c => c.trim());
                            const Tag = ri === 0 ? 'th' : 'td';
                            return (
                              <tr key={ri} className={ri === 0 ? 'bg-zinc-800' : 'border-b border-zinc-700'}>
                                {cells.map((cell, ci) => (
                                  <Tag key={ci} className="px-3 py-2 text-left">{cell.trim().replace(/\*\*/g, '')}</Tag>
                                ))}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    );
                  }
                  // Regular paragraph with markdown-like formatting
                  const formatted = para
                    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
                    .replace(/`([^`]+)`/g, '<code class="bg-zinc-800 px-1 rounded">$1</code>');
                  return (
                    <p key={i} className="mb-4 leading-relaxed" dangerouslySetInnerHTML={{ __html: formatted }} />
                  );
                })}
              </div>

              {selectedDoc.codeExample && (
                <div className="mt-6">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold uppercase tracking-widest text-zinc-500">Code Example</span>
                    <button
                      onClick={() => copyCode(selectedDoc.codeExample!)}
                      className="flex items-center gap-1 text-xs text-zinc-400 hover:text-white"
                    >
                      {copiedCode ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                      {copiedCode ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  <pre className="bg-zinc-800 rounded-lg p-4 overflow-x-auto text-sm border border-zinc-700">
                    <code className="text-emerald-400">{selectedDoc.codeExample}</code>
                  </pre>
                </div>
              )}

              {selectedDoc.relatedAxioms && selectedDoc.relatedAxioms.length > 0 && (
                <div className="mt-6 p-4 bg-zinc-800 rounded-lg border border-zinc-700">
                  <h3 className="font-bold text-sm mb-2 flex items-center gap-2">
                    <Lightbulb size={14} className="text-yellow-400" />
                    Related Axioms
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedDoc.relatedAxioms.map(num => {
                      const related = KNOWLEDGE_BASE.find(d => d.id === `axiom-${num}`);
                      return (
                        <button
                          key={num}
                          onClick={() => related && setSelectedDoc(related)}
                          className="px-3 py-1 bg-zinc-700 rounded-lg text-xs hover:bg-zinc-600 flex items-center gap-1"
                        >
                          Axiom {num}
                          <ArrowRight size={10} />
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-zinc-500">
              <div className="text-center">
                <BookOpen size={48} className="mx-auto mb-4 opacity-50" />
                <p className="text-lg">Select a document to view</p>
                <p className="text-sm">Everything links back to the core SCBE axioms</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
