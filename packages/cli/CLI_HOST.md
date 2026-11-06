# GeoSeal: one command session for local CLIs

Run `geoseal shell` for the terminal, or `geoseal shell --agent-json` for one
JSON request per line. `geoseal shell --describe` returns the request schema.
The initial ready message identifies the session. Subsequent replies keep the
request ID, sequence, working directory and geometric task context.

```json
{"id":"catalog","op":"tools"}
{"id":"route","op":"geo","task":"inspect and compile the project"}
{"id":"git","op":"tool","name":"git","args":["status","--short"],"timeout_ms":30000}
{"id":"scbe","op":"tool","name":"scbe","args":["tools","--json"]}
{"id":"native","op":"run","command":"Get-ChildItem -File | Select-Object Name"}
```

In the human terminal, use `tools` and `tool git ["status","--short"]`.
Use the `run` operation for native PowerShell pipelines. Tool arguments are
literal strings: empty strings, spaces, quotes, Unicode, `$()` and `|` retain
their argument boundaries. The selected CLI still interprets its own flags and
code arguments. All tools go through the existing GeoSeal command gate and
execution history. Geometric task context does not grant permission.

## Available tools and extension

The default catalog contains Node, SCBE, the agent bus, Git, GitHub CLI, Python,
Hermes and Blender. Missing executables are reported as unavailable. Discovery
does not start models, authenticate providers, install tools or launch jobs.

Additional tools belong in `geoseal-tools.json` inside the configured SCBE home
(normally `~/.scbe`; respects `SCBE_HOME`). For example:

```json
{
  "schema_version": "geoseal.cli_tools.v1",
  "tools": [
    {
      "name": "my-compiler",
      "executable": "C:/Program Files/nodejs/node.exe",
      "args": ["C:/my-project/bin/compiler.cjs"],
      "description": "Compile the local project language."
    }
  ]
}
```

Replace the example script with an existing CLI entry point. The owner can
override a default name in this file. The catalog is loaded once per session;
agent requests cannot register arbitrary executable paths. Windows registrations
use native `.exe` files; use Node/Python plus a script path for `.js`/`.py` CLIs,
rather than `.cmd` wrappers. No package installation or API keys are required
for the host itself. A hosted CLI may need its own dependencies or credentials.

## Execution contract

### Local diagnostics

Run `geoseal shell --diagnose` for a JSON diagnostic report, type `diagnose`
inside the shell, or send `{"id":"check","op":"diagnose"}` through agent-json.
The result schema is `geoseal.runtime_diagnostics.v1`. A successful protocol
reply means the inspection completed; its `result.status` can still be
`degraded` when a runtime is unavailable.

The report includes PowerShell candidates, the selected absolute path, observed
versions, startup/permission/timeout failures and the CLI catalog. Default Node,
Python, Git and GitHub CLI registrations receive bounded version-only probes.
Custom registrations, script wrappers, app execution aliases and model tools
are not automatically executed. Every check runs hidden with an output limit.
No authentication or network request is performed. Account authentication is
explicitly `not_checked`; authentication errors and service-scope errors are
classified separately when an actual command reports them. Raw probe output is
not included in the diagnostic report.

Run the check under the worker's actual account and sandbox when diagnosing
that worker. A success in an unrestricted terminal does not prove the worker
has equivalent access. `SCBE_POWERSHELL` still selects a preferred executable;
failed candidates are recorded before fallback. If all PowerShell probes fail,
Windows commands report `shell_unavailable` rather than changing their syntax
by silently running through cmd.exe. Diagnostics change no permissions.

- Tool requests share FIFO ordering, duplicate-ID rejection, cwd and geo context
  with shell requests. A failed tool does not close the session.
- At most 256 arguments totaling 65,536 characters; NUL is rejected. A timeout
  is 1–300,000 ms, default 30,000. Standard input is closed: this is a
  noninteractive command interface. Interactive CLI sessions need a separate
  persistent-process adapter.
- Exit codes, bounded stdout/stderr, truncation and timeout errors come from the
  process. Output is limited to 1 MiB combined in a reply. Execution history
  follows the existing SCBE policy; do not pass credentials as command arguments.
- Processes inherit the host account/environment. This host is **not an OS
  sandbox**. Windows child-tree timeout cleanup is covered by a test that proves
  the child started; descendant cleanup on other operating systems is not
  verified here. Use containers/OS isolation for untrusted programs.
- Native shell variables/functions and tool processes do not persist across
  requests. No distributed/parallel dispatch, paid job launch or automatic
  model-provider startup occurs merely by opening this session.
- CLI-host capability requires the matching agent-bus build. An older bus
  fails with an explicit upgrade/build error. This local change has not been
  released to npm.

## Training and internal workspaces

This supplies the real execution half of a future Clay workspace. The model
can learn typed actions and predict their effects; a receipt establishes what
actually ran. Existing Clay weights and the running training job are unchanged.
Training traces must pass the existing custom tokenizer/multiview pipeline and
separate proposals, observed results and evaluator judgments.

NeuralOS predicts GUI frames and interaction state using an RNN and diffusion
renderer ([paper](https://arxiv.org/abs/2507.08800)). This is relevant to learned
workspace simulation; it does not establish arbitrary binary execution inside
weights. Proposed next steps:

1. Represent a workspace with stable object IDs, content hashes, files and tool
   state; record actions and observed transitions.
2. Add a scene graph and an existing 3D tool adapter. Validate actual meshes,
   transforms and exported assets independently of rendered appearance.
3. Render headless, perspective, orthographic, fisheye and multiple camera views
   from the same scene state. Changing a view must preserve object identity.
4. Train state prediction on verified transitions with held-out tasks, then
   compare prediction with execution. Measure task success, invalid actions,
   geometry errors, latency and memory against the same model without the host.

A different camera view or more internal screens does not itself increase model
parameters or prove stronger reasoning. Those are hypotheses for controlled
experiments after the executable interfaces are stable.
