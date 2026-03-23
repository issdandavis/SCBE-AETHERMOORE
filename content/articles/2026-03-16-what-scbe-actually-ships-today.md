# What SCBE Actually Ships Today: Kernel, Control Plane, and Creative Foundry

**Issac Daniel Davis** | SCBE-AETHERMOORE | 2026-03-16

## The narrow claim

SCBE-AETHERMOORE is not one app.

It is a monorepo with three distinct layers that keep getting mistaken for one another:

- a TypeScript kernel
- a Python control plane
- a creative production lane

That distinction matters, because people read the repo and either think it is "just a math/security library" or "just a pile of scripts." It is neither.

## Layer 1: the kernel

The real library surface starts at:

- `src/index.ts`

From there, the core exports break down into the actual SCBE primitives:

- `src/harmonic/index.ts`
- `src/crypto/index.ts`
- `src/governance/index.ts`

This is the part of the repo that defines the underlying math, crypto, and governance surface. If the question is "what does SCBE mean as a package or reusable system," this is where the answer starts.

That is also why repo summaries that only focus on Python are incomplete. The TypeScript lane is still the kernel.

## Layer 2: the control plane

The newer runtime/control plane is the FastAPI lane in:

- `src/api/main.py`

That is where the repo starts to look like a service platform instead of a pure library. HYDRA routes, mesh routes, storage, and the newer flock/SaaS-facing paths live here.

There is also an older governance API in:

- `api/main.py`

That older service still matters, but it is a different lane. It exposes the `/v1` authorization, registration, consensus, and audit surface rather than the newer control-plane shape. Treating those two files as the same app is how people get lost.

## Layer 3: the operator lane

A large percentage of the repo's real work does not begin in an app server. It begins in scripts.

The practical operator surface is:

- `scripts/hydra_command_center.ps1`

From there, the repo fans out into:

- browser operations
- automation
- training jobs
- packaging
- webtoon generation
- Hugging Face publishing
- admin and repair flows

This is why the repo can feel messy on first read. A lot of the working system behavior is script-first instead of UI-first.

## Layer 4: the delivery surfaces

The user-facing web/mobile lane is:

- `kindle-app/www/`

Two files matter most for orientation:

- `kindle-app/www/reader.html`
- `kindle-app/www/polly-pad.html`

`reader.html` is the reading lane. `polly-pad.html` is the wider phone shell.

So if someone asks where the "product UI" is, the answer is not the same as where the kernel is. It is in the Kindle/mobile web surface.

## Layer 5: the creative foundry

The repo also contains a governed creative production system:

- `artifacts/webtoon/`
- `scripts/webtoon_gen.py`
- `scripts/webtoon_quality_gate.py`
- `scripts/render_full_book_router.py`
- `scripts/build_webtoon_lock_packet.py`

This is the lane that turns prose into storyboard packets, packets into prompts, prompts into governed renders, and renders into a phone-readable chapter flow.

That does not make the repo "a webtoon app." It means the same repo also contains a production foundry built on top of the kernel and operator layers.

## Why the structure feels confusing

The confusion is understandable because the repo mixes:

- reusable primitives
- runtime services
- operator scripts
- product delivery surfaces
- generated artifacts

and it keeps all of them in one place.

A cleaner mental model is:

- `src/` = source of real behavior
- `scripts/` = operational glue and execution
- `kindle-app/www/` = delivery/UI lane
- `artifacts/` = outputs and production state

Once you separate those categories, the repo stops looking chaotic and starts looking layered.

## The shortest accurate map

If you only need the practical read:

- kernel: `src/index.ts`
- control plane: `src/api/main.py`
- older governance API: `api/main.py`
- operator command center: `scripts/hydra_command_center.ps1`
- current webtoon lane: `artifacts/webtoon/production_bible.md` plus `scripts/render_full_book_router.py`

That is the repo in one screen.

## Conclusion

SCBE-AETHERMOORE is best understood as a layered monorepo:

- kernel at the bottom
- control plane above it
- operator scripts around it
- delivery surfaces at the edge
- creative production on top

If you start from that model, the repo becomes readable. If you assume it is one app, almost every path through it looks wrong.

## References

- `src/index.ts`
- `src/harmonic/index.ts`
- `src/crypto/index.ts`
- `src/governance/index.ts`
- `src/api/main.py`
- `api/main.py`
- `scripts/hydra_command_center.ps1`
- `kindle-app/www/reader.html`
- `kindle-app/www/polly-pad.html`
- `artifacts/webtoon/production_bible.md`
- `scripts/render_full_book_router.py`
