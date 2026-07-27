/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */
import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Code,
  Copy,
  GitBranch,
  Layers3,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

export const RUBIX_FACES = [
  {
    label: 'HTML',
    role: 'Structure',
    question: 'Semantic and accessible?',
    color: 'bg-sky-400',
    text: 'text-sky-950',
  },
  {
    label: 'CSS',
    role: 'Style',
    question: 'Portable and scoped?',
    color: 'bg-fuchsia-400',
    text: 'text-fuchsia-950',
  },
  {
    label: 'JS',
    role: 'Behavior',
    question: 'Minimal and inspectable?',
    color: 'bg-amber-300',
    text: 'text-amber-950',
  },
  {
    label: 'SCBE',
    role: 'Governance',
    question: 'Provenance attached?',
    color: 'bg-emerald-400',
    text: 'text-emerald-950',
  },
  {
    label: 'UX',
    role: 'Handoff',
    question: 'Human-readable?',
    color: 'bg-rose-400',
    text: 'text-rose-950',
  },
  {
    label: 'API',
    role: 'Ingest',
    question: 'Dependencies explicit?',
    color: 'bg-violet-400',
    text: 'text-violet-950',
  },
] as const;

export const PROMPT_CARD = `<section class="scbe-artifact" data-format="html-response">
  <header><h2>Make the answer runnable</h2></header>
  <p>Return semantic HTML first, then CSS and JS blocks only when needed.</p>
  <button data-action="copy">Copy artifact</button>
</section>`;

export const STATE_DIMENSIONS = [
  {
    index: 0,
    symbol: 'v1',
    name: 'Identity',
    status: 'evidence_bound',
    detail: 'Packet source and app route are bound as identity evidence.',
  },
  {
    index: 1,
    symbol: 'v2',
    name: 'Intent phase',
    status: 'evidence_bound',
    detail: 'Declared intent is bound; the numeric phase is derived by the gate.',
  },
  {
    index: 2,
    symbol: 'v3',
    name: 'Trajectory',
    status: 'runtime_required',
    detail: 'The trusted runtime supplies trajectory history and its EWMA.',
  },
  {
    index: 3,
    symbol: 'v4',
    name: 'Linear time',
    status: 'runtime_required',
    detail: 'The gate binds a real, monotonic time value.',
  },
  {
    index: 4,
    symbol: 'v5',
    name: 'Commitment',
    status: 'runtime_required',
    detail: 'A key-derived commitment hash is generated outside the browser.',
  },
  {
    index: 5,
    symbol: 'v6',
    name: 'Signature',
    status: 'runtime_required',
    detail: 'Signature validity comes from a trusted verifier.',
  },
  {
    index: 6,
    symbol: 'tau',
    name: 'Time flow',
    status: 'runtime_required',
    detail: 'The state engine derives dilated time from the runtime clock.',
  },
  {
    index: 7,
    symbol: 'eta',
    name: 'Entropy',
    status: 'runtime_required',
    detail: 'Entropy is computed from the completed context vector.',
  },
  {
    index: 8,
    symbol: 'q',
    name: 'Quantum state',
    status: 'runtime_required',
    detail: 'The normalized complex state is evolved under Hamiltonian H.',
  },
] as const;

export const STATE_VECTOR_REQUEST = {
  schema: 'scbe_9d_state_request.v1',
  status: 'runtime_required',
  engine: 'src/symphonic_cipher/scbe_aethermoore/unified.py#SCBEAethermoore.create_state',
  vector_layout: {
    context: 'xi[0..5]',
    time: 'xi[6]',
    entropy: 'xi[7]',
    quantum: 'xi[8]',
  },
  bound_evidence: {
    identity: ['source', 'website_app', 'registry_tile'],
    intent: ['principle', 'rubix_faces', 'governance_checks'],
  },
  runtime_inputs: [
    'trajectory EWMA',
    'monotonic Unix time t',
    'key-derived commitment hash',
    'trusted signature validity',
    'Hamiltonian H',
  ],
  serialization: {
    complex: '{ real, imag }',
    python_dtype: 'object',
  },
  guardrails: [
    'Preserve mixed real and complex values with dtype object.',
    'Convert complex context values to magnitudes before entropy estimation.',
    'Normalize q before governance evaluation.',
    'Use real, monotonic runtime time for v4 and tau.',
  ],
  dimensions: STATE_DIMENSIONS.map(({ index, symbol, name, status }) => ({
    index,
    symbol,
    name,
    status,
  })),
  governance_decision: 'not_evaluated',
} as const;
export const HANDOFF_PACKET_SCHEMA = {
  packet: 'html_response_rubix_bridge',
  version: '2026-07-12',
  source: 'https://youtu.be/f39MnczcJZA?si=eC6znn9yMfGmnnFF',
  principle:
    'When AI output is meant to become software, ask for portable semantic HTML artifacts instead of markdown-only prose.',
  rubix_faces: RUBIX_FACES.map((face) => face.label),
  copy_targets: ['prompt', 'handoff_packet'],
  governance_checks: [
    'Provenance is captured before reuse.',
    'Generated HTML is reviewed as untrusted input.',
    'Scripts are sandboxed or removed before embedding.',
    'Copy/export affordances are explicit for cross-agent handoff.',
  ],
  state_vector_request: STATE_VECTOR_REQUEST,
  website_app: 'scbe-visual-system/components/apps/HtmlBridgeApp.tsx',
  registry_tile: 'scbe-visual-system/apps-registry.json#ai-workspace/htmlbridge',
};

export const HANDOFF_PACKET = JSON.stringify(HANDOFF_PACKET_SCHEMA, null, 2);

type CopyTarget = 'prompt' | 'handoff packet';
type CopyStatus = { kind: 'copied' | 'blocked'; target: CopyTarget } | null;

const checkpoints = [
  'Ask for semantic HTML when the answer should become an interface.',
  'Keep the artifact portable: explicit data attributes and no hidden dependencies.',
  'Review provenance, links, script scope, and handoff metadata before reuse.',
];

const buttonClassName =
  'inline-flex items-center gap-2 rounded-full px-4 py-2 text-[11px] font-black uppercase tracking-[0.16em] transition hover:-translate-y-0.5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950';

export const HtmlBridgeApp: React.FC = () => {
  const [copyStatus, setCopyStatus] = useState<CopyStatus>(null);

  const copyText = async (target: CopyTarget, value: string) => {
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error('Clipboard API unavailable');
      }
      await navigator.clipboard.writeText(value);
      setCopyStatus({ kind: 'copied', target });
    } catch {
      setCopyStatus({ kind: 'blocked', target });
    }
  };

  const targetLabel = copyStatus?.target === 'prompt' ? 'Prompt' : 'Handoff packet';
  const packetNeedsManualCopy =
    copyStatus?.kind === 'blocked' && copyStatus.target === 'handoff packet';

  return (
    <div className="h-full overflow-auto bg-[#06070d] text-white selection:bg-sky-300 selection:text-sky-950">
      <section
        aria-labelledby="html-bridge-title"
        className="relative min-h-full p-4 sm:p-6 md:p-8"
      >
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_#38bdf8,_transparent_28%),radial-gradient(circle_at_bottom_right,_#a855f7,_transparent_30%)] opacity-25"
        />
        <div className="relative z-10 grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="min-w-0 rounded-[2rem] border border-white/10 bg-black/55 p-5 shadow-2xl backdrop-blur sm:p-6">
            <div className="mb-6 flex items-start gap-3">
              <div className="rounded-2xl bg-sky-400/15 p-3 text-sky-300">
                <Code aria-hidden="true" size={28} />
              </div>
              <div>
                <p className="text-[10px] font-black uppercase tracking-[0.34em] text-sky-300">
                  Portable artifact relay
                </p>
                <h1
                  id="html-bridge-title"
                  className="text-3xl font-black uppercase italic md:text-5xl"
                >
                  HTML Response Bridge
                </h1>
              </div>
            </div>
            <p className="max-w-3xl text-base leading-relaxed text-zinc-200 sm:text-lg">
              Turn model output into a governed interface artifact that can move between agents,
              apps, and reviewers without losing its source, safety checks, or dependencies.
            </p>
            <ol className="mt-6 grid gap-3 md:grid-cols-3" aria-label="Artifact relay steps">
              {checkpoints.map((item, index) => (
                <li key={item} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="mb-3 font-mono text-xs font-black uppercase tracking-widest text-emerald-300">
                    Relay {index + 1}
                  </p>
                  <p className="text-sm leading-relaxed text-zinc-300">{item}</p>
                </li>
              ))}
            </ol>
          </div>

          <div className="min-w-0 rounded-[2rem] border border-white/10 bg-white/[0.04] p-5 shadow-2xl sm:p-6">
            <div className="mb-5 flex items-center gap-3">
              <Layers3 aria-hidden="true" className="text-amber-300" />
              <div>
                <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-zinc-500">
                  Six checks
                </p>
                <h2 className="text-xl font-black uppercase tracking-widest">Rubix face gate</h2>
              </div>
            </div>
            <ol
              className="grid grid-cols-2 gap-2 sm:grid-cols-3"
              aria-label="Rubix artifact checks"
            >
              {RUBIX_FACES.map((face, index) => (
                <li key={face.label} className="rounded-2xl border border-white/10 bg-black/45 p-3">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <span
                      className={`${face.color} ${face.text} rounded-lg px-2 py-1 font-mono text-[10px] font-black`}
                    >
                      {face.label}
                    </span>
                    <span className="font-mono text-[10px] text-zinc-600">0{index + 1}</span>
                  </div>
                  <p className="text-xs font-bold text-zinc-200">{face.role}</p>
                  <p className="mt-1 text-[11px] leading-relaxed text-zinc-500">{face.question}</p>
                </li>
              ))}
            </ol>
            <p className="mt-5 text-sm leading-relaxed text-zinc-300">
              Ship only when every face is answered. A missing face means the artifact is not ready
              for cross-system use.
            </p>
          </div>

          <div className="min-w-0 rounded-[2rem] border border-amber-300/20 bg-amber-300/[0.05] p-5 xl:col-span-2 sm:p-6">
            <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <Activity aria-hidden="true" className="text-amber-300" />
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-zinc-500">
                    Evidence before evaluation
                  </p>
                  <h2 className="text-xl font-black uppercase tracking-widest">
                    9D state preflight
                  </h2>
                </div>
              </div>
              <span className="rounded-full border border-amber-300/30 bg-amber-300/10 px-3 py-1 font-mono text-[10px] font-black uppercase tracking-widest text-amber-200">
                Runtime evaluation required
              </span>
            </div>
            <p className="max-w-4xl text-sm leading-relaxed text-zinc-300">
              This packet binds identity and declared intent as evidence. It does not manufacture a
              browser-side xi vector or governance score; the trusted SCBE runtime derives and
              evaluates all numeric state.
            </p>
            <ol
              className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"
              aria-label="SCBE 9D state dimensions"
            >
              {STATE_DIMENSIONS.map((dimension) => {
                const isBound = dimension.status === 'evidence_bound';
                return (
                  <li
                    key={dimension.symbol}
                    className="rounded-2xl border border-white/10 bg-black/40 p-3"
                  >
                    <div className="mb-2 flex items-center justify-between gap-2 font-mono text-[10px]">
                      <span className="font-black text-zinc-400">D{dimension.index + 1}</span>
                      <span className="text-amber-200">{dimension.symbol}</span>
                    </div>
                    <p className="text-xs font-black uppercase tracking-wide text-white">
                      {dimension.name}
                    </p>
                    <p
                      className={`mt-2 text-[10px] font-black uppercase tracking-wider ${isBound ? 'text-emerald-300' : 'text-amber-300'}`}
                    >
                      {isBound ? 'Evidence bound' : 'Gate runtime'}
                    </p>
                    <p className="mt-2 text-[11px] leading-relaxed text-zinc-500">
                      {dimension.detail}
                    </p>
                  </li>
                );
              })}
            </ol>
            <p className="mt-4 break-all font-mono text-[11px] leading-relaxed text-zinc-400">
              Decision: <span className="font-black text-amber-200">not_evaluated</span> | Engine:
              SCBEAethermoore.create_state
            </p>
          </div>
          <div className="min-w-0 rounded-[2rem] border border-white/10 bg-zinc-950 p-5 xl:col-span-2 sm:p-6">
            <div className="mb-4 flex flex-wrap items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <Sparkles aria-hidden="true" className="text-fuchsia-300" />
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.28em] text-zinc-500">
                    Ready to relay
                  </p>
                  <h2 className="text-xl font-black uppercase tracking-widest">Artifact source</h2>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => copyText('prompt', PROMPT_CARD)}
                  className={`${buttonClassName} bg-sky-400 text-sky-950 hover:bg-sky-300`}
                >
                  <Copy aria-hidden="true" size={14} />
                  Copy prompt
                </button>
                <button
                  type="button"
                  onClick={() => copyText('handoff packet', HANDOFF_PACKET)}
                  className={`${buttonClassName} bg-violet-400 text-violet-950 hover:bg-violet-300`}
                >
                  <GitBranch aria-hidden="true" size={14} />
                  Copy packet
                </button>
              </div>
            </div>

            {copyStatus ? (
              <div
                id="copy-status"
                role={copyStatus.kind === 'blocked' ? 'alert' : 'status'}
                aria-live="polite"
                className={`mb-4 flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm ${
                  copyStatus.kind === 'blocked'
                    ? 'border-amber-300/30 bg-amber-300/10 text-amber-100'
                    : 'border-emerald-400/30 bg-emerald-400/10 text-emerald-100'
                }`}
              >
                {copyStatus.kind === 'blocked' ? (
                  <AlertTriangle aria-hidden="true" className="mt-0.5 shrink-0" size={16} />
                ) : (
                  <CheckCircle2 aria-hidden="true" className="mt-0.5 shrink-0" size={16} />
                )}
                <p>
                  {copyStatus.kind === 'blocked'
                    ? `Clipboard unavailable. Select the ${copyStatus.target} below and copy it manually.`
                    : `${targetLabel} copied for cross-system use.`}
                </p>
              </div>
            ) : null}

            <pre
              tabIndex={0}
              aria-label="Reusable HTML artifact prompt"
              className="overflow-auto rounded-2xl border border-white/10 bg-black p-5 font-mono text-sm leading-relaxed text-sky-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-300"
            >
              <code>{PROMPT_CARD}</code>
            </pre>

            <div className="mt-5 grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl bg-white/[0.04] p-4">
                <Copy aria-hidden="true" className="mb-2 text-sky-300" />
                <p className="text-sm text-zinc-300">
                  Copy the prompt when the answer should become a runnable interface.
                </p>
              </div>
              <div className="rounded-2xl bg-white/[0.04] p-4">
                <ShieldCheck aria-hidden="true" className="mb-2 text-emerald-300" />
                <p className="text-sm text-zinc-300">
                  Treat generated UI as untrusted until it is reviewed and sandboxed.
                </p>
              </div>
              <div className="rounded-2xl bg-white/[0.04] p-4">
                <GitBranch aria-hidden="true" className="mb-2 text-violet-300" />
                <p className="text-sm text-zinc-300">
                  Attach the packet so the next system receives the same contract.
                </p>
              </div>
            </div>

            <details
              open={packetNeedsManualCopy}
              className="mt-5 rounded-2xl border border-white/10 bg-black p-4"
            >
              <summary className="cursor-pointer text-xs font-black uppercase tracking-widest text-violet-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-300">
                View canonical handoff packet
              </summary>
              <pre
                tabIndex={0}
                aria-label="Canonical JSON handoff packet"
                className="mt-4 overflow-auto font-mono text-xs leading-relaxed text-violet-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-300"
              >
                <code>{HANDOFF_PACKET}</code>
              </pre>
            </details>
          </div>
        </div>
      </section>
    </div>
  );
};
