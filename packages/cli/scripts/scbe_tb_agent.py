"""
SCBE Terminal-Bench adapter.

Wraps `scbe shell --agent-json` as a Terminal-Bench BaseAgent.
The SCBE governed shell handles LLM routing + GeoSeal governance;
this adapter maps its NDJSON protocol onto the TB TmuxSession API.

Usage:
    pip install terminal-bench
    tb run \
        --agent-import-path scbe_tb_agent:ScbeAgent \
        --model ollama/llama3.2 \
        --task-id hello-world

    # Specify SCBE CLI path explicitly:
    SCBE_CLI=/path/to/scbe.js tb run --agent-import-path scbe_tb_agent:ScbeAgent ...

    # Run on terminal-bench-core leaderboard set:
    tb run \
        --agent-import-path scbe_tb_agent:ScbeAgent \
        --model ollama/llama3.2 \
        --dataset-name terminal-bench-core \
        --dataset-version 0.1.1

Environment variables consumed by this adapter:
    SCBE_CLI          Path to scbe.js CLI (auto-detected if absent)
    SCBE_MODEL        Override model in provider/model format (e.g. ollama/llama3.2)
    SCBE_PROVIDER     Override provider only
    SCBE_URL          Override Ollama/OpenAI base URL
    SCBE_API_KEY      Override API key
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__" and any(arg in {"-h", "--help"} for arg in sys.argv[1:]):
    print((__doc__ or "").strip())
    sys.exit(0)

try:
    from terminal_bench.agents.base_agent import AgentResult, BaseAgent
    from terminal_bench.agents.failure_mode import FailureMode
    from terminal_bench.terminal.tmux_session import TmuxSession
except ImportError as _e:
    raise ImportError(
        "terminal-bench package not installed. Run: pip install terminal-bench"
    ) from _e


class ScbeAgent(BaseAgent):
    """SCBE governed shell as a Terminal-Bench agent.

    The SCBE shell receives the task instruction and current terminal
    state, routes through the configured LLM, runs a GeoSeal governance
    check on the proposed command, then returns the approved keystrokes.
    This loop repeats until the LLM signals completion or MAX_EPISODES
    is reached.
    """

    MAX_EPISODES = 30
    DEFAULT_TIMEOUT_SEC = 30.0

    def __init__(self, model_name: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self._model_name = model_name
        self._scbe_cli = self._find_scbe_cli()

    @staticmethod
    def name() -> str:
        return "scbe"

    # ── CLI resolution ────────────────────────────────────────────────────────

    def _find_scbe_cli(self) -> str:
        override = os.environ.get("SCBE_CLI")
        if override:
            return override

        # Try PATH (npm global install: scbe)
        scbe_bin = shutil.which("scbe")
        if scbe_bin:
            return scbe_bin

        # Try adjacent bin/ relative to this script (repo layout)
        candidates = [
            Path(__file__).parent.parent / "bin" / "scbe.js",
            Path(__file__).parent.parent.parent / "packages" / "cli" / "bin" / "scbe.js",
        ]
        for c in candidates:
            if c.exists():
                return str(c.resolve())

        raise RuntimeError(
            "Cannot find scbe CLI. Set SCBE_CLI env var pointing to scbe.js, "
            "or install the npm package: npm install -g scbe-aethermoore"
        )

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        if self._model_name:
            env["SCBE_MODEL"] = self._model_name
        return env

    def _build_cmd(self) -> list[str]:
        cli = self._scbe_cli
        extra_args: list[str] = []
        if os.environ.get("SCBE_AGENT_JSON_SCAFFOLD") == "1":
            extra_args.append("--scaffold")
        if cli.endswith(".js"):
            node = shutil.which("node") or "node"
            return [node, cli, "shell", "--agent-json", *extra_args]
        return [cli, "shell", "--agent-json", *extra_args]

    # ── NDJSON helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _send(proc: subprocess.Popen, msg: dict) -> None:
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    @staticmethod
    def _recv(proc: subprocess.Popen) -> dict:
        line = proc.stdout.readline()
        if not line:
            return {}
        try:
            return json.loads(line.strip())
        except json.JSONDecodeError:
            return {"error": f"bad JSON: {line[:200]}"}

    # ── Core loop ─────────────────────────────────────────────────────────────

    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
    ) -> AgentResult:
        stderr_dest = subprocess.DEVNULL
        if logging_dir:
            logging_dir.mkdir(parents=True, exist_ok=True)
            stderr_dest = open(logging_dir / "scbe_stderr.log", "w")

        proc = subprocess.Popen(
            self._build_cmd(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_dest,
            text=True,
            env=self._build_env(),
        )

        try:
            ready = self._recv(proc)
            if not ready.get("ready"):
                proc.kill()
                return AgentResult(failure_mode=FailureMode.AGENT_INSTALLATION_FAILED)

            # Initial task message
            self._send(proc, {
                "instruction": instruction,
                "terminal_state": session.capture_pane(),
            })

            for episode in range(self.MAX_EPISODES):
                msg = self._recv(proc)

                if not msg or msg.get("error"):
                    break

                if logging_dir:
                    ep_dir = logging_dir / f"episode-{episode}"
                    ep_dir.mkdir(parents=True, exist_ok=True)
                    (ep_dir / "scbe_response.json").write_text(
                        json.dumps(msg, indent=2)
                    )

                commands = msg.get("commands", [])
                done = msg.get("done", False)
                blocked = msg.get("blocked", False)

                if blocked:
                    # governance block — report to log but continue (harness may retry)
                    if logging_dir:
                        (ep_dir / "governance_block.txt").write_text(
                            msg.get("rationale", "blocked")
                        )
                    break

                for cmd_spec in commands:
                    keystrokes = cmd_spec.get("keystrokes", "")
                    is_blocking = cmd_spec.get("is_blocking", True)
                    timeout_sec = float(cmd_spec.get("timeout_sec", self.DEFAULT_TIMEOUT_SEC))
                    if not keystrokes:
                        continue
                    try:
                        session.send_keys(
                            [keystrokes, "Enter"],
                            block=is_blocking,
                            max_timeout_sec=timeout_sec,
                        )
                    except TimeoutError:
                        pass

                if done:
                    break

                if episode < self.MAX_EPISODES - 1:
                    self._send(proc, {"terminal_state": session.capture_pane()})

        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

        return AgentResult(failure_mode=FailureMode.NONE)
