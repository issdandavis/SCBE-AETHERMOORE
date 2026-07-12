/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */
import React from 'react';
import { Code, Copy, GitBranch, Layers3, ShieldCheck, Sparkles } from 'lucide-react';

const RUBIX_FACES = [
  { label: 'HTML', color: 'bg-sky-400', text: 'text-sky-950' },
  { label: 'CSS', color: 'bg-fuchsia-400', text: 'text-fuchsia-950' },
  { label: 'JS', color: 'bg-amber-300', text: 'text-amber-950' },
  { label: 'SCBE', color: 'bg-emerald-400', text: 'text-emerald-950' },
  { label: 'UX', color: 'bg-rose-400', text: 'text-rose-950' },
  { label: 'API', color: 'bg-violet-400', text: 'text-violet-950' },
];

const PROMPT_CARD = `<section class="scbe-artifact" data-format="html-response">
  <header><h2>Make the answer runnable</h2></header>
  <p>Return semantic HTML first, then CSS and JS blocks only when needed.</p>
  <button data-action="copy">Copy artifact</button>
</section>`;

const checkpoints = [
  'Ask the model for semantic HTML instead of long markdown when the result should become an interface.',
  'Keep each answer portable: one artifact, explicit data attributes, no hidden dependencies, and clear copy/export affordances.',
  'Run every artifact through the SCBE gate: provenance, safe links, sandboxed script scope, and cross-system handoff metadata.',
];

export const HtmlBridgeApp: React.FC = () => {
  return (
    <div className="h-full overflow-auto bg-[#06070d] text-white">
      <section className="relative min-h-full p-6 md:p-8">
        <div className="absolute inset-0 opacity-30 bg-[radial-gradient(circle_at_top_left,_#38bdf8,_transparent_28%),radial-gradient(circle_at_bottom_right,_#a855f7,_transparent_30%)]" />
        <div className="relative z-10 grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-[2rem] border border-white/10 bg-black/45 p-6 shadow-2xl backdrop-blur">
            <div className="mb-6 flex items-center gap-3">
              <div className="rounded-2xl bg-sky-400/15 p-3 text-sky-300">
                <Code size={28} />
              </div>
              <div>
                <p className="text-[10px] font-black uppercase tracking-[0.4em] text-sky-300">
                  Video note applied
                </p>
                <h1 className="text-3xl font-black uppercase italic md:text-5xl">
                  HTML Response Bridge
                </h1>
              </div>
            </div>
            <p className="max-w-3xl text-lg leading-relaxed text-zinc-200">
              The linked video's core idea — AI responses can become direct HTML interfaces, not
              just markdown notes — is now captured as a website-native workspace. Use it to turn
              model output into governed, portable UI artifacts that can move between agents, apps,
              and review systems.
            </p>
            <div className="mt-6 grid gap-3 md:grid-cols-3">
              {checkpoints.map((item, index) => (
                <div key={item} className="rounded-2xl border border-white/10 bg-white/[0.04] p-4">
                  <p className="mb-3 text-xs font-black uppercase tracking-widest text-emerald-300">
                    0{index + 1}
                  </p>
                  <p className="text-sm leading-relaxed text-zinc-300">{item}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-white/[0.04] p-6 shadow-2xl">
            <div className="mb-5 flex items-center gap-3">
              <Layers3 className="text-amber-300" />
              <h2 className="text-xl font-black uppercase tracking-widest">Code Rubix Cube</h2>
            </div>
            <div className="grid grid-cols-3 gap-2 rounded-3xl bg-black/50 p-3">
              {Array.from({ length: 27 }).map((_, index) => {
                const face = RUBIX_FACES[index % RUBIX_FACES.length];
                return (
                  <div
                    key={index}
                    className={`${face.color} ${face.text} flex aspect-square items-center justify-center rounded-xl text-[10px] font-black shadow-inner`}
                  >
                    {face.label}
                  </div>
                );
              })}
            </div>
            <p className="mt-5 text-sm leading-relaxed text-zinc-300">
              Each face represents a transformation layer: content, style, behavior, governance,
              usability, and API handoff. Rotate the cube mentally before shipping: if any face is
              missing, the artifact is not ready for cross-system use.
            </p>
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-zinc-950 p-6 xl:col-span-2">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <Sparkles className="text-fuchsia-300" />
                <h2 className="text-xl font-black uppercase tracking-widest">
                  Reusable Artifact Prompt
                </h2>
              </div>
              <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-[10px] font-black uppercase tracking-widest text-emerald-200">
                Cross-system ready
              </span>
            </div>
            <pre className="overflow-auto rounded-2xl border border-white/10 bg-black p-5 text-sm leading-relaxed text-sky-100">
              <code>{PROMPT_CARD}</code>
            </pre>
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl bg-white/[0.04] p-4">
                <Copy className="mb-2 text-sky-300" />
                <p className="text-sm text-zinc-300">
                  Copy/paste into prompts when you want runnable HTML output.
                </p>
              </div>
              <div className="rounded-2xl bg-white/[0.04] p-4">
                <ShieldCheck className="mb-2 text-emerald-300" />
                <p className="text-sm text-zinc-300">
                  Treat generated UI as untrusted until reviewed and sandboxed.
                </p>
              </div>
              <div className="rounded-2xl bg-white/[0.04] p-4">
                <GitBranch className="mb-2 text-violet-300" />
                <p className="text-sm text-zinc-300">
                  Attach provenance so Codex, Gemini, and browser agents can reuse it safely.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
