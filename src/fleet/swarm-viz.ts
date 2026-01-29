/**
 * Swarm Visualization Utilities
 * =============================
 *
 * Generates visualization data for swarm formations.
 * Outputs can be used with various rendering backends:
 * - SVG (browser)
 * - ASCII (terminal)
 * - JSON (API/WebSocket)
 * - Matplotlib-compatible Python code
 *
 * @module fleet/swarm-viz
 * @version 1.0.0
 * @since 2026-01-29
 */

import {
  Position3D,
  AgentPosition,
  FormationState,
  euclideanDistance,
  hyperbolicDistance,
  calculateCenter,
} from './formations';
import { TongueID } from '../spiralverse/types';
import { QuarantineState } from './byzantine';

/**
 * Color palette for Sacred Tongues
 */
export const TONGUE_COLORS: Record<TongueID, string> = {
  ko: '#FF6B6B', // Red - Control
  av: '#FFA94D', // Orange - I/O
  ru: '#FFE066', // Yellow - Policy
  ca: '#51CF66', // Green - Logic
  um: '#339AF0', // Blue - Security
  dr: '#CC5DE8', // Purple - Types
};

/**
 * Tongue display names
 */
export const TONGUE_NAMES: Record<TongueID, string> = {
  ko: "Kor'aelin",
  av: 'Avali',
  ru: 'Runethic',
  ca: 'Cassisivadan',
  um: 'Umbroth',
  dr: 'Draumric',
};

/**
 * ASCII characters for tongues
 */
export const TONGUE_ASCII: Record<TongueID, string> = {
  ko: 'K',
  av: 'A',
  ru: 'R',
  ca: 'C',
  um: 'U',
  dr: 'D',
};

/**
 * 2D projection of 3D position (for flat displays)
 */
export interface Position2D {
  x: number;
  y: number;
}

/**
 * Visualization node
 */
export interface VizNode {
  id: string;
  tongue: TongueID;
  position2D: Position2D;
  position3D: Position3D;
  radius: number;
  color: string;
  label: string;
  /** Is quarantined */
  quarantined: boolean;
  /** Opacity (0-1) */
  opacity: number;
}

/**
 * Visualization edge (connection between agents)
 */
export interface VizEdge {
  source: string;
  target: string;
  distance: number;
  /** Edge weight for rendering */
  weight: number;
  /** Is this a critical connection */
  critical: boolean;
}

/**
 * Complete visualization data
 */
export interface VizData {
  nodes: VizNode[];
  edges: VizEdge[];
  center: Position2D;
  bounds: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
  };
  metrics: {
    coherence: number;
    spread: number;
    minDistance: number;
    agentCount: number;
    quarantinedCount: number;
  };
  timestamp: number;
}

/**
 * SVG render options
 */
export interface SVGOptions {
  width: number;
  height: number;
  padding: number;
  nodeRadius: number;
  showLabels: boolean;
  showEdges: boolean;
  showBoundary: boolean;
  edgeThreshold: number;
}

/**
 * Default SVG options
 */
export const DEFAULT_SVG_OPTIONS: SVGOptions = {
  width: 600,
  height: 600,
  padding: 50,
  nodeRadius: 20,
  showLabels: true,
  showEdges: true,
  showBoundary: true,
  edgeThreshold: 0.5,
};

/**
 * Project 3D to 2D (orthographic XY projection)
 */
export function projectTo2D(pos: Position3D): Position2D {
  return { x: pos[0], y: pos[1] };
}

/**
 * Project 3D to 2D (perspective projection)
 */
export function projectTo2DPerspective(
  pos: Position3D,
  cameraZ: number = 2.0
): Position2D {
  const scale = cameraZ / (cameraZ - pos[2]);
  return {
    x: pos[0] * scale,
    y: pos[1] * scale,
  };
}

/**
 * Generate visualization data from formation state
 */
export function generateVizData(
  formation: FormationState,
  quarantined: QuarantineState[] = [],
  edgeThreshold: number = 0.5
): VizData {
  const quarantinedIds = new Set(quarantined.map((q) => q.agentId));

  // Generate nodes
  const nodes: VizNode[] = formation.positions.map((pos) => {
    const pos2D = projectTo2D(pos.position);
    const isQuarantined = quarantinedIds.has(pos.agentId);

    return {
      id: pos.agentId,
      tongue: pos.tongue,
      position2D: pos2D,
      position3D: pos.position,
      radius: pos.radius,
      color: TONGUE_COLORS[pos.tongue],
      label: `${TONGUE_ASCII[pos.tongue]}${pos.agentId.slice(-4)}`,
      quarantined: isQuarantined,
      opacity: isQuarantined ? 0.4 : 1.0,
    };
  });

  // Generate edges (connections below threshold distance)
  const edges: VizEdge[] = [];
  for (let i = 0; i < formation.positions.length; i++) {
    for (let j = i + 1; j < formation.positions.length; j++) {
      const posA = formation.positions[i].position;
      const posB = formation.positions[j].position;
      const dist = euclideanDistance(posA, posB);

      if (dist < edgeThreshold) {
        edges.push({
          source: formation.positions[i].agentId,
          target: formation.positions[j].agentId,
          distance: dist,
          weight: 1 - dist / edgeThreshold,
          critical: dist < edgeThreshold / 2,
        });
      }
    }
  }

  // Calculate bounds
  const xs = nodes.map((n) => n.position2D.x);
  const ys = nodes.map((n) => n.position2D.y);

  const center2D = projectTo2D(
    calculateCenter(formation.positions.map((p) => p.position))
  );

  return {
    nodes,
    edges,
    center: center2D,
    bounds: {
      minX: Math.min(...xs),
      maxX: Math.max(...xs),
      minY: Math.min(...ys),
      maxY: Math.max(...ys),
    },
    metrics: {
      coherence: formation.metrics.coherence,
      spread: formation.metrics.spread,
      minDistance: formation.metrics.minDistance,
      agentCount: nodes.length,
      quarantinedCount: quarantined.length,
    },
    timestamp: Date.now(),
  };
}

/**
 * Generate SVG visualization
 */
export function generateSVG(vizData: VizData, options: SVGOptions = DEFAULT_SVG_OPTIONS): string {
  const { width, height, padding, nodeRadius, showLabels, showEdges, showBoundary } = options;

  // Scale coordinates to fit canvas
  const scaleX = (width - 2 * padding) / 2;
  const scaleY = (height - 2 * padding) / 2;
  const centerX = width / 2;
  const centerY = height / 2;

  const toCanvasX = (x: number) => centerX + x * scaleX;
  const toCanvasY = (y: number) => centerY - y * scaleY; // Flip Y

  let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}">`;

  // Background
  svg += `<rect width="${width}" height="${height}" fill="#1a1a2e"/>`;

  // Poincaré ball boundary
  if (showBoundary) {
    svg += `<circle cx="${centerX}" cy="${centerY}" r="${scaleX}" fill="none" stroke="#333" stroke-width="2" stroke-dasharray="5,5"/>`;
    svg += `<circle cx="${centerX}" cy="${centerY}" r="${scaleX * 0.87}" fill="none" stroke="#444" stroke-width="1" stroke-dasharray="2,2"/>`;
  }

  // Edges
  if (showEdges) {
    for (const edge of vizData.edges) {
      const sourceNode = vizData.nodes.find((n) => n.id === edge.source);
      const targetNode = vizData.nodes.find((n) => n.id === edge.target);
      if (!sourceNode || !targetNode) continue;

      const x1 = toCanvasX(sourceNode.position2D.x);
      const y1 = toCanvasY(sourceNode.position2D.y);
      const x2 = toCanvasX(targetNode.position2D.x);
      const y2 = toCanvasY(targetNode.position2D.y);

      const strokeColor = edge.critical ? '#ff6b6b' : '#555';
      const strokeWidth = edge.critical ? 2 : 1;
      const opacity = edge.weight * 0.5 + 0.2;

      svg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${strokeColor}" stroke-width="${strokeWidth}" opacity="${opacity}"/>`;
    }
  }

  // Nodes
  for (const node of vizData.nodes) {
    const cx = toCanvasX(node.position2D.x);
    const cy = toCanvasY(node.position2D.y);

    // Node circle
    const strokeColor = node.quarantined ? '#ff0000' : '#fff';
    const strokeWidth = node.quarantined ? 3 : 1;

    svg += `<circle cx="${cx}" cy="${cy}" r="${nodeRadius}" fill="${node.color}" stroke="${strokeColor}" stroke-width="${strokeWidth}" opacity="${node.opacity}"/>`;

    // Label
    if (showLabels) {
      svg += `<text x="${cx}" y="${cy + 5}" text-anchor="middle" fill="#fff" font-size="12" font-family="monospace">${TONGUE_ASCII[node.tongue]}</text>`;
    }
  }

  // Metrics display
  svg += `<text x="10" y="20" fill="#888" font-size="12" font-family="monospace">Coherence: ${vizData.metrics.coherence.toFixed(2)}</text>`;
  svg += `<text x="10" y="35" fill="#888" font-size="12" font-family="monospace">Agents: ${vizData.metrics.agentCount} (Q: ${vizData.metrics.quarantinedCount})</text>`;

  svg += '</svg>';
  return svg;
}

/**
 * Generate ASCII visualization for terminal
 */
export function generateASCII(vizData: VizData, width: number = 60, height: number = 30): string {
  const grid: string[][] = [];

  // Initialize grid with spaces
  for (let y = 0; y < height; y++) {
    grid[y] = [];
    for (let x = 0; x < width; x++) {
      grid[y][x] = ' ';
    }
  }

  // Scale coordinates
  const scaleX = (width - 2) / 2;
  const scaleY = (height - 2) / 2;
  const centerX = Math.floor(width / 2);
  const centerY = Math.floor(height / 2);

  const toGridX = (x: number) => Math.round(centerX + x * scaleX);
  const toGridY = (y: number) => Math.round(centerY - y * scaleY);

  // Draw boundary (approximate circle)
  for (let angle = 0; angle < 2 * Math.PI; angle += 0.1) {
    const x = toGridX(Math.cos(angle) * 0.95);
    const y = toGridY(Math.sin(angle) * 0.95);
    if (x >= 0 && x < width && y >= 0 && y < height) {
      grid[y][x] = '.';
    }
  }

  // Draw center
  grid[centerY][centerX] = '+';

  // Draw edges
  for (const edge of vizData.edges) {
    const sourceNode = vizData.nodes.find((n) => n.id === edge.source);
    const targetNode = vizData.nodes.find((n) => n.id === edge.target);
    if (!sourceNode || !targetNode) continue;

    const x1 = toGridX(sourceNode.position2D.x);
    const y1 = toGridY(sourceNode.position2D.y);
    const x2 = toGridX(targetNode.position2D.x);
    const y2 = toGridY(targetNode.position2D.y);

    // Bresenham's line (simplified)
    const dx = Math.abs(x2 - x1);
    const dy = Math.abs(y2 - y1);
    const sx = x1 < x2 ? 1 : -1;
    const sy = y1 < y2 ? 1 : -1;
    let err = dx - dy;

    let cx = x1;
    let cy = y1;
    while (cx !== x2 || cy !== y2) {
      if (cx >= 0 && cx < width && cy >= 0 && cy < height && grid[cy][cx] === ' ') {
        grid[cy][cx] = edge.critical ? '=' : '-';
      }
      const e2 = 2 * err;
      if (e2 > -dy) {
        err -= dy;
        cx += sx;
      }
      if (e2 < dx) {
        err += dx;
        cy += sy;
      }
    }
  }

  // Draw nodes (over edges)
  for (const node of vizData.nodes) {
    const x = toGridX(node.position2D.x);
    const y = toGridY(node.position2D.y);

    if (x >= 0 && x < width && y >= 0 && y < height) {
      const char = node.quarantined
        ? TONGUE_ASCII[node.tongue].toLowerCase()
        : TONGUE_ASCII[node.tongue];
      grid[y][x] = char;
    }
  }

  // Build output string
  const border = '┌' + '─'.repeat(width) + '┐';
  const footer = '└' + '─'.repeat(width) + '┘';

  let output = border + '\n';
  for (let y = 0; y < height; y++) {
    output += '│' + grid[y].join('') + '│\n';
  }
  output += footer + '\n';

  // Add legend
  output += '\nLegend: ';
  for (const tongue of ['ko', 'av', 'ru', 'ca', 'um', 'dr'] as TongueID[]) {
    output += `${TONGUE_ASCII[tongue]}=${TONGUE_NAMES[tongue].slice(0, 3)} `;
  }
  output += '\n';
  output += `Coherence: ${vizData.metrics.coherence.toFixed(2)} | Agents: ${vizData.metrics.agentCount}\n`;

  return output;
}

/**
 * Generate Python matplotlib code
 */
export function generateMatplotlibCode(vizData: VizData): string {
  const nodePositions = vizData.nodes
    .map((n) => `    ['${n.id}', ${n.position3D[0]}, ${n.position3D[1]}, ${n.position3D[2]}, '${n.color}', '${n.tongue}'],`)
    .join('\n');

  const edgeList = vizData.edges
    .map((e) => `    ('${e.source}', '${e.target}', ${e.distance.toFixed(4)}),`)
    .join('\n');

  return `"""
SCBE-AETHERMOORE Swarm Visualization
Generated: ${new Date().toISOString()}
Coherence: ${vizData.metrics.coherence.toFixed(2)}
Agents: ${vizData.metrics.agentCount}
"""

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

# Agent positions: [id, x, y, z, color, tongue]
agents = [
${nodePositions}
]

# Edges: (source, target, distance)
edges = [
${edgeList}
]

def plot_swarm():
    fig = plt.figure(figsize=(12, 12))
    ax = fig.add_subplot(111, projection='3d')

    # Plot Poincaré ball boundary (wireframe sphere)
    u = np.linspace(0, 2 * np.pi, 50)
    v = np.linspace(0, np.pi, 50)
    x_sphere = np.outer(np.cos(u), np.sin(v))
    y_sphere = np.outer(np.sin(u), np.sin(v))
    z_sphere = np.outer(np.ones(np.size(u)), np.cos(v))
    ax.plot_surface(x_sphere, y_sphere, z_sphere, alpha=0.1, color='gray')

    # Plot edges
    for source, target, dist in edges:
        source_agent = next((a for a in agents if a[0] == source), None)
        target_agent = next((a for a in agents if a[0] == target), None)
        if source_agent and target_agent:
            ax.plot(
                [source_agent[1], target_agent[1]],
                [source_agent[2], target_agent[2]],
                [source_agent[3], target_agent[3]],
                'k-', alpha=0.3
            )

    # Plot agents
    for agent_id, x, y, z, color, tongue in agents:
        ax.scatter(x, y, z, c=color, s=200, marker='o', edgecolors='white', linewidth=1)
        ax.text(x, y, z, f'  {tongue.upper()}', fontsize=10)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('SCBE-AETHERMOORE Swarm (Poincaré Ball)')
    ax.set_xlim(-1, 1)
    ax.set_ylim(-1, 1)
    ax.set_zlim(-1, 1)

    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    plot_swarm()
`;
}

/**
 * Generate JSON for API/WebSocket
 */
export function generateJSON(vizData: VizData): string {
  return JSON.stringify(vizData, null, 2);
}

/**
 * Generate Grafana-compatible metrics
 */
export interface GrafanaMetric {
  metric: string;
  value: number;
  timestamp: number;
  labels: Record<string, string>;
}

/**
 * Generate Grafana metrics from viz data
 */
export function generateGrafanaMetrics(vizData: VizData, swarmId: string): GrafanaMetric[] {
  const ts = vizData.timestamp;
  const metrics: GrafanaMetric[] = [];

  // Swarm-level metrics
  metrics.push({
    metric: 'scbe_swarm_coherence',
    value: vizData.metrics.coherence,
    timestamp: ts,
    labels: { swarm_id: swarmId },
  });

  metrics.push({
    metric: 'scbe_swarm_spread',
    value: vizData.metrics.spread,
    timestamp: ts,
    labels: { swarm_id: swarmId },
  });

  metrics.push({
    metric: 'scbe_swarm_agent_count',
    value: vizData.metrics.agentCount,
    timestamp: ts,
    labels: { swarm_id: swarmId },
  });

  metrics.push({
    metric: 'scbe_swarm_quarantined_count',
    value: vizData.metrics.quarantinedCount,
    timestamp: ts,
    labels: { swarm_id: swarmId },
  });

  // Per-agent metrics
  for (const node of vizData.nodes) {
    metrics.push({
      metric: 'scbe_agent_radius',
      value: node.radius,
      timestamp: ts,
      labels: { swarm_id: swarmId, agent_id: node.id, tongue: node.tongue },
    });

    metrics.push({
      metric: 'scbe_agent_quarantined',
      value: node.quarantined ? 1 : 0,
      timestamp: ts,
      labels: { swarm_id: swarmId, agent_id: node.id, tongue: node.tongue },
    });
  }

  return metrics;
}

/**
 * Generate distance matrix heatmap data
 */
export interface HeatmapData {
  labels: string[];
  values: number[][];
  min: number;
  max: number;
}

/**
 * Generate heatmap data for distance matrix
 */
export function generateDistanceHeatmap(
  positions: AgentPosition[],
  metric: 'euclidean' | 'hyperbolic' = 'euclidean'
): HeatmapData {
  const n = positions.length;
  const labels = positions.map((p) => `${TONGUE_ASCII[p.tongue]}${p.agentId.slice(-4)}`);
  const values: number[][] = [];

  let min = Infinity;
  let max = -Infinity;

  for (let i = 0; i < n; i++) {
    values[i] = [];
    for (let j = 0; j < n; j++) {
      if (i === j) {
        values[i][j] = 0;
      } else {
        const dist =
          metric === 'hyperbolic'
            ? hyperbolicDistance(positions[i].position, positions[j].position)
            : euclideanDistance(positions[i].position, positions[j].position);
        values[i][j] = dist;
        if (dist < min) min = dist;
        if (dist > max && dist < Infinity) max = dist;
      }
    }
  }

  return { labels, values, min, max };
}
