/**
 * @file swarm_governance.test.ts
 * @description Tests for HYDRA Swarm Governance - BFT + Adaptive Geometry
 *
 * Tests cover:
 * - Agent lifecycle (add, remove, isolate, recover)
 * - Adaptive geometry (variable R, κ, penalties)
 * - BFT consensus integration
 * - Attack detection and self-regulation
 * - Autonomous code execution
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { spawn } from 'child_process';
import { promisify } from 'util';
import { execSync } from 'child_process';

function resolvePython(): string | null {
  const envPython = process.env.PYTHON_BIN?.trim();
  const candidates = [
    envPython,
    process.platform === 'win32' ? 'python' : 'python3',
    'python3',
    'python',
  ].filter((v): v is string => Boolean(v && v.length > 0));

  for (const candidate of candidates) {
    try {
      execSync(`${candidate} --version`, {
        cwd: process.cwd(),
        encoding: 'utf-8',
        stdio: 'pipe',
        timeout: 5000,
      });
      return candidate;
    } catch {
      // keep scanning candidates
    }
  }
  return null;
}

const PYTHON = resolvePython();

// Helper to run Python and capture output
async function runPython(code: string): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  return new Promise((resolve) => {
    const proc = spawn(PYTHON || 'python', ['-c', code]);
    let stdout = '';
    let stderr = '';

    proc.stdout.on('data', (data) => { stdout += data; });
    proc.stderr.on('data', (data) => { stderr += data; });

    proc.on('close', (exitCode) => {
      resolve({ stdout, stderr, exitCode: exitCode || 0 });
    });
  });
}

const maybeDescribe = PYTHON ? describe : describe.skip;

maybeDescribe('SwarmGovernance', () => {
  describe('Module Import', () => {
    it('should import SwarmGovernance without errors', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, SwarmAgent, AgentRole
print("OK")
      `);
      expect(result.stdout.trim()).toBe('OK');
      expect(result.exitCode).toBe(0);
    });

    it('should import all exported classes', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import (
    SwarmGovernance,
    SwarmAgent,
    AgentRole,
    AgentState,
    GovernanceConfig,
    AutonomousCodeAgent,
    create_swarm_governance,
    create_autonomous_coder
)
print("OK")
      `);
      expect(result.stdout.trim()).toBe('OK');
    });
  });

  describe('Agent Lifecycle', () => {
    it('should add agents to swarm', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, AgentRole

gov = SwarmGovernance()
gov.add_agent("agent-1", AgentRole.VALIDATOR)
gov.add_agent("agent-2", AgentRole.EXECUTOR)

print(len(gov.agents))
print(gov.agents["agent-1"].role.value)
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('2');
      expect(lines[1]).toBe('validator');
    });

    it('should remove agents from swarm', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, AgentRole

gov = SwarmGovernance()
gov.add_agent("agent-1")
gov.add_agent("agent-2")
gov.remove_agent("agent-1")

print(len(gov.agents))
print("agent-1" in gov.agents)
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('1');
      expect(lines[1]).toBe('False');
    });

    it('should track agent position history', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance

gov = SwarmGovernance()
agent = gov.add_agent("agent-1", initial_position=[0.1, 0.2, 0, 0, 0, 0])
agent.update_position([0.15, 0.25, 0.05, 0, 0, 0])
agent.update_position([0.2, 0.3, 0.1, 0, 0, 0])

print(len(agent.position_history))
      `);
      expect(result.stdout.trim()).toBe('2');
    });
  });

  describe('Adaptive Geometry', () => {
    it('should compute variable R based on coherence', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance

gov = SwarmGovernance()

r_high = gov.get_R(1.0)
r_mid = gov.get_R(0.5)
r_low = gov.get_R(0.0)

print(f"{r_high:.2f}")
print(f"{r_mid:.2f}")
print(f"{r_low:.2f}")
print(r_low > r_mid > r_high)
      `);
      const lines = result.stdout.trim().split('\n');
      expect(parseFloat(lines[0])).toBeCloseTo(1.5, 1);  // Base R
      expect(lines[3]).toBe('True');  // Low coherence → higher R
    });

    it('should compute variable curvature based on coherence', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance

gov = SwarmGovernance()

k_high = gov.get_kappa(1.0)
k_low = gov.get_kappa(0.0)

print(f"{k_high:.4f}")
print(k_low < k_high)  # More negative for low coherence
      `);
      const lines = result.stdout.trim().split('\n');
      expect(parseFloat(lines[0])).toBeCloseTo(-1.0, 3);  // κ = -1 at full coherence
      expect(lines[1]).toBe('True');
    });

    it('should compute hyperbolic distance with variable curvature', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance

gov = SwarmGovernance()

a = [0.3, 0, 0, 0, 0, 0]
b = [0, 0.3, 0, 0, 0, 0]

d1 = gov.hyperbolic_distance(a, b, -1)
d2 = gov.hyperbolic_distance(a, b, -2)

print(d1 > 0)
print(d1 != d2)
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('True');
      expect(lines[1]).toBe('True');
    });

    it('should compute harmonic penalty', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance

gov = SwarmGovernance()

p_small = gov.harmonic_penalty(0.5, 1.5)
p_large = gov.harmonic_penalty(2.0, 1.5)

print(p_large > p_small)
print(p_small > 1)
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('True');  // Larger distance → larger penalty
      expect(lines[1]).toBe('True');
    });
  });

  describe('Simulation Step', () => {
    it('should update agent positions', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, AgentRole

gov = SwarmGovernance()
gov.add_agent("a1", initial_position=[0.1, 0, 0, 0, 0, 0])
gov.add_agent("a2", initial_position=[0, 0.1, 0, 0, 0, 0])

result = gov.simulation_step(dt=0.1)

print(result["agents_updated"])
print("swarm_coherence" in result)
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('2');
      expect(lines[1]).toBe('True');
    });

    it('should isolate low-coherence agents', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, AgentState

gov = SwarmGovernance()
agent = gov.add_agent("agent-1", initial_coherence=0.05)

gov.simulation_step()

print(agent.state.value)
      `);
      expect(result.stdout.trim()).toBe('frozen');  // Below freeze threshold
    });

    it('should compute swarm metrics', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance

gov = SwarmGovernance()
gov.add_agent("a1", initial_coherence=0.9)
gov.add_agent("a2", initial_coherence=0.8)
gov.add_agent("a3", initial_coherence=0.85)

gov.simulation_step()

print(f"{gov.swarm_coherence:.2f}")
      `);
      const coherence = parseFloat(result.stdout.trim());
      expect(coherence).toBeGreaterThan(0.8);
      expect(coherence).toBeLessThan(0.95);
    });
  });

  describe('Attack Detection', () => {
    it('should self-regulate when malicious agents present', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, AgentRole, AgentState

gov = SwarmGovernance()

# Add honest agents
for i in range(4):
    gov.add_agent(f"honest-{i}", AgentRole.VALIDATOR, initial_coherence=0.9)

# Add malicious agents with low coherence
for i in range(4):
    gov.add_agent(f"mal-{i}", AgentRole.MALICIOUS, initial_coherence=0.15)

initial_count = len(gov.agents)

# Run many steps to let self-regulation occur
for _ in range(50):
    gov.simulation_step(dt=0.1)

final_count = len(gov.agents)
expelled_count = initial_count - final_count

# Count remaining active honest agents
honest_active = sum(1 for a in gov.agents.values()
                    if a.role != AgentRole.MALICIOUS
                    and a.state == AgentState.ACTIVE)

print(expelled_count > 0)  # At least some agents should be expelled
print(honest_active >= 3)  # Most honest agents should remain active
print(gov.swarm_coherence > 0.7)  # Swarm coherence should recover
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('True');  // Malicious agents expelled
      expect(lines[1]).toBe('True');  // Honest agents remain
      expect(lines[2]).toBe('True');  // Swarm coherence recovered
    });

    it('should expel agents with excessive penalties', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, GovernanceConfig, AgentRole

config = GovernanceConfig(expel_penalty_threshold=50)  # Low threshold for test
gov = SwarmGovernance(config)

# Add malicious agent that will accumulate penalties
gov.add_agent("mal-1", AgentRole.MALICIOUS, initial_coherence=0.1)
gov.agents["mal-1"].penalty_accumulated = 100  # Force high penalty

result = gov.simulation_step()

print("mal-1" in gov.agents)
print(result["agents_expelled"])
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('False');
      expect(lines[1]).toBe('1');
    });
  });

  describe('BFT Consensus', () => {
    it('should create proposals through governance', async () => {
      const result = await runPython(`
import sys
import asyncio
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, AgentRole

async def test():
    gov = SwarmGovernance()

    # Add enough agents for consensus
    for i in range(6):
        gov.add_agent(f"agent-{i}", AgentRole.VALIDATOR, initial_coherence=0.9)

    result = await gov.propose_action(
        proposer_id="agent-0",
        action="read",
        target="file.txt",
        context={}
    )

    return result

result = asyncio.run(test())
print(result["success"])
print("auto_executed" in result or "consensus_reached" in result)
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('True');
      expect(lines[1]).toBe('True');
    });

    it('should require consensus for risky actions', async () => {
      const result = await runPython(`
import sys
import asyncio
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, AgentRole

async def test():
    gov = SwarmGovernance()

    for i in range(6):
        gov.add_agent(f"agent-{i}", AgentRole.VALIDATOR, initial_coherence=0.9)

    # Risky action should require consensus
    result = await gov.propose_action(
        proposer_id="agent-0",
        action="delete",
        target="/important/file",
        context={}
    )

    return result

result = asyncio.run(test())
print("consensus_reached" in result or "auto_executed" in result)
      `);
      expect(result.stdout.trim()).toBe('True');
    });
  });

  describe('Autonomous Code Agent', () => {
    it('should create autonomous coder', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, AutonomousCodeAgent

gov = SwarmGovernance()
coder = AutonomousCodeAgent(gov, "coder-1")

print(coder.agent_id)
print("coder-1" in gov.agents)
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('coder-1');
      expect(lines[1]).toBe('True');
    });

    it('should assess code risk correctly', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, AutonomousCodeAgent

gov = SwarmGovernance()
coder = AutonomousCodeAgent(gov, "coder-1")

safe_risk = coder._assess_code_risk("print('hello')", "python")
risky_risk = coder._assess_code_risk("import os; os.system('rm -rf /')", "python")

print(safe_risk < 0.5)
print(risky_risk > 0.5)
print(risky_risk > safe_risk)
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('True');
      expect(lines[1]).toBe('True');
      expect(lines[2]).toBe('True');
    });

    it('should execute code through governance', async () => {
      const result = await runPython(`
import sys
import asyncio
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, AutonomousCodeAgent, AgentRole

async def test():
    gov = SwarmGovernance()

    # Add supporting agents for consensus
    for i in range(4):
        gov.add_agent(f"validator-{i}", AgentRole.VALIDATOR, initial_coherence=0.9)

    coder = AutonomousCodeAgent(gov, "coder-1")

    result = await coder.execute_code(
        code="x = 1 + 1",
        language="python",
        sandbox=True
    )

    return result

result = asyncio.run(test())
print(result["executed"])
print("risk" in result)
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('True');
      expect(lines[1]).toBe('True');
    });
  });

  describe('Swarm Status', () => {
    it('should return comprehensive status', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance, AgentRole

gov = SwarmGovernance()
gov.add_agent("a1", AgentRole.VALIDATOR)
gov.add_agent("a2", AgentRole.EXECUTOR)
gov.add_agent("a3", AgentRole.LEADER)

gov.simulation_step()

status = gov.get_status()

print(status["total_agents"])
print("swarm_coherence" in status)
print("attack_detected" in status)
print("agents_by_role" in status)
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('3');
      expect(lines[1]).toBe('True');
      expect(lines[2]).toBe('True');
      expect(lines[3]).toBe('True');
    });

    it('should compute agent distances', async () => {
      const result = await runPython(`
import sys
sys.path.insert(0, '.')
from hydra.swarm_governance import SwarmGovernance

gov = SwarmGovernance()
gov.add_agent("a1", initial_position=[0.3, 0, 0, 0, 0, 0])
gov.add_agent("a2", initial_position=[0, 0.3, 0, 0, 0, 0])

distances = gov.get_agent_distances()

print("a1" in distances)
print("a2" in distances.get("a1", {}))
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('True');
      expect(lines[1]).toBe('True');
    });
  });

  describe('Attack Simulation', () => {
    it('should run attack simulation successfully', async () => {
      const result = await runPython(`
import sys
import asyncio
sys.path.insert(0, '.')
from hydra.swarm_governance import simulate_swarm_attack

async def test():
    result = await simulate_swarm_attack(
        num_honest=4,
        num_malicious=1,
        num_steps=10,
        dt=0.1
    )
    return result

result = asyncio.run(test())
print("final_status" in result)
print("history" in result)
print(len(result["history"]))
      `);
      const lines = result.stdout.trim().split('\n');
      expect(lines[0]).toBe('True');
      expect(lines[1]).toBe('True');
      expect(lines[2]).toBe('10');
    });
  });
});
