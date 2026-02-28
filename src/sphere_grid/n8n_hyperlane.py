"""
n8n Hyperlane Bridge — connects sphere grid nodes via n8n workflows.

Each edge on the sphere grid = a "hyperlane" = an n8n workflow that fires
when traversal occurs. This module generates n8n workflow JSON and provides
the webhook endpoint interface for the FastAPI bridge.

Workflow pattern per hyperlane:
  1. Webhook trigger (receives traversal event)
  2. Governance scan (calls /v1/governance/scan on the bridge)
  3. Conditional: ALLOW -> execute target skill, DENY -> log + block
  4. Training data capture (append SFT pair to JSONL)
  5. State update (update the 21D CanonicalState)

All n8n workflows are generated programmatically and can be imported
via the existing import_workflows.ps1 infrastructure.
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional

from .canonical_state import TONGUE_NAMES, CanonicalState

# n8n instance config (local self-hosted, free)
N8N_BASE_URL = "http://127.0.0.1:5680"
BRIDGE_URL = "http://127.0.0.1:8001"


def generate_hyperlane_workflow(
    source_egg: str,
    target_egg: str,
    source_tongue: str,
    target_tongue: str,
    source_phase: str,
    target_phase: str,
    bridge_url: str = BRIDGE_URL,
) -> dict:
    """
    Generate an n8n workflow JSON for a single hyperlane (edge).

    The workflow:
      1. Webhook trigger: POST /webhook/hyperlane-{source}-to-{target}
      2. HTTP Request: governance scan via bridge
      3. IF node: check ALLOW/DENY/QUARANTINE
      4. On ALLOW: HTTP Request to target skill webhook
      5. Function node: generate training pair
      6. Write to file: append JSONL training data
    """
    workflow_name = f"Hyperlane: {source_egg} -> {target_egg}"
    lane_id = f"{source_egg}-to-{target_egg}"

    return {
        "name": workflow_name,
        "nodes": [
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": f"hyperlane-{lane_id}",
                    "responseMode": "onReceived",
                    "options": {},
                },
                "name": "Webhook Trigger",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [250, 300],
            },
            {
                "parameters": {
                    "url": f"{bridge_url}/v1/governance/scan",
                    "method": "POST",
                    "sendBody": True,
                    "bodyParameters": {
                        "parameters": [
                            {"name": "source", "value": f"={{{{$json.source_egg}}}}"},
                            {"name": "target", "value": f"={{{{$json.target_egg}}}}"},
                            {"name": "tongue", "value": source_tongue},
                            {"name": "phase", "value": target_phase},
                            {"name": "player_state", "value": "={{$json.player_state}}"},
                        ],
                    },
                    "options": {
                        "timeout": 10000,
                    },
                },
                "name": "Governance Scan",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 3,
                "position": [470, 300],
            },
            {
                "parameters": {
                    "conditions": {
                        "string": [
                            {
                                "value1": "={{$json.decision}}",
                                "operation": "equals",
                                "value2": "ALLOW",
                            },
                        ],
                    },
                },
                "name": "Gate Check",
                "type": "n8n-nodes-base.if",
                "typeVersion": 1,
                "position": [690, 300],
            },
            {
                "parameters": {
                    "url": f"{bridge_url}/v1/agent/task",
                    "method": "POST",
                    "sendBody": True,
                    "bodyParameters": {
                        "parameters": [
                            {"name": "skill", "value": target_egg},
                            {"name": "action", "value": "={{$json.action}}"},
                            {"name": "context", "value": "={{$json.context}}"},
                        ],
                    },
                    "options": {},
                },
                "name": "Execute Target Skill",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 3,
                "position": [910, 200],
            },
            {
                "parameters": {
                    "functionCode": f"""
// Generate SFT training pair from traversal
const pair = {{
    instruction: `Navigate hyperlane from {source_egg} to {target_egg}`,
    input: JSON.stringify({{
        source: '{source_egg}',
        target: '{target_egg}',
        source_tongue: '{source_tongue}',
        target_tongue: '{target_tongue}',
        source_phase: '{source_phase}',
        target_phase: '{target_phase}',
        player_state: $json.player_state,
        governance_decision: 'ALLOW',
    }}),
    output: JSON.stringify($json),
    metadata: {{
        lane: '{lane_id}',
        timestamp: new Date().toISOString(),
        type: 'hyperlane_traversal',
    }},
}};
return [{{ json: pair }}];
""",
                },
                "name": "Generate Training Pair",
                "type": "n8n-nodes-base.function",
                "typeVersion": 1,
                "position": [1130, 200],
            },
            {
                "parameters": {
                    "operation": "append",
                    "fileName": "C:\\Users\\issda\\SCBE-AETHERMOORE\\training-data\\sphere_grid_traversals.jsonl",
                    "options": {},
                },
                "name": "Write Training Data",
                "type": "n8n-nodes-base.readWriteFile",
                "typeVersion": 1,
                "position": [1350, 200],
            },
            {
                "parameters": {
                    "functionCode": """
// Log DENY/QUARANTINE for training (negative examples)
const pair = {
    instruction: `Blocked traversal attempt`,
    input: JSON.stringify($json),
    output: 'DENIED - governance gate blocked',
    metadata: {
        type: 'governance_block',
        timestamp: new Date().toISOString(),
    },
};
return [{ json: pair }];
""",
                },
                "name": "Log Blocked Traversal",
                "type": "n8n-nodes-base.function",
                "typeVersion": 1,
                "position": [910, 400],
            },
        ],
        "connections": {
            "Webhook Trigger": {
                "main": [
                    [{"node": "Governance Scan", "type": "main", "index": 0}],
                ],
            },
            "Governance Scan": {
                "main": [
                    [{"node": "Gate Check", "type": "main", "index": 0}],
                ],
            },
            "Gate Check": {
                "main": [
                    [{"node": "Execute Target Skill", "type": "main", "index": 0}],
                    [{"node": "Log Blocked Traversal", "type": "main", "index": 0}],
                ],
            },
            "Execute Target Skill": {
                "main": [
                    [{"node": "Generate Training Pair", "type": "main", "index": 0}],
                ],
            },
            "Generate Training Pair": {
                "main": [
                    [{"node": "Write Training Data", "type": "main", "index": 0}],
                ],
            },
        },
        "settings": {
            "executionOrder": "v1",
        },
        "tags": [
            {"name": "sphere-grid"},
            {"name": "hyperlane"},
            {"name": f"tongue-{source_tongue}"},
        ],
    }


def generate_all_hyperlane_workflows(
    grid,  # SphereGrid
    output_dir: Path,
    bridge_url: str = BRIDGE_URL,
) -> List[Path]:
    """
    Generate n8n workflow JSON files for all tested edges in the grid.
    Returns list of generated workflow file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    for edge in grid.edges:
        src_node = grid.nodes.get(edge.source)
        tgt_node = grid.nodes.get(edge.target)
        if not src_node or not tgt_node:
            continue

        workflow = generate_hyperlane_workflow(
            source_egg=edge.source,
            target_egg=edge.target,
            source_tongue=TONGUE_NAMES[src_node.primary_tongue],
            target_tongue=TONGUE_NAMES[tgt_node.primary_tongue],
            source_phase=src_node.phase,
            target_phase=tgt_node.phase,
            bridge_url=bridge_url,
        )

        filename = f"hyperlane_{edge.source}_to_{edge.target}.json"
        filepath = output_dir / filename
        filepath.write_text(json.dumps(workflow, indent=2), encoding="utf-8")
        generated.append(filepath)

    return generated


def generate_master_orchestrator_workflow(
    grid,  # SphereGrid
    bridge_url: str = BRIDGE_URL,
) -> dict:
    """
    Generate a single master n8n workflow that orchestrates the full
    SENSE -> PLAN -> EXECUTE -> PUBLISH pipeline.

    This is the "main loop" workflow that:
      1. Receives a task via webhook
      2. Determines current phase
      3. Selects optimal skill node via sphere grid navigator
      4. Fires the appropriate hyperlane
      5. Records telemetry
      6. Advances to next phase
    """
    return {
        "name": "Sphere Grid — Master Orchestrator",
        "nodes": [
            {
                "parameters": {
                    "httpMethod": "POST",
                    "path": "sphere-grid-orchestrate",
                    "responseMode": "lastNode",
                    "options": {},
                },
                "name": "Task Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [250, 300],
            },
            {
                "parameters": {
                    "functionCode": """
// Determine current phase and select optimal route
const task = $json;
const phases = ['SENSE', 'PLAN', 'EXECUTE', 'PUBLISH'];
const currentPhase = task.current_phase || 'SENSE';
const phaseIdx = phases.indexOf(currentPhase);

// Build routing decision
return [{
    json: {
        task_id: task.task_id || `task-${Date.now()}`,
        current_phase: currentPhase,
        next_phase: phaseIdx < 3 ? phases[phaseIdx + 1] : 'COMPLETE',
        player_state: task.player_state || [],
        action: task.action || 'auto',
        context: task.context || {},
    }
}];
""",
                },
                "name": "Route Selector",
                "type": "n8n-nodes-base.function",
                "typeVersion": 1,
                "position": [470, 300],
            },
            {
                "parameters": {
                    "url": f"{bridge_url}/v1/governance/scan",
                    "method": "POST",
                    "sendBody": True,
                    "bodyParameters": {
                        "parameters": [
                            {"name": "phase", "value": "={{$json.current_phase}}"},
                            {"name": "action", "value": "={{$json.action}}"},
                            {"name": "player_state", "value": "={{$json.player_state}}"},
                        ],
                    },
                    "options": {},
                },
                "name": "Phase Governance",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 3,
                "position": [690, 300],
            },
            {
                "parameters": {
                    "conditions": {
                        "string": [
                            {
                                "value1": "={{$json.next_phase}}",
                                "operation": "notEquals",
                                "value2": "COMPLETE",
                            },
                        ],
                    },
                },
                "name": "More Phases?",
                "type": "n8n-nodes-base.if",
                "typeVersion": 1,
                "position": [910, 300],
            },
            {
                "parameters": {
                    "url": f"{N8N_BASE_URL}/webhook/sphere-grid-orchestrate",
                    "method": "POST",
                    "sendBody": True,
                    "bodyParameters": {
                        "parameters": [
                            {"name": "current_phase", "value": "={{$json.next_phase}}"},
                            {"name": "task_id", "value": "={{$json.task_id}}"},
                            {"name": "player_state", "value": "={{$json.player_state}}"},
                            {"name": "action", "value": "={{$json.action}}"},
                        ],
                    },
                    "options": {},
                },
                "name": "Advance Phase (Loop)",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 3,
                "position": [1130, 200],
            },
            {
                "parameters": {
                    "functionCode": """
// Pipeline complete — collect results
return [{
    json: {
        status: 'COMPLETE',
        task_id: $json.task_id,
        phases_completed: ['SENSE', 'PLAN', 'EXECUTE', 'PUBLISH'],
        timestamp: new Date().toISOString(),
    }
}];
""",
                },
                "name": "Pipeline Complete",
                "type": "n8n-nodes-base.function",
                "typeVersion": 1,
                "position": [1130, 400],
            },
        ],
        "connections": {
            "Task Webhook": {
                "main": [[{"node": "Route Selector", "type": "main", "index": 0}]],
            },
            "Route Selector": {
                "main": [[{"node": "Phase Governance", "type": "main", "index": 0}]],
            },
            "Phase Governance": {
                "main": [[{"node": "More Phases?", "type": "main", "index": 0}]],
            },
            "More Phases?": {
                "main": [
                    [{"node": "Advance Phase (Loop)", "type": "main", "index": 0}],
                    [{"node": "Pipeline Complete", "type": "main", "index": 0}],
                ],
            },
        },
        "settings": {"executionOrder": "v1"},
        "tags": [{"name": "sphere-grid"}, {"name": "orchestrator"}],
    }
