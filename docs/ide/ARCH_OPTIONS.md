# SCBE-AETHERMOORE IDE: Architecture Options

**Date**: 2026-02-19
**Status**: Research / RFC
**Authors**: SCBE Core Team
**Scope**: Technology selection for the SCBE-governed IDE shell, editor engine, and backend runtime

---

## Table of Contents

1. [Core Shell: Tauri vs Electron](#1-core-shell-tauri-vs-electron)
2. [Editor Engine: Monaco vs CodeMirror 6](#2-editor-engine-monaco-vs-codemirror-6)
3. [Backend Runtime: Rust vs Node](#3-backend-runtime-rust-vs-node)
4. [Competitive Teardown](#4-competitive-teardown)
5. [Weighted Decision Matrix](#5-weighted-decision-matrix)
6. [Recommendation](#6-recommendation)

---

## 1. Core Shell: Tauri vs Electron

### Overview

| Attribute | Tauri v2 (2.x, stable Oct 2024) | Electron (v33+, Chromium 130+) |
|---|---|---|
| Language | Rust backend + WebView frontend | Node.js backend + Chromium frontend |
| Rendering | OS-native WebView2 (Win), WebKit (macOS/Linux) | Bundled Chromium |
| Current Version | 2.2.x (Feb 2025) | 33.x / 34.x (Q1 2025) |
| License | MIT / Apache 2.0 | MIT |

### Bundle Size

| Metric | Tauri v2 | Electron |
|---|---|---|
| Hello-world installer (Windows) | ~3-6 MB | ~85-120 MB |
| Hello-world installer (macOS) | ~5-8 MB | ~90-130 MB |
| Delta update payload | ~2-4 MB (OS webview reused) | ~60+ MB (full Chromium) |

Tauri does not bundle a browser engine. On Windows 11, WebView2 is pre-installed as a system component. On macOS, WebKit ships with the OS. On Linux, WebKitGTK is a system dependency. This means Tauri installers are **10-20x smaller** than Electron equivalents.

For an IDE that users install alongside other dev tools, the 80+ MB Electron overhead is tolerable (VS Code is ~100 MB). But Tauri's small footprint is a meaningful differentiator for auto-update speed and for distribution in bandwidth-constrained environments.

### Memory Footprint

| Metric | Tauri v2 | Electron |
|---|---|---|
| Idle (empty window) | ~30-50 MB RSS | ~80-150 MB RSS |
| Moderate workload (editor + file tree) | ~80-150 MB | ~250-400 MB |
| Heavy workload (multiple tabs, LSP, terminal) | ~200-350 MB | ~500-900 MB |

Electron runs a full Chromium multi-process architecture: a main browser process, one GPU process, and one renderer process per window. Each renderer carries V8, Blink, and the full Chromium networking stack. Tauri uses a single native WebView process plus the Rust backend process, with far lower baseline overhead.

For an IDE that must coexist with language servers, Docker, and the user's project processes, the memory delta is significant. **Tauri's lower baseline leaves more headroom for LSP processes and file indexing.**

### Startup Time

| Metric | Tauri v2 | Electron |
|---|---|---|
| Cold start (first launch) | ~0.5-1.5s | ~2-4s |
| Warm start (cached) | ~0.3-0.8s | ~1-2s |

Tauri's Rust binary initializes faster than Electron's Node.js + Chromium bootstrap. For an IDE, perceived startup time matters for developer satisfaction, though both are acceptable.

### Native API Access

| Capability | Tauri v2 | Electron |
|---|---|---|
| Filesystem | Full via Rust + IPC commands | Full via Node.js `fs` |
| Crypto (OpenSSL / ring) | Native Rust crates (ring, rustls) | Node.js `crypto` module |
| Process management | `std::process`, tokio | `child_process`, node-pty |
| System tray | Built-in plugin | Built-in |
| Shell integration | Plugin | Full Node.js access |
| Native menus | Built-in | Built-in |
| Auto-updater | Built-in plugin (differential) | electron-updater |
| Notifications | Built-in plugin | Built-in |
| Clipboard | Built-in plugin | Built-in |
| Global shortcuts | Built-in plugin | Built-in |

Both frameworks provide comprehensive native access. Tauri's advantage: native APIs run in Rust with no serialization overhead for compute-heavy operations (file indexing, crypto). Electron's advantage: Node.js has a larger ecosystem of npm packages for native operations.

**Critical for SCBE**: The post-quantum crypto layer (ML-KEM-768, ML-DSA-65) currently uses Node.js bindings to liboqs. In Tauri, this would use the `pqcrypto` Rust crate or FFI to liboqs -- both are mature. The Rust `pqcrypto` crate wraps the same PQClean reference implementations and is arguably more natural than the Node.js bindings.

### Cross-Platform Support

| Platform | Tauri v2 | Electron |
|---|---|---|
| Windows 11 (primary) | Excellent (WebView2 pre-installed) | Excellent |
| Windows 10 | Good (WebView2 auto-installs) | Excellent |
| macOS (Apple Silicon) | Excellent (native WebKit) | Excellent |
| macOS (Intel) | Good | Excellent |
| Linux (x86_64) | Good (WebKitGTK dependency) | Excellent |
| Linux (ARM64) | Experimental | Good |

Electron's bundled Chromium guarantees pixel-identical rendering across platforms. Tauri's reliance on OS WebViews introduces potential rendering differences between WebView2 (Windows), WebKit (macOS), and WebKitGTK (Linux). In practice, modern CSS/JS works consistently, but edge cases exist -- particularly with advanced CSS features and Web APIs.

**Windows 11 primary**: Both are excellent. WebView2 on Windows 11 is a first-class, evergreen component maintained by Microsoft.

### Security Model

| Aspect | Tauri v2 | Electron |
|---|---|---|
| Process isolation | Rust backend + WebView (strict IPC) | Node main + Chromium renderer |
| Default permissions | Deny-all; explicit capability grants | Full Node.js access by default |
| IPC model | Typed commands with permission scoping | `ipcMain`/`ipcRenderer` (ad-hoc) |
| CSP enforcement | Strict by default | Manual configuration |
| Sandbox | WebView is sandboxed; Rust backend is native | Renderer sandbox (optional) |
| Supply chain surface | Smaller (Rust crates, audited) | Larger (npm ecosystem) |

**Tauri's security model is fundamentally stronger.** Its deny-by-default capability system maps directly to SCBE's governance philosophy: every operation requires explicit permission, and the Rust backend acts as a trust boundary. This aligns with SCBE's L13 decision gate (ALLOW/QUARANTINE/ESCALATE/DENY).

In Electron, the renderer process can access Node.js APIs unless explicitly sandboxed, and even with `contextIsolation` and `nodeIntegration: false`, the attack surface is larger. The SCBE extension gate (`agents/extension_gate.py`) would need significant hardening in Electron to match Tauri's built-in isolation.

### Plugin/Extension Architecture Feasibility

| Aspect | Tauri v2 | Electron |
|---|---|---|
| Plugin system | Tauri plugin API (Rust + JS bridge) | Full Node.js module system |
| Extension isolation | Can enforce via Rust IPC boundary | Requires manual sandboxing |
| Hot reload | WebView hot reload; Rust requires restart | Full hot reload |
| WASM support | Native via WebView | Native via Chromium |
| Extension marketplace precedent | None (would be first) | VS Code marketplace model |

For SCBE's signed extension manifests with governance gates, Tauri's architecture is more natural: extensions run in the WebView sandbox, and their API access is mediated through typed Rust commands that can enforce SCBE governance checks at the IPC boundary. In Electron, achieving equivalent isolation requires building a custom sandbox layer.

### Maturity, Community, Ecosystem

| Metric | Tauri v2 | Electron |
|---|---|---|
| GitHub stars | ~88k (Feb 2025) | ~115k |
| npm weekly downloads | ~30k (@tauri-apps/cli) | ~2.5M (electron) |
| Major apps built | 1Password (portions), Cody, Clash Verge | VS Code, Slack, Discord, Figma, Notion |
| Age | v1.0: Jun 2022, v2.0: Oct 2024 | v1.0: May 2014 |
| Documentation quality | Good, improving rapidly | Excellent, mature |
| Stack Overflow questions | ~3k | ~50k+ |

Electron is vastly more mature with a proven track record for IDE-class applications (VS Code). Tauri v2 is production-ready but the ecosystem is younger. Fewer IDE-class reference implementations exist in Tauri.

### Dev Velocity (Rust Learning Curve vs Node Familiarity)

| Aspect | Tauri v2 (Rust backend) | Electron (Node backend) |
|---|---|---|
| Frontend dev velocity | Identical (both use web tech) | Identical |
| Backend dev velocity | Slower (Rust learning curve, borrow checker) | Faster (JavaScript/TypeScript familiarity) |
| Hiring pool | Smaller (Rust developers) | Larger (Node.js developers) |
| Compile times | 30s-2min incremental, 5-15min clean | Instant (interpreted) |
| Debugging | Rust debugger + Chrome DevTools | Chrome DevTools + Node debugger |
| Prototype speed | Moderate (Rust boilerplate) | Fast |

**The Rust learning curve is real but bounded.** For a team already working in TypeScript (SCBE's canonical language), the backend logic (file watching, process management, IPC) requires moderate Rust competence. The SCBE pipeline itself remains TypeScript/Python and runs in the WebView or as a subprocess -- the Rust layer is plumbing, not application logic.

---

## 2. Editor Engine: Monaco vs CodeMirror 6

### Overview

| Attribute | Monaco Editor | CodeMirror 6 |
|---|---|---|
| Origin | Extracted from VS Code (Microsoft) | Marijn Haverbeke (independent) |
| Current Version | 0.52.x (Feb 2025) | 6.x (stable since Jun 2022) |
| License | MIT | MIT |
| Architecture | Monolithic class hierarchy | Modular, functional composition |
| Framework | Standalone (DOM-based) | Standalone (DOM-based) |

### Feature Completeness

| Feature | Monaco | CodeMirror 6 |
|---|---|---|
| IntelliSense / autocomplete | Built-in, VS Code-grade | Via extensions (basic built-in) |
| Multi-cursor editing | Full support | Full support |
| Minimap | Built-in | Community extension |
| Diff view | Built-in (side-by-side, inline) | Community extension (less polished) |
| Find and replace | Full (regex, whole word, case) | Full (regex, case) |
| Code folding | Built-in | Built-in |
| Bracket matching | Built-in | Built-in |
| Syntax highlighting | TextMate grammars (Monarch) | Lezer parser system |
| Inline hints / diagnostics | Built-in | Via extensions |
| Command palette | Built-in | Community extension |
| Drag and drop | Built-in | Via extensions |
| Collaborative editing | Not built-in | Designed for it (OT/CRDT ready) |

Monaco ships with more features out-of-the-box because it is literally the VS Code editor extracted. CodeMirror 6 ships lean and expects you to compose exactly the features you need.

### Bundle Size and Performance

| Metric | Monaco | CodeMirror 6 |
|---|---|---|
| Minimum bundle (gzipped) | ~2.5-4 MB (with workers) | ~150-300 KB (core + basic extensions) |
| Full-featured bundle | ~5-8 MB | ~400-800 KB |
| Initial parse time | ~100-200ms | ~30-80ms |
| Scroll performance (large files) | Good (virtualized) | Excellent (viewport-only rendering) |
| Memory per document (10k lines) | ~15-30 MB | ~5-10 MB |
| 100k+ line files | Handles well | Handles very well |

**CodeMirror 6 is dramatically smaller and faster.** Its modular architecture means you only pay for what you import. Monaco's monolithic design pulls in the entire VS Code editor infrastructure even for basic use cases.

For an IDE that will also run SCBE governance checks, LSP processes, and connector integrations, CodeMirror 6's lighter footprint leaves more resource headroom.

### Customizability and Extensibility

| Aspect | Monaco | CodeMirror 6 |
|---|---|---|
| API design | Object-oriented, VS Code-like | Functional, state-transaction-based |
| Custom views/widgets | Possible but complex | First-class (decorations, panels, widgets) |
| Custom keymaps | Full support | Full support (precedence-based) |
| Theme engine | CSS-based, VS Code themes compatible | Theme facets, highly customizable |
| State management | Internal mutable state | Immutable state transactions (Redux-like) |
| Extension composition | Additive (register providers) | Composable facets and extensions |

CodeMirror 6 was designed from the ground up for extensibility. Its facet/extension system allows clean composition without monkey-patching. This maps well to SCBE's modular architecture: each SCBE layer can be an editor extension that decorates, annotates, or intercepts editor operations.

Monaco's API is powerful but opinionated -- it assumes you want a VS Code-like experience. Deviating from that assumption requires fighting the API.

### Language Server Protocol (LSP) Support

| Aspect | Monaco | CodeMirror 6 |
|---|---|---|
| Built-in LSP client | No (but monaco-languageclient exists) | No (but codemirror-languageserver exists) |
| LSP integration maturity | Mature (monaco-languageclient, widely used) | Growing (less battle-tested) |
| Language support out-of-box | ~30+ languages (syntax highlighting) | ~20+ languages via @codemirror/lang-* |
| Custom language support | Monarch (regex-based tokenizer) | Lezer (incremental LR parser) |

Both require external packages for LSP integration. Monaco has a slight maturity advantage here due to its VS Code heritage. However, the LSP protocol is standardized -- the transport layer is straightforward in either editor.

**Lezer vs Monarch**: CodeMirror 6's Lezer parser system produces actual parse trees (incremental, error-recovering), enabling deeper structural understanding of code. Monaco's Monarch is regex-based tokenization -- fast but shallow. For an AI-governed IDE that needs to understand code structure for governance decisions, Lezer's parse trees are more valuable.

### Theming and Accessibility

| Aspect | Monaco | CodeMirror 6 |
|---|---|---|
| VS Code theme compatibility | Direct (same format) | Requires conversion |
| Dark/light mode | Built-in | Built-in |
| High contrast | Built-in | Via theme extension |
| Screen reader support | Good (VS Code-derived) | Good (ARIA roles, live regions) |
| Keyboard navigation | Excellent | Excellent |
| RTL support | Partial | Built-in |
| Font size scaling | Built-in | Built-in |

Monaco has a slight edge on accessibility due to VS Code's enterprise accessibility investment. Both are acceptable for production use.

### Mobile/Responsive Support

| Aspect | Monaco | CodeMirror 6 |
|---|---|---|
| Touch support | Limited (designed for desktop) | First-class (touch selection, gestures) |
| Mobile viewport handling | Poor | Good |
| Responsive layout | Fixed-size model | Flexible |
| Virtual keyboard handling | Problematic | Handled |

CodeMirror 6 was designed with mobile and touch in mind. Monaco was extracted from a desktop application and has known issues on mobile. If the SCBE IDE ever targets tablets or responsive layouts, CodeMirror 6 is the clear choice.

### Community and Maintenance

| Metric | Monaco | CodeMirror 6 |
|---|---|---|
| GitHub stars | ~42k | ~10k |
| npm weekly downloads | ~2M | ~1.5M (core) |
| Maintainers | Microsoft (VS Code team) | Marijn Haverbeke (+ community) |
| Release cadence | Monthly | As-needed (stable) |
| Bus factor concern | Low (Microsoft-backed) | Moderate (single primary maintainer) |
| Documentation quality | Good (VS Code docs crossover) | Excellent (comprehensive guide + API docs) |

Monaco benefits from Microsoft's resources. CodeMirror 6's primary risk is its single-maintainer model, though Marijn Haverbeke has maintained CodeMirror for over 15 years and the codebase is exceptionally well-designed for community contribution.

---

## 3. Backend Runtime: Rust vs Node

### Performance for File Watching, Indexing, Search

| Operation | Rust | Node.js |
|---|---|---|
| Directory traversal (100k files) | ~200-500ms (walkdir) | ~1-3s (fs.readdir recursive) |
| Full-text index build (1M lines) | ~2-5s (tantivy) | ~8-15s (flexsearch/lunr) |
| File watching setup | ~50ms (notify crate) | ~100-300ms (chokidar) |
| Regex search across project | ~100-300ms (ripgrep-core) | ~500ms-2s (node regex) |
| Git status (large repo) | ~50-200ms (gitoxide/libgit2) | ~200-500ms (isomorphic-git) |

Rust has a decisive performance advantage for I/O-bound and CPU-bound backend operations. The `ripgrep` crate alone (which is Rust) powers search in VS Code -- this speaks to the performance ceiling.

**For an IDE, backend performance directly impacts perceived responsiveness.** File search, go-to-definition, and project indexing are core operations that run thousands of times per session.

### Concurrency Model

| Aspect | Rust | Node.js |
|---|---|---|
| Model | Async (tokio) + true parallelism (threads) | Event loop + worker_threads |
| CPU-bound work | Parallel across cores (rayon) | Single-threaded (or worker_threads with overhead) |
| I/O-bound work | Efficient async (tokio, zero-cost futures) | Efficient async (libuv) |
| Memory safety | Guaranteed at compile time | GC-managed (occasional pauses) |
| Deadlock prevention | Compile-time borrow checking | Runtime (developer discipline) |

Rust's ability to saturate all CPU cores for parallel indexing/search while maintaining memory safety is a structural advantage. Node.js can use worker_threads but with serialization overhead for data transfer between threads.

### Integration with SCBE TypeScript/Python Codebase

| Approach | Rust Backend | Node.js Backend |
|---|---|---|
| TypeScript SCBE pipeline | Subprocess or WASM compilation | Direct import (same runtime) |
| Python SCBE pipeline | Subprocess (python -m) | Subprocess (python -m) |
| IPC overhead | Tauri IPC (JSON serialization) | In-process (zero overhead) |
| Shared types | JSON schema or protobuf | Direct TypeScript imports |
| SCBE governance calls | HTTP to FastAPI or Rust port | HTTP to FastAPI or direct TS call |

**This is Electron/Node's strongest argument.** SCBE's canonical implementation is TypeScript. In an Electron app, the governance pipeline (`src/harmonic/pipeline14.ts`) can be imported directly into the backend process with zero serialization overhead. In Tauri, the TypeScript pipeline would run in the WebView or as a separate Node subprocess, with IPC overhead for each governance call.

However, the SCBE API already exposes HTTP endpoints (`/api/authorize`, `/api/govern`, `/v1/fleet/task`). An IDE backend in any language can call these APIs. The overhead of localhost HTTP calls is ~1-5ms, which is negligible for governance decisions that happen per-action, not per-keystroke.

**Hybrid approach**: Tauri's Rust backend handles performance-critical operations (file I/O, search, indexing), while the SCBE TypeScript pipeline runs as a sidecar Node process or in the WebView. This is exactly how VS Code works -- the Electron main process delegates heavy work to extension hosts and language servers.

### Build Tooling Complexity

| Aspect | Rust | Node.js |
|---|---|---|
| Build system | Cargo (excellent, integrated) | npm/pnpm + bundler (Vite/esbuild) |
| Cross-compilation | cargo + cross (Docker-based) | pkg / electron-builder |
| CI build time | 5-15 min (clean Rust build) | 1-3 min |
| Dependency management | Cargo.lock (deterministic) | package-lock.json (deterministic) |
| Native dependencies | Cargo handles automatically | node-gyp (occasional pain) |

Rust build times are longer but Cargo is arguably a better build system than npm. Cross-compilation for Tauri is well-supported via GitHub Actions and the `tauri-action` plugin.

### Developer Availability and Hiring

| Aspect | Rust | Node.js / TypeScript |
|---|---|---|
| Stack Overflow survey popularity | #1 "most admired" (2024) | #1 most used (TypeScript) |
| Job market supply | Growing but smaller | Very large |
| Average compensation | Higher (scarcity premium) | Market rate |
| SCBE team familiarity | Learning required | Already proficient |
| Onboarding time | 2-4 months for productivity | Immediate |

Node.js/TypeScript has a dramatically larger hiring pool. Rust developers are harder to find and more expensive. However, Rust skills are increasingly valued and the language's popularity is growing rapidly.

---

## 4. Competitive Teardown

### 4.1 Cursor

**What it does well:**

- **AI-first architecture**: Every feature is designed around AI code generation and editing. The "Composer" multi-file edit mode and "Cmd+K" inline generation are best-in-class UX patterns.
- **Context-aware completions**: Uses a proprietary context engine that understands the full codebase, open files, recent edits, and terminal output. Completions feel aware of project-level patterns.
- **VS Code compatibility**: Forked from VS Code, so the entire extension ecosystem works. Users migrate without friction.
- **Diff-based editing**: AI edits are presented as diffs that can be accepted/rejected per-hunk. This gives the developer control without disrupting flow.
- **Fast iteration**: The team ships weekly. New models (Claude, GPT-4o, Gemini) are integrated within days of release.

**Gaps we can exploit:**

- **Closed source**: The core AI integration, context engine, and routing logic are proprietary. Users cannot audit what data leaves their machine, how prompts are constructed, or what telemetry is collected. *SCBE's open governance model and on-device 14-layer pipeline provide auditable, verifiable AI safety.*
- **No custom governance**: Cursor has no concept of a governance layer. Any AI model can generate any code, execute any command. There is no ALLOW/QUARANTINE/ESCALATE/DENY gate. *SCBE's L13 decision gate fills this gap entirely.*
- **No connector/task engine**: Cursor is a code editor. It cannot trigger Shopify deployments, Zapier workflows, n8n automations, or Slack notifications as part of a structured task pipeline. *SCBE's connector API (`/mobile/connectors`, `/mobile/goals/{id}/bind-connector`) provides this.*
- **Privacy concerns**: Cursor sends code context to cloud APIs for completions. Enterprise teams with sensitive IP (financial, medical, defense) cannot use it without risk. *SCBE's post-quantum sealed envelopes and on-device governance enable air-gapped operation.*
- **No extension governance**: Cursor inherits VS Code's extension model where extensions have broad Node.js access. A malicious extension can exfiltrate code. *SCBE's Safe Extension Gate (`agents/extension_gate.py`) with turnstile resolution addresses this.*
- **Subscription lock-in**: $20/month per developer. No self-hosted option. *SCBE IDE can be self-hosted with local AI models.*

### 4.2 Windsurf (Codeium)

**What it does well:**

- **Flow-based AI**: The "Cascade" feature maintains a persistent AI conversation that understands the developer's intent across multiple edits. It feels like pair programming rather than autocomplete.
- **Workspace understanding**: Indexes the entire workspace and uses embeddings for semantic code search. Understands project structure, dependencies, and patterns.
- **Free tier**: Generous free tier makes it accessible. Low barrier to trial.
- **Multi-file awareness**: Cascade can reason about changes across multiple files simultaneously, understanding import chains and type dependencies.

**Gaps we can exploit:**

- **Limited orchestration**: Windsurf operates at the code-editing level. It cannot orchestrate multi-step workflows that span code, deployment, testing, and external service integration. *SCBE's fleet manager and task dispatcher enable Research -> Task -> Approve -> Execute loops.*
- **No governance layer**: Like Cursor, there is no governance gate between AI suggestion and execution. No cost controls, no risk assessment, no approval workflows. *SCBE's harmonic wall (`H(d) = exp(d^2)`) makes adversarial operations exponentially expensive.*
- **Vendor lock-in**: Codeium's AI models are proprietary. If the service changes pricing or features, users have no recourse. *SCBE IDE supports any LLM provider and can run fully offline.*
- **No task engine**: Cannot bind AI operations to external connectors (Zapier, n8n, Shopify). Development is isolated from deployment and operations. *SCBE's connector onboarding system supports 10+ connector kinds.*
- **Weak extension model**: Inherits VS Code extension architecture without additional security hardening. *SCBE's turnstile-based extension gate provides domain-aware security.*
- **No secrets governance**: No post-quantum protection for API keys, tokens, or credentials stored in the IDE. *SCBE's ML-KEM-768 + ML-DSA-65 sealed envelopes protect secrets against quantum-era threats.*

### 4.3 VS Code

**What it does well:**

- **Ecosystem**: 50,000+ extensions. If a developer tool exists, there is a VS Code extension for it. This is VS Code's moat.
- **LSP standard**: VS Code popularized the Language Server Protocol, which is now the universal standard. Every language has an LSP server that works with VS Code.
- **Ubiquity**: ~74% developer market share (Stack Overflow 2024). It is the default choice.
- **Performance (for Electron)**: Microsoft has invested heavily in performance optimization. VS Code is the proof that Electron apps can be fast with sufficient engineering.
- **Remote development**: VS Code Remote (SSH, Containers, WSL, Tunnels) enables development on remote machines with local UI. This is a significant enterprise feature.
- **Debugging**: Integrated debugging with DAP (Debug Adapter Protocol) supports every major language.
- **Source control**: Built-in Git integration with diff view, staging, and merge conflict resolution.

**Gaps we can exploit:**

- **Extension security model is weak**: Extensions run in a shared Node.js host process with broad API access. A malicious extension can read any file, make network requests, and access secrets. The extension marketplace has had supply-chain attacks (e.g., malicious extensions mimicking popular ones). *SCBE's Safe Extension Gate with threat scanning, manifest scoring, and turnstile resolution directly addresses this.*
- **No built-in AI governance**: VS Code Copilot is an extension, not a governed subsystem. There is no cost control, no approval workflow, no risk assessment for AI-generated code. The `settings.json` approach to configuration provides no security guarantees. *SCBE's 14-layer pipeline provides mathematically-grounded governance.*
- **No task orchestration beyond tasks.json**: VS Code's task system is a thin wrapper around shell commands. It cannot orchestrate multi-step workflows with approval gates, external service connectors, or risk-based execution modes. *SCBE's goal/connector API with execution modes (manual, auto, connector) fills this gap.*
- **Bloated for focused use cases**: VS Code tries to be everything to everyone. The result is a 500+ MB installation with features most developers never use. *SCBE IDE can ship a focused, governance-first experience with a fraction of the footprint.*
- **No cryptographic secret protection**: VS Code stores settings and secrets in plaintext JSON or OS keychain with no cryptographic envelope. No post-quantum protection. *SCBE's AES-256-GCM + ML-KEM-768 sealed envelope provides defense-in-depth.*
- **Microsoft telemetry**: While open-source (MIT), VS Code's telemetry collection is extensive. Enterprise and government users have compliance concerns. *SCBE IDE can operate fully offline with zero telemetry.*

### 4.4 Replit

**What it does well:**

- **Instant dev environments**: Zero setup. Open a browser, start coding. No local installation, no dependency management, no configuration.
- **Multiplayer editing**: Real-time collaborative editing with cursor presence, chat, and shared terminals. Best-in-class for pair programming.
- **Integrated deployment**: One-click deployment from editor to production. No CI/CD pipeline configuration needed.
- **AI Agent**: Replit Agent can scaffold entire applications from natural language descriptions, including file structure, dependencies, and deployment.
- **Education**: Excellent for learning and prototyping. Low barrier to entry.

**Gaps we can exploit:**

- **Cloud-only**: All computation happens on Replit's servers. No offline mode, no local development, no air-gapped operation. Latency is noticeable (50-200ms per keystroke for completions). *SCBE IDE runs locally with optional cloud features.*
- **Limited for large codebases**: Replit struggles with repositories over ~50k files. The containerized environment has resource limits that large enterprise projects exceed. *SCBE IDE's Rust/Node backend can index and search million-line codebases locally.*
- **No security governance**: No concept of operation governance, risk assessment, or approval workflows. Any code can be deployed with a single click. *SCBE's ALLOW/QUARANTINE/ESCALATE/DENY gate prevents unreviewed deployment.*
- **Vendor dependency**: All code, data, and deployment live on Replit's infrastructure. If Replit changes pricing, features, or goes offline, users lose their development environment. *SCBE IDE is self-contained.*
- **Limited language/framework support**: While Replit supports many languages, its Nix-based environment has gaps for complex build systems (Rust cross-compilation, C++ with custom toolchains, embedded systems). *SCBE IDE delegates to the user's local toolchain.*
- **Privacy and IP concerns**: Code runs on shared infrastructure. Enterprise teams with sensitive IP cannot use it. *SCBE IDE keeps all code and secrets on the developer's machine, protected by post-quantum cryptography.*

### 4.5 Our Differentiator: The SCBE-Governed IDE

The SCBE IDE is not another code editor with AI bolted on. It is a **governance-first development environment** where every operation -- from AI code generation to deployment -- passes through a mathematically-grounded security pipeline.

#### SCBE 14-Layer Governance as the IDE's Permission/Execution Backbone

Every IDE operation maps to the 14-layer pipeline:

| IDE Operation | SCBE Layer | Behavior |
|---|---|---|
| Extension install | L1-L4 (context embedding) | Extension manifest is embedded in Poincare ball |
| AI code generation | L5-L7 (hyperbolic distance) | Distance from safe operation center is measured |
| File system write | L8 (multi-well realms) | Operation must fall within an allowed realm |
| Command execution | L9-L10 (spectral coherence) | Command pattern is checked for coherence with project norms |
| Connector dispatch | L12 (harmonic wall) | Cost scales as `H(d) = exp(d^2)` with deviation |
| Deploy/publish | L13 (decision gate) | ALLOW/QUARANTINE/ESCALATE/DENY |
| Telemetry | L14 (audio axis) | FFT-based anomaly detection on operation patterns |

#### Connector-Driven Task Engine

The SCBE IDE integrates the goal/connector API (`/mobile/goals`, `/mobile/connectors`) as a first-class task engine:

- **Research phase**: Developer or AI agent identifies a task (bug fix, feature, deployment).
- **Task creation**: Task is created as a goal with connector bindings (Shopify, Zapier, n8n, GitHub Actions, Slack, Notion, Linear, Discord).
- **Approval gate**: High-risk tasks pass through L13 governance. Human approval required for QUARANTINE/ESCALATE decisions.
- **Execution**: Approved tasks dispatch to bound connectors. Results flow back into the IDE.

Supported connectors (already implemented in `src/api/main.py`):

| Connector Kind | Use Case |
|---|---|
| `n8n` | Complex multi-step automations |
| `zapier` | Simple trigger-action workflows |
| `shopify` | Store deployment, product management |
| `slack` | Team notifications, approval requests |
| `notion` | Documentation sync |
| `airtable` | Data management |
| `github_actions` | CI/CD pipeline triggers |
| `linear` | Issue tracking integration |
| `discord` | Community notifications |
| `generic_webhook` | Any HTTP-based service |

#### Signed Extension Manifests with SCBE Governance Gates

The Safe Extension Gate (already implemented in `agents/extension_gate.py`) provides:

1. **Threat scan**: Prompt injection signatures, malware-like commands, external link pressure.
2. **Manifest scoring**: Permission risk (weighted by capability) + provenance risk (trusted source domain, SHA-256 pin, manifest completeness).
3. **Combined suspicion**: `suspicion = 0.55 * scan + 0.25 * permission + 0.20 * provenance`.
4. **Turnstile resolution**: Domain-aware outcomes (ALLOW / HOLD / ISOLATE / HONEYPOT).
5. **Permission partition**: Low suspicion = full enablement; medium = reduced allowlist; high = zero permissions.

This is a structural advantage over VS Code, Cursor, and Windsurf, none of which have extension governance.

#### Post-Quantum Crypto for Secrets Vault

The SCBE IDE's secrets vault uses:

- **ML-KEM-768** (NIST FIPS 203): Key encapsulation for secret exchange
- **ML-DSA-65** (NIST FIPS 204): Digital signatures for manifest integrity
- **AES-256-GCM**: Symmetric encryption for sealed envelopes
- **HKDF-SHA256**: Key derivation for per-secret keys
- **Bloom filter replay guard**: Prevents nonce reuse

No other IDE provides post-quantum protection for developer secrets.

---

## 5. Weighted Decision Matrix

### Criteria Weights

| # | Criterion | Weight | Rationale |
|---|---|---|---|
| 1 | Dev velocity (time to ship v0) | 5 | Must ship a usable IDE quickly to validate the concept |
| 2 | Performance (memory, startup, responsiveness) | 4 | IDE must feel fast; competes with native apps |
| 3 | Security (sandboxing, isolation, secret protection) | 5 | Core differentiator; SCBE governance must be enforceable |
| 4 | Extensibility (plugin/extension model) | 4 | Must support third-party extensions with governance |
| 5 | SCBE integration ease (TS/Python interop) | 5 | The IDE exists to surface SCBE governance |
| 6 | Cross-platform (Win/Mac/Linux) | 3 | Windows 11 primary; others secondary |
| 7 | Community and ecosystem | 3 | Matters for hiring, troubleshooting, libraries |
| 8 | Long-term maintainability | 4 | Must be sustainable beyond v0 |

**Total possible weight points**: 33

### Option Combinations

We evaluate four realistic combinations:

- **Option A**: Tauri v2 + CodeMirror 6 + Rust backend
- **Option B**: Tauri v2 + Monaco + Rust backend
- **Option C**: Electron + Monaco + Node.js backend
- **Option D**: Electron + CodeMirror 6 + Node.js backend

### Scoring Matrix (1-10 per criterion)

| # | Criterion | Wt | A: Tauri+CM6+Rust | B: Tauri+Monaco+Rust | C: Electron+Monaco+Node | D: Electron+CM6+Node |
|---|---|---|---|---|---|---|
| 1 | Dev velocity | 5 | 5 | 5 | 9 | 8 |
| 2 | Performance | 4 | 10 | 8 | 5 | 6 |
| 3 | Security | 5 | 10 | 10 | 5 | 5 |
| 4 | Extensibility | 4 | 7 | 7 | 9 | 8 |
| 5 | SCBE integration | 5 | 6 | 6 | 9 | 9 |
| 6 | Cross-platform | 3 | 7 | 7 | 9 | 9 |
| 7 | Community | 3 | 5 | 6 | 10 | 8 |
| 8 | Maintainability | 4 | 8 | 7 | 7 | 7 |

### Score Justifications

**Option A (Tauri + CM6 + Rust):**

- Dev velocity (5): Rust learning curve slows initial development. CM6 requires building features that Monaco provides out-of-box. Two unfamiliar technologies compound the slowdown.
- Performance (10): Best possible combination. Rust backend + CM6's lightweight architecture = minimal memory, fastest startup, smoothest large-file handling.
- Security (10): Tauri's deny-by-default capabilities + Rust memory safety + CM6's minimal attack surface = strongest security posture. Maps perfectly to SCBE governance model.
- Extensibility (7): Tauri plugin API is capable but less proven. CM6's facet system is excellent for composition. No marketplace precedent.
- SCBE integration (6): SCBE is TypeScript/Python. Rust backend requires IPC to reach SCBE pipeline. Adds serialization overhead and architectural complexity.
- Cross-platform (7): Excellent on Windows 11 (WebView2) and macOS (WebKit). Linux WebKitGTK can have quirks.
- Community (5): Smallest combined community of the four options.
- Maintainability (8): Rust's type system and memory safety prevent entire classes of bugs. CM6's clean architecture ages well.

**Option B (Tauri + Monaco + Rust):**

- Dev velocity (5): Same Rust overhead as Option A. Monaco provides more features out-of-box than CM6, but its larger bundle in a Tauri WebView creates optimization work.
- Performance (8): Rust backend is fast, but Monaco's 5+ MB bundle and higher memory usage partially offset Tauri's lightweight shell.
- Security (10): Same Tauri + Rust security benefits as Option A.
- Extensibility (7): Monaco's provider API is well-known. Same Tauri plugin limitations.
- SCBE integration (6): Same IPC overhead as Option A.
- Cross-platform (7): Same as Option A.
- Community (6): Monaco's larger community slightly helps.
- Maintainability (7): Monaco's monolithic architecture is harder to maintain long-term than CM6's modular design.

**Option C (Electron + Monaco + Node):**

- Dev velocity (9): Fastest path to v0. TypeScript everywhere. Monaco provides VS Code-grade editing out-of-box. Electron is familiar territory. SCBE pipeline imports directly.
- Performance (5): Highest memory usage. Slowest startup. Electron + Monaco is the VS Code stack -- proven but heavy.
- Security (5): Electron's security model requires careful configuration. Node.js backend has broader attack surface. Must build custom sandboxing for extensions.
- Extensibility (9): VS Code extension model is the gold standard. Can potentially load VS Code extensions with compatibility layer.
- SCBE integration (9): Direct TypeScript imports. Same runtime. Zero IPC overhead for governance calls.
- Cross-platform (9): Proven on all platforms.
- Community (10): Largest combined community. Most documentation, examples, and prior art.
- Maintainability (7): Electron apps accumulate technical debt around Chromium version management and security patches.

**Option D (Electron + CM6 + Node):**

- Dev velocity (8): Node.js familiarity + CM6 requires building some features that Monaco provides. Slightly slower than Option C.
- Performance (6): Electron's overhead remains, but CM6's lighter footprint helps compared to Monaco.
- Security (5): Same Electron security limitations as Option C.
- Extensibility (8): CM6's facet system + Node.js = flexible. Less VS Code ecosystem compatibility.
- SCBE integration (9): Same direct TypeScript integration as Option C.
- Cross-platform (9): Same as Option C.
- Community (8): Electron's large community + CM6's smaller but high-quality community.
- Maintainability (7): Same Electron maintenance concerns. CM6's modular architecture helps.

### Weighted Totals

| # | Criterion | Wt | A: Tauri+CM6+Rust | B: Tauri+Monaco+Rust | C: Electron+Monaco+Node | D: Electron+CM6+Node |
|---|---|---|---|---|---|---|
| 1 | Dev velocity | 5 | 25 | 25 | 45 | 40 |
| 2 | Performance | 4 | 40 | 32 | 20 | 24 |
| 3 | Security | 5 | 50 | 50 | 25 | 25 |
| 4 | Extensibility | 4 | 28 | 28 | 36 | 32 |
| 5 | SCBE integration | 5 | 30 | 30 | 45 | 45 |
| 6 | Cross-platform | 3 | 21 | 21 | 27 | 27 |
| 7 | Community | 3 | 15 | 18 | 30 | 24 |
| 8 | Maintainability | 4 | 32 | 28 | 28 | 28 |
| | **TOTAL** | **33** | **241** | **232** | **256** | **245** |
| | **Normalized (%)** | | **73.0%** | **70.3%** | **77.6%** | **74.2%** |

### Summary Ranking

| Rank | Option | Score | Normalized |
|---|---|---|---|
| 1 | **C: Electron + Monaco + Node** | **256** | **77.6%** |
| 2 | D: Electron + CM6 + Node | 245 | 74.2% |
| 3 | A: Tauri + CM6 + Rust | 241 | 73.0% |
| 4 | B: Tauri + Monaco + Rust | 232 | 70.3% |

---

## 6. Recommendation

### Primary Recommendation: Option C (Electron + Monaco + Node) for v0, with Tauri Migration Path for v2

**Ship v0 with Electron + Monaco + Node.js.** Migrate to Tauri + CodeMirror 6 for v2 once the product-market fit is validated.

### Rationale

**Why Electron + Monaco + Node for v0:**

1. **Dev velocity is the highest priority.** The SCBE IDE must ship quickly to validate the governance-first IDE hypothesis. Electron + Monaco + Node.js is the fastest path because the SCBE team already works in TypeScript, the SCBE pipeline imports directly with zero IPC overhead, and Monaco provides VS Code-grade editing without building features from scratch.

2. **SCBE integration is seamless.** The 14-layer pipeline (`src/harmonic/pipeline14.ts`), governance API (`src/api/govern.ts`), connector system (`src/api/main.py`), and extension gate (`agents/extension_gate.py`) all run natively in a Node.js environment. No serialization layer, no subprocess management, no FFI bridges.

3. **The ecosystem accelerates development.** Monaco's built-in diff view, IntelliSense, and multi-cursor editing are table-stakes features that would take months to build on CodeMirror 6. The VS Code extension compatibility potential (via the VS Code Extension API subset) provides a massive head start on language support.

4. **The security gap is addressable.** Electron's weaker security model is a real concern, but SCBE's Safe Extension Gate, sealed envelopes, and governance pipeline can be layered on top. Electron's `contextIsolation`, `sandbox: true`, and custom `webContents` permission handlers provide the foundation. The SCBE governance layer adds what Electron lacks: operation-level ALLOW/DENY gates.

**Why plan for Tauri + CM6 migration in v2:**

1. **Security ceiling.** Tauri's Rust backend isolation and deny-by-default capability system are architecturally superior for a security-focused product. Once the IDE is validated, the security story should be maximized.

2. **Performance ceiling.** As the IDE grows (more extensions, larger workspaces, more concurrent operations), Tauri + CM6's lighter footprint will matter. An IDE that uses 200 MB instead of 600 MB wins on developer machines running Docker, language servers, and databases simultaneously.

3. **Differentiation.** Every competitor (Cursor, Windsurf, VS Code) is built on Electron. A Tauri-based IDE is a meaningful technical differentiator that signals engineering seriousness to enterprise buyers.

4. **Bundle size for distribution.** A 5 MB IDE installer vs. a 100 MB installer matters for auto-updates, enterprise deployment, and first-impression perception.

### Migration Strategy

The architecture should be designed from day one to make the Electron-to-Tauri migration feasible:

1. **Abstract the shell layer.** Define an `IdeShell` interface that abstracts window management, native menus, system tray, file dialogs, and notifications. Implement `ElectronShell` for v0 and `TauriShell` for v2.

2. **Abstract the editor layer.** Define an `IEditor` interface that abstracts document management, decorations, diagnostics, and completions. Implement `MonacoEditor` for v0 and `CodeMirrorEditor` for v2.

3. **Isolate the SCBE governance layer.** The governance pipeline should run as an independent service (HTTP on localhost or WebSocket) rather than being tightly coupled to the Electron main process. This makes it runtime-agnostic.

4. **Use Web APIs where possible.** Prefer `fetch`, `WebSocket`, `IndexedDB`, and `Web Crypto` over Node-specific APIs in the renderer. This code will work unchanged in Tauri's WebView.

5. **Design the extension API as an IPC protocol.** Extensions communicate via a defined message protocol (JSON-RPC or similar), not via direct API access. This protocol works identically over Electron IPC or Tauri commands.

### Architecture Sketch (v0)

```
+----------------------------------------------------------------------+
|                        SCBE IDE (Electron)                           |
|                                                                       |
|  +---------------------------+   +--------------------------------+  |
|  |    Renderer (Chromium)    |   |     Main Process (Node.js)     |  |
|  |                           |   |                                |  |
|  |  +---------------------+ |   |  +---------------------------+ |  |
|  |  |   Monaco Editor     | |   |  | SCBE Governance Engine    | |  |
|  |  |   (code editing)    | |   |  | (pipeline14.ts, govern.ts)| |  |
|  |  +---------------------+ |   |  +---------------------------+ |  |
|  |                           |   |                                |  |
|  |  +---------------------+ |   |  +---------------------------+ |  |
|  |  |   Task Panel        | |   |  | Connector Engine          | |  |
|  |  |   (goals, connectors)| |   |  | (n8n, Zapier, Shopify...) | |  |
|  |  +---------------------+ |   |  +---------------------------+ |  |
|  |                           |   |                                |  |
|  |  +---------------------+ |   |  +---------------------------+ |  |
|  |  |   Extension Host    | |   |  | File System / Indexer     | |  |
|  |  |   (sandboxed)       | |   |  | (chokidar, flexsearch)   | |  |
|  |  +---------------------+ |   |  +---------------------------+ |  |
|  |                           |   |                                |  |
|  |  +---------------------+ |   |  +---------------------------+ |  |
|  |  |   Terminal           | |   |  | Secrets Vault             | |  |
|  |  |   (xterm.js)        | |   |  | (ML-KEM-768, AES-256-GCM) | |  |
|  |  +---------------------+ |   |  +---------------------------+ |  |
|  +---------------------------+   +--------------------------------+  |
|                                                                       |
|  +------------------------------------------------------------------+|
|  |                  Extension Gate (L13 Turnstile)                   ||
|  |  Threat Scan -> Manifest Score -> Suspicion -> ALLOW/ISOLATE     ||
|  +------------------------------------------------------------------+|
|                                                                       |
|  +------------------------------------------------------------------+|
|  |                  SCBE 14-Layer Pipeline                           ||
|  |  L1-4: Context Embedding | L5-7: Hyperbolic Distance            ||
|  |  L8: Realms | L9-10: Spectral | L11: Temporal                   ||
|  |  L12: Harmonic Wall | L13: Decision Gate | L14: Telemetry       ||
|  +------------------------------------------------------------------+|
+----------------------------------------------------------------------+
         |                    |                    |
         v                    v                    v
  +------------+      +-------------+      +-------------+
  | LSP Servers |      | Python SCBE |      | Connectors  |
  | (TS, Py,   |      | (FastAPI    |      | (n8n, Zapier|
  |  Rust, Go) |      |  sidecar)   |      |  Shopify)   |
  +------------+      +-------------+      +-------------+
```

### Key Milestones

| Phase | Duration | Deliverable |
|---|---|---|
| v0.1 (Prototype) | 6-8 weeks | Electron + Monaco shell with SCBE governance gate on file operations |
| v0.5 (Alpha) | 12-16 weeks | Full editor with LSP, terminal, connector panel, extension loading |
| v1.0 (Beta) | 24-30 weeks | Production-ready with secrets vault, signed extensions, 5+ connectors |
| v2.0 (Migration) | 36-48 weeks | Tauri + CM6 rewrite with full feature parity |

### Final Verdict

**Electron + Monaco + Node.js** wins on weighted score (256 vs 241) primarily because of dev velocity (+20 points) and SCBE integration ease (+15 points) -- the two criteria with the highest weight (5 each). The security gap (-25 points vs Tauri) is real but addressable through SCBE's own governance layer, which is the entire point of building this IDE.

Build the product first. Harden the foundation second. The SCBE governance pipeline is the differentiator, not the shell technology -- and that pipeline ships fastest on the stack the team already knows.

---

*This document should be revisited when Tauri v2 ecosystem matures further (target: Q4 2026 reassessment). Track Tauri IDE-class reference implementations (especially any LSP-integrated editors) as leading indicators for migration readiness.*
