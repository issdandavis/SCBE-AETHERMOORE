# SCBE Fleet Management System

> Secure AI Agent Fleet Orchestration with Sacred Tongue Governance

## Overview

The Fleet Management System integrates SCBE's security framework with AI workflow orchestration, enabling secure management of AI agent fleets with trust-based task assignment and Sacred Tongue governance.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      FleetManager                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Agent     │  │    Task     │  │      Governance         │  │
│  │  Registry   │  │ Dispatcher  │  │       Manager           │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                      │                │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌───────────┴─────────────┐  │
│  │   Trust     │  │  Spectral   │  │    Roundtable           │  │
│  │  Manager    │  │  Identity   │  │    Consensus            │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

```typescript
import { FleetManager, createDefaultFleet } from 'scbe-aethermoore/fleet';

// Create fleet with default agents
const fleet = createDefaultFleet();

// Or create custom fleet
const customFleet = new FleetManager({ autoAssign: true });

// Register an agent
const agent = customFleet.registerAgent({
  name: 'CodeGen-GPT4',
  description: 'Code generation specialist',
  provider: 'openai',
  model: 'gpt-4o',
  capabilities: ['code_generation', 'code_review'],
  maxGovernanceTier: 'CA',
  initialTrustVector: [0.7, 0.6, 0.8, 0.5, 0.6, 0.4]
});

// Create and assign a task
const task = customFleet.createTask({
  name: 'Generate API Handler',
  description: 'Create REST API endpoint',
  requiredCapability: 'code_generation',
  requiredTier: 'RU',
  priority: 'high',
  input: { prompt: 'Create a user authentication endpoint' }
});

// Complete the task
customFleet.completeTask(task.id, { code: '...' });
```

## Sacred Tongue Governance Tiers

| Tier | Name | Min Trust | Required Tongues | Operations |
|------|------|-----------|------------------|------------|
| KO | Koraelin | 0.1 | 1 | Read-only |
| AV | Avali | 0.3 | 2 | Write |
| RU | Runethic | 0.5 | 3 | Execute |
| CA | Cassisivadan | 0.7 | 4 | Deploy |
| UM | Umbroth | 0.85 | 5 | Admin |
| DR | Draumric | 0.95 | 6 | Critical/Destructive |

## Spectral Identity

Each agent receives a unique chromatic fingerprint based on their 6D trust vector:

```typescript
// Agent's spectral identity
{
  spectralHash: 'SP-A3F2-8B1C',
  hexCode: '#4A7B9C',
  colorName: 'Deep Blue',
  confidence: 'HIGH'
}
```

## Roundtable Consensus

Critical operations (UM/DR tier) require roundtable approval:

```typescript
// Create roundtable for critical operation
const session = fleet.createRoundtable({
  topic: 'Delete production database',
  requiredTier: 'DR'
});

// Agents vote
fleet.castVote(session.id, agent1.id, 'approve');
fleet.castVote(session.id, agent2.id, 'approve');
// ... requires 6 approvals for DR tier
```

## Event System

```typescript
fleet.onEvent(event => {
  switch (event.type) {
    case 'agent_registered':
    case 'task_completed':
    case 'security_alert':
      console.log(event);
  }
});
```

## Health Monitoring

```typescript
const health = fleet.getHealthStatus();
// { healthy: true, issues: [], metrics: { ... } }

const stats = fleet.getStatistics();
// { totalAgents, tasksByStatus, fleetSuccessRate, ... }
```

## Integration with AI Workflow Architect

The Fleet Management System is designed to integrate with the AI Workflow Architect's:
- MCP server for tool execution
- Agent orchestration queue
- Roundtable sessions for multi-AI collaboration
- Audit logging for compliance

See `external_repos/ai-workflow-architect/` for the full platform.
