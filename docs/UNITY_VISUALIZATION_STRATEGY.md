# Unity Visualization Strategy for Spiralverse

**Document Status:** Planning
**Target Platform:** Unity 2022.3 LTS (or newer)
**Estimated Effort:** 4-6 weeks

---

## 1. Executive Summary

The Spiralverse visualization system will provide real-time 3D rendering of:

1. **Swarm Agent Networks** - 6D positions projected to 3D with trust coloring
2. **Contact Graph Topology** - Force-directed network visualization
3. **Trust Vector Heatmaps** - Per-tongue contribution display
4. **PHDM Polyhedra** - 16 canonical polyhedra in hyperbolic space
5. **Circuit Construction** - Animated onion routing paths
6. **Temporal Playback** - Recording and replay of swarm evolution

**Why Unity over Web?**
- Native 3D performance for 1000+ agents
- VR/AR readiness for immersive monitoring
- GPU-accelerated particle systems for swarm visualization
- Professional game-engine tooling and asset ecosystem
- Cross-platform deployment (Windows, Mac, Linux, WebGL)

---

## 2. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    SPIRALVERSE UNITY DASHBOARD                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────┐    ┌────────────────┐    ┌───────────────┐  │
│  │  SCBE Backend  │───▶│  WebSocket API │───▶│ Unity Client  │  │
│  │  (Python/TS)   │    │  (FastAPI)     │    │               │  │
│  └────────────────┘    └────────────────┘    └───────┬───────┘  │
│                                                      │          │
│                                                      ▼          │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                     UNITY SCENES                          │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │   Swarm     │  │   Contact   │  │    PHDM     │       │  │
│  │  │  Dashboard  │  │    Graph    │  │   Explorer  │       │  │
│  │  │  (3D View)  │  │  (Network)  │  │ (Polyhedra) │       │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │  │
│  │  │   Trust     │  │   Circuit   │  │   Mission   │       │  │
│  │  │  Heatmap    │  │  Animation  │  │  Timeline   │       │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘       │  │
│  │                                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Project Structure

```
unity-spiralverse/
├── Assets/
│   ├── Scripts/
│   │   ├── Core/
│   │   │   ├── WebSocketClient.cs      # Real-time data connection
│   │   │   ├── DataModels.cs           # C# data classes
│   │   │   ├── VisualizationManager.cs # Scene orchestration
│   │   │   └── CameraController.cs     # Free-fly camera
│   │   │
│   │   ├── Swarm/
│   │   │   ├── SwarmVisualizer.cs      # Agent rendering
│   │   │   ├── AgentController.cs      # Individual agent logic
│   │   │   ├── TrustConnection.cs      # Edge rendering
│   │   │   └── Position6DProjector.cs  # 6D → 3D projection
│   │   │
│   │   ├── ContactGraph/
│   │   │   ├── GraphRenderer.cs        # Force-directed layout
│   │   │   ├── NodeVisual.cs           # Node styling
│   │   │   ├── EdgeVisual.cs           # Edge styling
│   │   │   └── PathHighlighter.cs      # Route highlighting
│   │   │
│   │   ├── PHDM/
│   │   │   ├── PolyhedronGenerator.cs  # Procedural mesh generation
│   │   │   ├── HamiltonianPath.cs      # Path visualization
│   │   │   └── HyperbolicSpace.cs      # Poincaré ball projection
│   │   │
│   │   ├── Trust/
│   │   │   ├── TrustHeatmap.cs         # 6-tongue heatmap
│   │   │   ├── TongueColorScheme.cs    # KO/AV/RU/CA/UM/DR colors
│   │   │   └── HistoryGraph.cs         # Trust over time
│   │   │
│   │   └── UI/
│   │       ├── DashboardPanel.cs       # Main UI
│   │       ├── AgentInspector.cs       # Selected agent details
│   │       ├── MetricsDisplay.cs       # Real-time stats
│   │       └── TimelineControl.cs      # Playback controls
│   │
│   ├── Prefabs/
│   │   ├── Agent/
│   │   │   ├── AgentSphere.prefab      # Basic agent visual
│   │   │   ├── AgentGlow.prefab        # Trust-based glow
│   │   │   └── AgentTrail.prefab       # Movement trail
│   │   │
│   │   ├── Network/
│   │   │   ├── ConnectionLine.prefab   # Trust edge
│   │   │   ├── RouteHighlight.prefab   # Active circuit
│   │   │   └── NodeMarker.prefab       # Graph node
│   │   │
│   │   └── PHDM/
│   │       ├── Tetrahedron.prefab
│   │       ├── Cube.prefab
│   │       ├── Octahedron.prefab
│   │       ├── Dodecahedron.prefab
│   │       ├── Icosahedron.prefab
│   │       └── ... (11 more polyhedra)
│   │
│   ├── Materials/
│   │   ├── TrustHigh.mat               # Green glow
│   │   ├── TrustMedium.mat             # Yellow glow
│   │   ├── TrustLow.mat                # Orange glow
│   │   ├── TrustCritical.mat           # Red glow
│   │   ├── ConnectionActive.mat        # Active edge
│   │   ├── ConnectionInactive.mat      # Dormant edge
│   │   └── TongueColors/
│   │       ├── KO_Koraelin.mat         # Blue - Control
│   │       ├── AV_Avali.mat            # Green - I/O
│   │       ├── RU_Runethic.mat         # Stone gray - Policy
│   │       ├── CA_Cassisivadan.mat     # Gold - Logic
│   │       ├── UM_Umbroth.mat          # Purple - Security
│   │       └── DR_Draumric.mat         # Orange - Types
│   │
│   ├── Shaders/
│   │   ├── HyperbolicSpace.shader      # Poincaré ball distortion
│   │   ├── TrustGlow.shader            # Agent emission
│   │   ├── ConnectionFlow.shader       # Animated edge
│   │   └── HeatmapSurface.shader       # Trust heatmap
│   │
│   └── Scenes/
│       ├── MainDashboard.unity         # Primary monitoring view
│       ├── ContactGraphExplorer.unity  # Network topology
│       ├── PHDMVisualizer.unity        # Polyhedra exploration
│       ├── SwarmSimulator.unity        # Standalone simulation
│       └── VRImmersive.unity           # VR mode (optional)
│
├── Packages/
│   └── manifest.json
│
├── ProjectSettings/
│   └── ...
│
└── README.md
```

---

## 4. Data Models (C#)

```csharp
// DataModels.cs

using System;
using System.Collections.Generic;
using UnityEngine;

namespace Spiralverse.Data
{
    [Serializable]
    public class Agent6D
    {
        public string id;
        public float[] position;  // [x, y, z, v, h, s]
        public float trustScore;
        public string trustLevel;  // HIGH, MEDIUM, LOW, CRITICAL
        public float[] trustVector;  // [KO, AV, RU, CA, UM, DR]
        public string swarmId;
        public string dimensionalState;  // POLLY, QUASI, DEMI, COLLAPSED
        public float nu;  // Flux coefficient
        public long lastUpdate;
    }

    [Serializable]
    public class ContactEdge
    {
        public string id;
        public string source;
        public string target;
        public float latency;
        public float capacity;
        public float confidence;
        public long startTime;
        public long endTime;
    }

    [Serializable]
    public class SwarmState
    {
        public string swarmId;
        public List<Agent6D> agents;
        public List<ContactEdge> edges;
        public float coherenceScore;
        public string dominantState;
        public long timestamp;
    }

    [Serializable]
    public class TrustHistory
    {
        public string agentId;
        public List<TrustSnapshot> history;
    }

    [Serializable]
    public class TrustSnapshot
    {
        public long timestamp;
        public float score;
        public float[] vector;
        public bool anomaly;
    }

    [Serializable]
    public class CircuitPath
    {
        public string circuitId;
        public List<string> nodes;
        public float totalLatency;
        public float reliability;
        public string status;  // BUILDING, ACTIVE, FAILED
    }

    // Six Sacred Tongues color mapping
    public static class TongueColors
    {
        public static readonly Color KO = new Color(0.2f, 0.4f, 0.8f);   // Blue
        public static readonly Color AV = new Color(0.2f, 0.8f, 0.4f);   // Green
        public static readonly Color RU = new Color(0.5f, 0.5f, 0.5f);   // Gray
        public static readonly Color CA = new Color(0.9f, 0.8f, 0.2f);   // Gold
        public static readonly Color UM = new Color(0.6f, 0.2f, 0.8f);   // Purple
        public static readonly Color DR = new Color(0.9f, 0.5f, 0.2f);   // Orange

        public static Color GetColor(int index)
        {
            return index switch
            {
                0 => KO,
                1 => AV,
                2 => RU,
                3 => CA,
                4 => UM,
                5 => DR,
                _ => Color.white
            };
        }
    }
}
```

---

## 5. Core Scripts

### 5.1 WebSocket Client

```csharp
// WebSocketClient.cs

using System;
using System.Collections;
using UnityEngine;
using WebSocketSharp;
using Spiralverse.Data;
using Newtonsoft.Json;

namespace Spiralverse.Core
{
    public class WebSocketClient : MonoBehaviour
    {
        [Header("Connection Settings")]
        public string serverUrl = "ws://localhost:8000/ws/swarm/main";
        public float reconnectDelay = 5f;

        [Header("Events")]
        public event Action<SwarmState> OnSwarmUpdate;
        public event Action<CircuitPath> OnCircuitUpdate;
        public event Action OnConnected;
        public event Action OnDisconnected;

        private WebSocket ws;
        private bool shouldReconnect = true;

        void Start()
        {
            Connect();
        }

        void OnDestroy()
        {
            shouldReconnect = false;
            ws?.Close();
        }

        public void Connect()
        {
            try
            {
                ws = new WebSocket(serverUrl);

                ws.OnOpen += (sender, e) =>
                {
                    Debug.Log($"[Spiralverse] Connected to {serverUrl}");
                    UnityMainThreadDispatcher.Instance().Enqueue(() => OnConnected?.Invoke());
                };

                ws.OnMessage += (sender, e) =>
                {
                    ProcessMessage(e.Data);
                };

                ws.OnClose += (sender, e) =>
                {
                    Debug.Log("[Spiralverse] Disconnected");
                    UnityMainThreadDispatcher.Instance().Enqueue(() =>
                    {
                        OnDisconnected?.Invoke();
                        if (shouldReconnect)
                            StartCoroutine(ReconnectAfterDelay());
                    });
                };

                ws.OnError += (sender, e) =>
                {
                    Debug.LogError($"[Spiralverse] WebSocket error: {e.Message}");
                };

                ws.Connect();
            }
            catch (Exception ex)
            {
                Debug.LogError($"[Spiralverse] Connection failed: {ex.Message}");
                if (shouldReconnect)
                    StartCoroutine(ReconnectAfterDelay());
            }
        }

        private IEnumerator ReconnectAfterDelay()
        {
            yield return new WaitForSeconds(reconnectDelay);
            Connect();
        }

        private void ProcessMessage(string json)
        {
            try
            {
                // Determine message type from JSON structure
                if (json.Contains("\"agents\""))
                {
                    var state = JsonConvert.DeserializeObject<SwarmState>(json);
                    UnityMainThreadDispatcher.Instance().Enqueue(() =>
                        OnSwarmUpdate?.Invoke(state));
                }
                else if (json.Contains("\"circuitId\""))
                {
                    var circuit = JsonConvert.DeserializeObject<CircuitPath>(json);
                    UnityMainThreadDispatcher.Instance().Enqueue(() =>
                        OnCircuitUpdate?.Invoke(circuit));
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[Spiralverse] Failed to parse message: {ex.Message}");
            }
        }

        public void SendCommand(string command)
        {
            if (ws?.ReadyState == WebSocketState.Open)
            {
                ws.Send(command);
            }
        }
    }
}
```

### 5.2 Swarm Visualizer

```csharp
// SwarmVisualizer.cs

using System.Collections.Generic;
using UnityEngine;
using Spiralverse.Data;

namespace Spiralverse.Swarm
{
    public class SwarmVisualizer : MonoBehaviour
    {
        [Header("Prefabs")]
        public GameObject agentPrefab;
        public GameObject connectionPrefab;

        [Header("Materials")]
        public Material trustHighMat;
        public Material trustMediumMat;
        public Material trustLowMat;
        public Material trustCriticalMat;

        [Header("Settings")]
        public float positionScale = 10f;
        public float transitionSpeed = 5f;
        public float connectionThreshold = 0.3f;

        [Header("6D Projection")]
        public ProjectionMode projectionMode = ProjectionMode.PCA;
        public Vector3[] projectionWeights = new Vector3[6];

        private Dictionary<string, GameObject> agents = new();
        private Dictionary<string, LineRenderer> connections = new();
        private WebSocketClient wsClient;

        public enum ProjectionMode
        {
            PCA,        // Principal component analysis
            Manual,     // Custom weights
            Split       // XYZ + color from VHS
        }

        void Start()
        {
            wsClient = FindObjectOfType<WebSocketClient>();
            wsClient.OnSwarmUpdate += UpdateSwarm;

            // Default projection weights (6D → 3D)
            projectionWeights[0] = new Vector3(1, 0, 0);   // X → X
            projectionWeights[1] = new Vector3(0, 1, 0);   // Y → Y
            projectionWeights[2] = new Vector3(0, 0, 1);   // Z → Z
            projectionWeights[3] = new Vector3(0.3f, 0, 0); // V → X influence
            projectionWeights[4] = new Vector3(0, 0.3f, 0); // H → Y influence
            projectionWeights[5] = new Vector3(0, 0, 0.3f); // S → Z influence
        }

        void OnDestroy()
        {
            if (wsClient != null)
                wsClient.OnSwarmUpdate -= UpdateSwarm;
        }

        private void UpdateSwarm(SwarmState state)
        {
            HashSet<string> activeIds = new();

            foreach (var agent in state.agents)
            {
                activeIds.Add(agent.id);
                UpdateAgent(agent);
            }

            // Remove stale agents
            List<string> toRemove = new();
            foreach (var kvp in agents)
            {
                if (!activeIds.Contains(kvp.Key))
                {
                    Destroy(kvp.Value);
                    toRemove.Add(kvp.Key);
                }
            }
            foreach (var id in toRemove)
            {
                agents.Remove(id);
            }

            // Update connections
            UpdateConnections(state);
        }

        private void UpdateAgent(Agent6D agent)
        {
            if (!agents.TryGetValue(agent.id, out GameObject go))
            {
                go = Instantiate(agentPrefab, transform);
                go.name = $"Agent_{agent.id}";
                agents[agent.id] = go;
            }

            // Project 6D to 3D
            Vector3 targetPos = Project6Dto3D(agent.position);

            // Smooth movement
            go.transform.position = Vector3.Lerp(
                go.transform.position,
                targetPos,
                Time.deltaTime * transitionSpeed
            );

            // Update material based on trust
            var renderer = go.GetComponent<Renderer>();
            renderer.material = agent.trustLevel switch
            {
                "HIGH" => trustHighMat,
                "MEDIUM" => trustMediumMat,
                "LOW" => trustLowMat,
                _ => trustCriticalMat
            };

            // Scale by flux coefficient (nu)
            float scale = Mathf.Lerp(0.5f, 1.5f, agent.nu);
            go.transform.localScale = Vector3.one * scale;

            // Store data for inspection
            var controller = go.GetComponent<AgentController>();
            if (controller != null)
                controller.SetData(agent);
        }

        private Vector3 Project6Dto3D(float[] pos6d)
        {
            if (pos6d == null || pos6d.Length < 6)
                return Vector3.zero;

            Vector3 result = Vector3.zero;

            switch (projectionMode)
            {
                case ProjectionMode.PCA:
                    // Simple additive projection
                    for (int i = 0; i < 6; i++)
                    {
                        result += projectionWeights[i] * pos6d[i];
                    }
                    break;

                case ProjectionMode.Manual:
                    // Custom weighted sum
                    for (int i = 0; i < 6; i++)
                    {
                        result += projectionWeights[i] * pos6d[i];
                    }
                    break;

                case ProjectionMode.Split:
                    // XYZ from first 3, color from last 3
                    result = new Vector3(pos6d[0], pos6d[1], pos6d[2]);
                    break;
            }

            return result * positionScale;
        }

        private void UpdateConnections(SwarmState state)
        {
            HashSet<string> activeEdges = new();

            foreach (var edge in state.edges)
            {
                string edgeKey = $"{edge.source}_{edge.target}";
                activeEdges.Add(edgeKey);

                if (!agents.TryGetValue(edge.source, out var sourceGO) ||
                    !agents.TryGetValue(edge.target, out var targetGO))
                    continue;

                if (!connections.TryGetValue(edgeKey, out var line))
                {
                    var lineGO = Instantiate(connectionPrefab, transform);
                    line = lineGO.GetComponent<LineRenderer>();
                    connections[edgeKey] = line;
                }

                // Update line positions
                line.SetPosition(0, sourceGO.transform.position);
                line.SetPosition(1, targetGO.transform.position);

                // Color by confidence
                Color color = Color.Lerp(Color.red, Color.green, edge.confidence);
                line.startColor = color;
                line.endColor = color;

                // Width by capacity
                float width = Mathf.Lerp(0.01f, 0.1f, edge.capacity / 1_000_000f);
                line.startWidth = width;
                line.endWidth = width;
            }

            // Remove stale connections
            List<string> toRemove = new();
            foreach (var kvp in connections)
            {
                if (!activeEdges.Contains(kvp.Key))
                {
                    Destroy(kvp.Value.gameObject);
                    toRemove.Add(kvp.Key);
                }
            }
            foreach (var key in toRemove)
            {
                connections.Remove(key);
            }
        }
    }
}
```

### 5.3 PHDM Polyhedron Generator

```csharp
// PolyhedronGenerator.cs

using UnityEngine;
using System.Collections.Generic;

namespace Spiralverse.PHDM
{
    public class PolyhedronGenerator : MonoBehaviour
    {
        public enum PolyhedronType
        {
            Tetrahedron,
            Cube,
            Octahedron,
            Dodecahedron,
            Icosahedron,
            TruncatedTetrahedron,
            Cuboctahedron,
            TruncatedCube,
            TruncatedOctahedron,
            Rhombicuboctahedron,
            TruncatedCuboctahedron,
            SnubCube,
            Icosidodecahedron,
            TruncatedDodecahedron,
            TruncatedIcosahedron,
            SmallStellatedDodecahedron
        }

        public static Mesh GeneratePolyhedron(PolyhedronType type)
        {
            return type switch
            {
                PolyhedronType.Tetrahedron => GenerateTetrahedron(),
                PolyhedronType.Cube => GenerateCube(),
                PolyhedronType.Octahedron => GenerateOctahedron(),
                PolyhedronType.Dodecahedron => GenerateDodecahedron(),
                PolyhedronType.Icosahedron => GenerateIcosahedron(),
                _ => GenerateIcosahedron()  // Default
            };
        }

        private static Mesh GenerateTetrahedron()
        {
            Mesh mesh = new Mesh();

            float a = 1f / Mathf.Sqrt(2f);

            Vector3[] vertices = new Vector3[]
            {
                new Vector3(1, 0, -a),
                new Vector3(-1, 0, -a),
                new Vector3(0, 1, a),
                new Vector3(0, -1, a)
            };

            int[] triangles = new int[]
            {
                0, 1, 2,
                0, 2, 3,
                0, 3, 1,
                1, 3, 2
            };

            mesh.vertices = vertices;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();

            return mesh;
        }

        private static Mesh GenerateCube()
        {
            Mesh mesh = new Mesh();

            Vector3[] vertices = new Vector3[]
            {
                new Vector3(-1, -1, -1),
                new Vector3(1, -1, -1),
                new Vector3(1, 1, -1),
                new Vector3(-1, 1, -1),
                new Vector3(-1, -1, 1),
                new Vector3(1, -1, 1),
                new Vector3(1, 1, 1),
                new Vector3(-1, 1, 1)
            };

            int[] triangles = new int[]
            {
                0, 2, 1, 0, 3, 2,  // Front
                1, 6, 5, 1, 2, 6,  // Right
                5, 7, 4, 5, 6, 7,  // Back
                4, 3, 0, 4, 7, 3,  // Left
                3, 6, 2, 3, 7, 6,  // Top
                4, 1, 5, 4, 0, 1   // Bottom
            };

            mesh.vertices = vertices;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();

            return mesh;
        }

        private static Mesh GenerateOctahedron()
        {
            Mesh mesh = new Mesh();

            Vector3[] vertices = new Vector3[]
            {
                new Vector3(0, 1, 0),
                new Vector3(1, 0, 0),
                new Vector3(0, 0, 1),
                new Vector3(-1, 0, 0),
                new Vector3(0, 0, -1),
                new Vector3(0, -1, 0)
            };

            int[] triangles = new int[]
            {
                0, 1, 2,
                0, 2, 3,
                0, 3, 4,
                0, 4, 1,
                5, 2, 1,
                5, 3, 2,
                5, 4, 3,
                5, 1, 4
            };

            mesh.vertices = vertices;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();

            return mesh;
        }

        private static Mesh GenerateDodecahedron()
        {
            Mesh mesh = new Mesh();

            float phi = (1f + Mathf.Sqrt(5f)) / 2f;  // Golden ratio
            float a = 1f;
            float b = 1f / phi;
            float c = 2f - phi;

            List<Vector3> verts = new List<Vector3>
            {
                new Vector3(c, 0, a),
                new Vector3(-c, 0, a),
                new Vector3(-b, b, b),
                new Vector3(0, a, c),
                new Vector3(b, b, b),
                new Vector3(b, -b, b),
                new Vector3(0, -a, c),
                new Vector3(-b, -b, b),
                new Vector3(c, 0, -a),
                new Vector3(-c, 0, -a),
                new Vector3(-b, -b, -b),
                new Vector3(0, -a, -c),
                new Vector3(b, -b, -b),
                new Vector3(b, b, -b),
                new Vector3(0, a, -c),
                new Vector3(-b, b, -b),
                new Vector3(a, c, 0),
                new Vector3(-a, c, 0),
                new Vector3(-a, -c, 0),
                new Vector3(a, -c, 0)
            };

            // Simplified triangulation (pentagon faces)
            List<int> tris = new List<int>();

            // This is a simplified version - full implementation would
            // triangulate each pentagonal face properly
            int[] faces = new int[]
            {
                0, 1, 2, 3, 4,
                0, 4, 16, 19, 5,
                // ... additional faces
            };

            // For now, use icosahedron as placeholder
            return GenerateIcosahedron();
        }

        private static Mesh GenerateIcosahedron()
        {
            Mesh mesh = new Mesh();

            float phi = (1f + Mathf.Sqrt(5f)) / 2f;
            float a = 1f;
            float b = 1f / phi;

            Vector3[] vertices = new Vector3[]
            {
                new Vector3(0, b, -a),
                new Vector3(b, a, 0),
                new Vector3(-b, a, 0),
                new Vector3(0, b, a),
                new Vector3(0, -b, a),
                new Vector3(-a, 0, b),
                new Vector3(0, -b, -a),
                new Vector3(a, 0, -b),
                new Vector3(a, 0, b),
                new Vector3(-a, 0, -b),
                new Vector3(b, -a, 0),
                new Vector3(-b, -a, 0)
            };

            int[] triangles = new int[]
            {
                0, 1, 2,
                3, 2, 1,
                3, 4, 5,
                3, 8, 4,
                0, 6, 7,
                0, 9, 6,
                4, 10, 11,
                6, 11, 10,
                2, 5, 9,
                11, 9, 5,
                1, 7, 8,
                10, 8, 7,
                3, 5, 2,
                3, 1, 8,
                0, 2, 9,
                0, 7, 1,
                6, 9, 11,
                6, 10, 7,
                4, 11, 5,
                4, 8, 10
            };

            mesh.vertices = vertices;
            mesh.triangles = triangles;
            mesh.RecalculateNormals();

            return mesh;
        }
    }
}
```

---

## 6. Backend WebSocket API

Add to `api/main.py`:

```python
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json

# Active WebSocket connections
active_connections: Dict[str, Set[WebSocket]] = {}

@app.websocket("/ws/swarm/{swarm_id}")
async def swarm_websocket(websocket: WebSocket, swarm_id: str):
    """
    Real-time swarm state feed for Unity visualization.

    Sends updates at 10 Hz with:
    - Agent positions (6D)
    - Trust scores and vectors
    - Contact graph edges
    - Circuit status
    """
    await websocket.accept()

    if swarm_id not in active_connections:
        active_connections[swarm_id] = set()
    active_connections[swarm_id].add(websocket)

    try:
        while True:
            # Get current swarm state
            state = await get_swarm_state(swarm_id)

            # Send to client
            await websocket.send_json(state)

            # 10 Hz update rate
            await asyncio.sleep(0.1)

    except WebSocketDisconnect:
        active_connections[swarm_id].discard(websocket)


async def get_swarm_state(swarm_id: str) -> dict:
    """Get current state of swarm for visualization."""
    # This would connect to your actual swarm coordinator
    # For now, return mock data structure

    return {
        "swarmId": swarm_id,
        "timestamp": int(time.time() * 1000),
        "agents": [
            {
                "id": f"agent_{i}",
                "position": [
                    random.uniform(-10, 10),  # x
                    random.uniform(-10, 10),  # y
                    random.uniform(-10, 10),  # z
                    random.uniform(0, 5),     # v (velocity)
                    random.uniform(-1, 1),    # h (harmony)
                    random.uniform(0, 255),   # s (security)
                ],
                "trustScore": random.uniform(0.3, 1.0),
                "trustLevel": random.choice(["HIGH", "MEDIUM", "LOW"]),
                "trustVector": [random.uniform(0, 1) for _ in range(6)],
                "dimensionalState": random.choice(["POLLY", "QUASI", "DEMI"]),
                "nu": random.uniform(0.5, 1.0),
            }
            for i in range(10)
        ],
        "edges": [
            {
                "source": f"agent_{i}",
                "target": f"agent_{(i+1) % 10}",
                "latency": random.uniform(10, 200),
                "capacity": random.uniform(100000, 1000000),
                "confidence": random.uniform(0.7, 1.0),
            }
            for i in range(10)
        ],
        "coherenceScore": random.uniform(0.6, 0.95),
    }
```

---

## 7. Development Roadmap

### Week 1-2: Core Infrastructure
- [ ] Unity project setup with required packages
- [ ] WebSocket client implementation
- [ ] Data model classes
- [ ] Basic agent spawning and positioning

### Week 3-4: Swarm Visualization
- [ ] 6D → 3D projection system
- [ ] Trust-based material swapping
- [ ] Connection line rendering
- [ ] Smooth position interpolation
- [ ] Agent selection and inspection UI

### Week 5-6: Advanced Features
- [ ] PHDM polyhedron mesh generation
- [ ] Force-directed contact graph layout
- [ ] Trust heatmap shader
- [ ] Circuit path animation
- [ ] Timeline recording and playback

### Week 7-8: Polish & Deployment
- [ ] Performance optimization (1000+ agents)
- [ ] VR mode (optional)
- [ ] WebGL build for browser embedding
- [ ] Documentation and tutorials

---

## 8. Alternative: Web-Based Dashboard

If Unity is too heavyweight, consider a web-based alternative:

```
dashboard-web/
├── src/
│   ├── components/
│   │   ├── SwarmCanvas.tsx      # Three.js canvas
│   │   ├── TrustHeatmap.tsx     # D3.js heatmap
│   │   ├── ContactGraph.tsx     # Force-directed graph
│   │   └── MetricsPanel.tsx     # Real-time stats
│   ├── hooks/
│   │   └── useWebSocket.ts      # Live data connection
│   └── shaders/
│       └── hyperbolic.glsl      # Poincaré ball shader
```

**Pros:**
- Faster development (2-3 weeks vs 4-6)
- No installation required
- Easier to embed in existing tools

**Cons:**
- Less performant for 1000+ agents
- No VR support
- Limited shader capabilities

---

## 9. Conclusion

The Unity visualization will provide an immersive, professional-grade monitoring interface for the Spiralverse system. Key deliverables:

1. **Real-time 3D swarm view** with 6D → 3D projection
2. **Trust-based coloring** using Six Sacred Tongues palette
3. **Contact graph exploration** with force-directed layout
4. **PHDM polyhedra** visualization in hyperbolic space
5. **Timeline playback** for debugging and analysis

**Recommended Path:**
Start with Unity for the full experience, but build the WebSocket API first so a web-based fallback remains possible.

---

*Document prepared for SCBE-AETHERMOORE v3.0*
*Visualization System Design - January 2026*
