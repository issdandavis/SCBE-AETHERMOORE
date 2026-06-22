# AetherDesk Terminal Agent Feature Cross-Reference

Date: 2026-06-19

## Things the user wanted added

- Shell-in-shell: launch another agent terminal from inside our shell and control it programmatically.
- Ollama launch integrations: Claude, Codex App, Hermes, OpenClaw, OpenCode, Codex, Copilot, Droid, Pi, plus raw local models.
- A relay station for agents: a structured context packet so an agent is not "free floating" when launched.
- Terminal plus apps in one local desktop surface.
- Agents that can run tasks, inspect output, and improve the system that launched them.
- A VR/game-like control surface later, where the environment is the thing the AI and user can both see and operate.
- Receipts, tests, and safety boundaries around all of this.

## Things I want added

- A bounded Agent Shell lane inside AetherDesk before any raw terminal access.
- A real PTY/ConPTY terminal later, with xterm.js on the frontend and node-pty or equivalent on the backend.
- Process lifecycle management: start, stream output, timeout, kill tree, prevent orphaned agent processes.
- A task packet schema with the five Ws: who, what, where, when, why, plus allowed paths and verification command.
- Receipt unification between AetherDesk receipts and Agent Shell receipts.
- A diff/apply gate: agents can propose patches, but AetherDesk shows and applies them explicitly.
- Provider/model inventory that shows local Ollama models and launchable agent surfaces, not just provider reachability.
- A small benchmark button for the agent shell itself.

## Research-backed things worth adding

- xterm.js browser terminal rendering. It is the standard browser terminal component and is used by terminal-heavy apps such as VS Code-style environments.
- node-pty or ConPTY-backed process control on Windows. node-pty supports Windows through ConPTY on modern Windows builds.
- WebSocket streaming between backend PTY and frontend terminal. This is the usual shape for browser terminals.
- Shell integration metadata similar to VS Code: command boundaries, exit codes, current working directory, and command history.
- AI terminal split-pane pattern: terminal buffer, chat/agent pane, session/task list, provider controls, and command palette.
- Local-first agent sandboxing: keep local execution separate from cloud provider calls, with explicit escalation.

## Cross-reference groups

### Group 1: Supervised Agent Launch

Overlap:

- User wanted shell-in-shell, Ollama launch agents, relay station context, and rebuild-itself loops.
- I wanted a bounded Agent Shell lane and task packet schema before raw terminal access.
- Research supports process supervision and local-first agent sandboxing before exposing more powerful terminal controls.

Build first:

- Add AetherDesk allowlisted shell profiles for `agent_shell_probe` and a bounded `agent_shell_codex_brief`.
- Keep them non-arbitrary and receipt-producing.

### Group 2: Real Interactive Terminal

Overlap:

- User wanted a terminal an AI can operate.
- I wanted PTY/ConPTY and lifecycle management.
- Research points to xterm.js plus node-pty/WebSocket as the common architecture.

Build after Group 1:

- Add a PTY service behind explicit risk gates.
- Stream terminal output into the UI.
- Support kill/timeout/session cleanup.

### Group 3: Agent Workbench / Patch Gate

Overlap:

- User wanted agents to build real products.
- I wanted diff/apply boundaries and verification commands.
- Research and the existing SCBE spec both point to task lists, receipts, and visible patch approval.

Build after Group 1:

- Agent task form.
- Proposed diff pane.
- Safe apply button.
- Test result receipt.

### Group 4: Shared Visual/VR Layer

Overlap:

- User wanted the AI and human to share a visible world.
- I want the terminal/workbench semantics stable before a 3D layer.
- Research on terminal/agent workbenches does not replace this, but it gives the control plane.

Build later:

- Treat the 3D/VR layer as a view over tasks, agents, files, drones, and receipts.
- Do not make the VR layer the first source of truth.

## First build chosen

Group 1 is first because it turns AetherDesk from "apps plus bounded commands" into "apps plus bounded agent handoff" without opening arbitrary shell execution.
