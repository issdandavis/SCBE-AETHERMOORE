#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Multi-Agent Coding Platform Launcher

Starts a 6-head HYDRA swarm with MCP servers for AI-to-AI coordination.
Multiple Claude/Gemini/OpenAI instances can connect and collaborate on code.

Sacred Tongue Specialists:
  - KO (Kor'aelin): Scout - Task discovery & planning
  - AV (Avali): Vision - Code analysis & pattern recognition
  - RU (Runethic): Reader - Documentation & knowledge retrieval
  - CA (Cassisivadan): Clicker - Interactive execution & testing
  - UM (Umbroth): Typer - Code generation & writing
  - DR (Draumric): Judge - Quality review & governance

Architecture:
  Spine (Orchestrator) ← → BFT Consensus ← → Ledger (Records)
    ↓↓↓↓↓↓
  6 Heads (Specialists) ← → Juggling Scheduler (Task Router)
    ↓
  MCP Servers (for external AI)
"""

import asyncio
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s — %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Platform constants
PLATFORM_VERSION = "1.0.0"
SCBE_ROOT = Path(__file__).parent
HYDRA_ROOT = SCBE_ROOT / "hydra"
MCP_ROOT = SCBE_ROOT / "mcp"
AGENTS_ROOT = SCBE_ROOT / "agents"

# Sacred Tongues
SACRED_TONGUES = {
    "KO": {"name": "Kor'aelin", "role": "Scout", "freq": "440-523 Hz"},
    "AV": {"name": "Avali", "role": "Vision", "freq": "330-392 Hz"},
    "RU": {"name": "Runethic", "role": "Reader", "freq": "262-311 Hz"},
    "CA": {"name": "Cassisivadan", "role": "Clicker", "freq": "494-587 Hz"},
    "UM": {"name": "Umbroth", "role": "Typer", "freq": "370-440 Hz"},
    "DR": {"name": "Draumric", "role": "Judge", "freq": "220-262 Hz"},
}


class PlatformLauncher:
    """Launches and manages the SCBE multi-agent coding platform."""

    def __init__(self):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.mcp_ports: Dict[str, int] = {}
        self.ledger_path = SCBE_ROOT / "artifacts" / "swarm_ledger.jsonl"
        self.config_path = SCBE_ROOT / ".scbe_platform_config.json"

    def setup_directories(self):
        """Create required directories."""
        (SCBE_ROOT / "artifacts").mkdir(exist_ok=True)
        self.ledger_path.parent.mkdir(exist_ok=True)
        logger.info(f"✓ Platform directories ready")

    def start_spine(self) -> bool:
        """Start the HYDRA Spine (central orchestrator)."""
        logger.info("▲ Starting HYDRA Spine (Central Orchestrator)...")
        try:
            cmd = [
                sys.executable,
                str(HYDRA_ROOT / "spine.py"),
                "--mode",
                "production",
                "--ledger",
                str(self.ledger_path),
            ]
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(SCBE_ROOT),
            )
            self.processes["spine"] = proc
            logger.info("▲ Spine started (PID: %d)", proc.pid)
            return True
        except Exception as e:
            logger.error("✗ Failed to start Spine: %s", e)
            return False

    def start_heads(self) -> bool:
        """Start the 6 Sacred Tongue specialist heads."""
        logger.info("≈ Starting 6 Specialist Heads...")
        base_port = 9000

        for tongue_id, (tongue_name, tongue_info) in enumerate(SACRED_TONGUES.items()):
            port = base_port + tongue_id
            self.mcp_ports[tongue_id] = port

            logger.info(f"  → {tongue_name} ({tongue_info['role']}) on ::{port}")
            try:
                cmd = [
                    sys.executable,
                    str(HYDRA_ROOT / "head.py"),
                    "--tongue",
                    tongue_id,
                    "--role",
                    tongue_info["role"].lower(),
                    "--port",
                    str(port),
                    "--ledger",
                    str(self.ledger_path),
                ]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(SCBE_ROOT),
                )
                self.processes[f"head_{tongue_id}"] = proc
                logger.info(f"  ✓ {tongue_name} head ready")
            except Exception as e:
                logger.error(f"  ✗ Failed to start {tongue_name} head: {e}")
                return False

        return True

    def start_ledger(self) -> bool:
        """Initialize and start the distributed ledger."""
        logger.info("◇ Starting Governance Ledger...")
        try:
            # Initialize ledger file
            if not self.ledger_path.exists():
                with open(self.ledger_path, "w") as f:
                    record = {
                        "type": "platform_init",
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": PLATFORM_VERSION,
                        "event": "Multi-agent coding platform initialized",
                    }
                    f.write(json.dumps(record) + "\n")

            logger.info(f"◇ Ledger initialized at {self.ledger_path}")
            return True
        except Exception as e:
            logger.error(f"✗ Failed to initialize ledger: {e}")
            return False

    def start_mcp_servers(self) -> bool:
        """Start the MCP servers for external AI connections."""
        logger.info("⟡ Starting MCP Servers...")

        mcp_servers = [
            ("scbe_server", 8000, "Core SCBE governance gate"),
            ("swarm_server", 8001, "Swarm agent management"),
            ("orchestrator", 8002, "Central orchestration"),
            ("notion_server", 8003, "Notion integration (optional)"),
        ]

        for server_name, port, desc in mcp_servers:
            server_path = MCP_ROOT / f"{server_name}.py"
            if not server_path.exists():
                logger.warning(f"⟡ {server_name} not found, skipping")
                continue

            try:
                cmd = [
                    sys.executable,
                    str(server_path),
                    "--port",
                    str(port),
                ]
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=str(SCBE_ROOT),
                )
                self.processes[f"mcp_{server_name}"] = proc
                logger.info(f"⟡ {server_name} ({desc}) listening on localhost:{port}")
            except Exception as e:
                logger.warning(f"⟡ Could not start {server_name}: {e}")

        return True

    def save_platform_config(self):
        """Save platform configuration for external clients."""
        config = {
            "platform": "SCBE-AETHERMOORE Multi-Agent Coding",
            "version": PLATFORM_VERSION,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "running",
            "mcp_servers": {
                "scbe_core": "localhost:8000",
                "swarm": "localhost:8001",
                "orchestrator": "localhost:8002",
                "notion": "localhost:8003",
            },
            "specialist_heads": {
                tongue_id: {
                    "name": info["name"],
                    "role": info["role"],
                    "port": self.mcp_ports.get(tongue_id, 9000 + i),
                }
                for i, (tongue_id, info) in enumerate(SACRED_TONGUES.items())
            },
            "governance": {
                "ledger": str(self.ledger_path),
                "policy": "SCBE-AETHERMOORE L13 Risk Gate (ALLOW/QUARANTINE/DENY)",
            },
            "how_to_connect": {
                "step_1": "Add .mcp.json entries for each server above",
                "step_2": "Use 'scbe_core' server for governance decisions",
                "step_3": "Route tasks through 'orchestrator' to specialist heads",
                "step_4": "All code reviews gated by L13 governance layer",
            },
        }

        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"✓ Platform config saved to {self.config_path}")

    def print_banner(self):
        """Print the platform banner."""
        print("""
╔═══════════════════════════════════════════════════════════════════════╗
║                                                                       ║
║         SCBE-AETHERMOORE Multi-Agent Coding Platform v1.0.0          ║
║                                                                       ║
║  A quantum-resistant AI governance stack for coordinated team coding  ║
║  across multiple LLM instances (Claude, Gemini, OpenAI, local, etc.) ║
║                                                                       ║
╚═══════════════════════════════════════════════════════════════════════╝

┌─ HYDRA 6-Head Specialist Swarm ──────────────────────────────────────┐
│                                                                       │
│  KO (Scout)      — Task discovery & planning                         │
│  AV (Vision)     — Code analysis & pattern recognition               │
│  RU (Reader)     — Documentation & knowledge retrieval                │
│  CA (Clicker)    — Interactive execution & testing                   │
│  UM (Typer)      — Code generation & writing                         │
│  DR (Judge)      — Quality review & governance                       │
│                                                                       │
└─ MCP Servers ───────────────────────────────────────────────────────┘

  🔐 Core Governance    → localhost:8000 (SCBE L13 Risk Gate)
  👥 Swarm Manager      → localhost:8001 (Agent coordination)
  🎯 Orchestrator       → localhost:8002 (Task routing)
  📔 Notion Integration  → localhost:8003 (Knowledge base)

┌─ Governance & Safety ────────────────────────────────────────────────┐
│                                                                       │
│  🛡️  All code is routed through L13 Risk Decision Gate               │
│  💾 All actions recorded in distributed ledger (JSONL)               │
│  ✅ Byzantine Fault Tolerant consensus between heads                 │
│  🚫 Multi-language injection detection (6 Sacred Tongues)            │
│  📊 Hyperbolic distance scaling: H(d,R) = R^(d²)                     │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
        """)

    async def run(self):
        """Launch the full platform."""
        self.print_banner()

        logger.info("=" * 70)
        logger.info("PLATFORM STARTUP SEQUENCE")
        logger.info("=" * 70)

        self.setup_directories()

        # Start components
        if not self.start_ledger():
            logger.error("✗ Failed to start ledger. Aborting.")
            return False

        await asyncio.sleep(0.5)

        if not self.start_spine():
            logger.error("✗ Failed to start Spine. Aborting.")
            return False

        await asyncio.sleep(1.0)

        if not self.start_heads():
            logger.error("✗ Failed to start Specialist Heads. Aborting.")
            return False

        await asyncio.sleep(1.0)

        if not self.start_mcp_servers():
            logger.warning("⚠ Some MCP servers failed to start (non-critical)")

        await asyncio.sleep(1.0)

        # Save configuration
        self.save_platform_config()

        logger.info("=" * 70)
        logger.info("✓ PLATFORM READY")
        logger.info("=" * 70)
        logger.info(f"📋 Config saved to: {self.config_path}")
        logger.info(f"📝 Ledger at:       {self.ledger_path}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Update .mcp.json with servers above")
        logger.info("  2. Connect Claude/Gemini/OpenAI instances")
        logger.info("  3. Route code tasks through 'orchestrator'")
        logger.info("  4. Watch the ledger for governance decisions")
        logger.info("")

        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("\n↓ Shutting down platform...")
            self.shutdown()

    def shutdown(self):
        """Gracefully shutdown all processes."""
        for name, proc in self.processes.items():
            logger.info(f"  Stopping {name} (PID: {proc.pid})...")
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()

        logger.info("✓ Platform shutdown complete")


if __name__ == "__main__":
    launcher = PlatformLauncher()
    asyncio.run(launcher.run())
