import React, { useRef, useEffect, useState, useCallback } from 'react';
import { GitGraph, Plus, Trash2, Play, Pause, RotateCcw, Zap, Anchor } from 'lucide-react';

// ═══════════════════════════════════════════════════════════════
//  PHYSICS ENGINE — Rubber Ducky Spring System
// ═══════════════════════════════════════════════════════════════

interface GraphNode {
  id: string;
  label: string;
  x: number;
  y: number; // current position
  vx: number;
  vy: number; // velocity
  ox: number;
  oy: number; // rest (original) position
  mass: number;
  radius: number;
  color: string;
  glow: number; // pulse effect
  pinned: boolean; // stays fixed
}

interface GraphEdge {
  from: string;
  to: string;
  label: string;
  strength: number; // spring constant
  restLength: number;
  color: string;
}

interface PhysicsConfig {
  springK: number; // spring stiffness
  damping: number; // velocity decay (0-1)
  repulsion: number; // node-node repulsion
  returnForce: number; // how strongly nodes return to rest position
  maxSpeed: number;
  dt: number; // timestep
}

const DEFAULT_CONFIG: PhysicsConfig = {
  springK: 0.08,
  damping: 0.92,
  repulsion: 800,
  returnForce: 0.03,
  maxSpeed: 15,
  dt: 1,
};

// Color palette for nodes
const NODE_COLORS = [
  '#3b82f6',
  '#8b5cf6',
  '#06b6d4',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#ec4899',
  '#6366f1',
  '#14b8a6',
  '#f97316',
  '#84cc16',
  '#a855f7',
];

function hexToRgba(hex: string, a: number) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${a})`;
}

// ═══════════════════════════════════════════════════════════════
//  PRESET GRAPHS
// ═══════════════════════════════════════════════════════════════

function buildMobiusGraph(
  centerX: number,
  centerY: number
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  // Dirichlet convolution ring: 1 → μ → Λ (the prime extraction pipeline)
  const nodes: GraphNode[] = [
    {
      id: 'identity',
      label: '𝟙(n)=1',
      x: centerX - 200,
      y: centerY,
      vx: 0,
      vy: 0,
      ox: centerX - 200,
      oy: centerY,
      mass: 2,
      radius: 35,
      color: NODE_COLORS[0],
      glow: 0,
      pinned: false,
    },
    {
      id: 'mobius',
      label: 'μ(n)',
      x: centerX,
      y: centerY - 120,
      vx: 0,
      vy: 0,
      ox: centerX,
      oy: centerY - 120,
      mass: 2.5,
      radius: 38,
      color: NODE_COLORS[1],
      glow: 0,
      pinned: false,
    },
    {
      id: 'vonmangoldt',
      label: 'Λ(n)',
      x: centerX + 200,
      y: centerY,
      vx: 0,
      vy: 0,
      ox: centerX + 200,
      oy: centerY,
      mass: 2.5,
      radius: 38,
      color: NODE_COLORS[4],
      glow: 0,
      pinned: false,
    },
    {
      id: 'delta',
      label: 'δ(n)',
      x: centerX,
      y: centerY + 140,
      vx: 0,
      vy: 0,
      ox: centerX,
      oy: centerY + 140,
      mass: 1.5,
      radius: 30,
      color: NODE_COLORS[2],
      glow: 0,
      pinned: false,
    },
    {
      id: 'log',
      label: 'log(n)',
      x: centerX + 80,
      y: centerY - 180,
      vx: 0,
      vy: 0,
      ox: centerX + 80,
      oy: centerY - 180,
      mass: 1.5,
      radius: 30,
      color: NODE_COLORS[6],
      glow: 0,
      pinned: false,
    },
    {
      id: 'zeta',
      label: 'ζ(s)',
      x: centerX - 80,
      y: centerY - 180,
      vx: 0,
      vy: 0,
      ox: centerX - 80,
      oy: centerY - 180,
      mass: 1.5,
      radius: 30,
      color: NODE_COLORS[5],
      glow: 0,
      pinned: false,
    },
    {
      id: 'primes',
      label: 'Primes',
      x: centerX + 320,
      y: centerY - 60,
      vx: 0,
      vy: 0,
      ox: centerX + 320,
      oy: centerY - 60,
      mass: 2,
      radius: 33,
      color: NODE_COLORS[8],
      glow: 0,
      pinned: false,
    },
  ];
  const edges: GraphEdge[] = [
    {
      from: 'identity',
      to: 'mobius',
      label: '1 * μ = δ',
      strength: 0.12,
      restLength: 140,
      color: '#8b5cf6',
    },
    {
      from: 'mobius',
      to: 'vonmangoldt',
      label: 'μ * log = Λ',
      strength: 0.12,
      restLength: 140,
      color: '#f59e0b',
    },
    {
      from: 'identity',
      to: 'delta',
      label: 'inverse',
      strength: 0.08,
      restLength: 160,
      color: '#06b6d4',
    },
    {
      from: 'mobius',
      to: 'delta',
      label: 'Möbius inv',
      strength: 0.08,
      restLength: 160,
      color: '#ec4899',
    },
    {
      from: 'log',
      to: 'vonmangoldt',
      label: 'ruler',
      strength: 0.1,
      restLength: 120,
      color: '#10b981',
    },
    {
      from: 'zeta',
      to: 'identity',
      label: 'Σ1/nˢ',
      strength: 0.08,
      restLength: 130,
      color: '#ef4444',
    },
    {
      from: 'vonmangoldt',
      to: 'primes',
      label: 'indicates',
      strength: 0.1,
      restLength: 120,
      color: '#14b8a6',
    },
  ];
  return { nodes, edges };
}

function buildTrigGraph(
  centerX: number,
  centerY: number
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes: GraphNode[] = [
    {
      id: 'sin',
      label: 'sin(x)',
      x: centerX - 150,
      y: centerY - 100,
      vx: 0,
      vy: 0,
      ox: centerX - 150,
      oy: centerY - 100,
      mass: 1.5,
      radius: 30,
      color: NODE_COLORS[0],
      glow: 0,
      pinned: false,
    },
    {
      id: 'cos',
      label: 'cos(x)',
      x: centerX + 150,
      y: centerY - 100,
      vx: 0,
      vy: 0,
      ox: centerX + 150,
      oy: centerY - 100,
      mass: 1.5,
      radius: 30,
      color: NODE_COLORS[1],
      glow: 0,
      pinned: false,
    },
    {
      id: 'tan',
      label: 'tan(x)',
      x: centerX,
      y: centerY - 180,
      vx: 0,
      vy: 0,
      ox: centerX,
      oy: centerY - 180,
      mass: 1.5,
      radius: 30,
      color: NODE_COLORS[2],
      glow: 0,
      pinned: false,
    },
    {
      id: 'sec',
      label: 'sec(x)',
      x: centerX - 250,
      y: centerY,
      vx: 0,
      vy: 0,
      ox: centerX - 250,
      oy: centerY,
      mass: 1.5,
      radius: 30,
      color: NODE_COLORS[3],
      glow: 0,
      pinned: false,
    },
    {
      id: 'csc',
      label: 'csc(x)',
      x: centerX + 250,
      y: centerY,
      vx: 0,
      vy: 0,
      ox: centerX + 250,
      oy: centerY,
      mass: 1.5,
      radius: 30,
      color: NODE_COLORS[6],
      glow: 0,
      pinned: false,
    },
    {
      id: 'cot',
      label: 'cot(x)',
      x: centerX,
      y: centerY + 80,
      vx: 0,
      vy: 0,
      ox: centerX,
      oy: centerY + 80,
      mass: 1.5,
      radius: 30,
      color: NODE_COLORS[7],
      glow: 0,
      pinned: false,
    },
    {
      id: 'unit',
      label: 'unit circle',
      x: centerX,
      y: centerY,
      vx: 0,
      vy: 0,
      ox: centerX,
      oy: centerY,
      mass: 3,
      radius: 45,
      color: NODE_COLORS[4],
      glow: 0,
      pinned: false,
    },
    {
      id: 'pi',
      label: 'π',
      x: centerX,
      y: centerY + 160,
      vx: 0,
      vy: 0,
      ox: centerX,
      oy: centerY + 160,
      mass: 1,
      radius: 25,
      color: NODE_COLORS[5],
      glow: 0,
      pinned: false,
    },
  ];
  const edges: GraphEdge[] = [
    {
      from: 'sin',
      to: 'cos',
      label: 'sin²+cos²=1',
      strength: 0.1,
      restLength: 160,
      color: '#3b82f6',
    },
    {
      from: 'sin',
      to: 'tan',
      label: 'tan=sin/cos',
      strength: 0.1,
      restLength: 120,
      color: '#06b6d4',
    },
    { from: 'cos', to: 'tan', label: '', strength: 0.1, restLength: 120, color: '#06b6d4' },
    {
      from: 'sin',
      to: 'csc',
      label: 'csc=1/sin',
      strength: 0.08,
      restLength: 140,
      color: '#8b5cf6',
    },
    {
      from: 'cos',
      to: 'sec',
      label: 'sec=1/cos',
      strength: 0.08,
      restLength: 140,
      color: '#10b981',
    },
    {
      from: 'tan',
      to: 'cot',
      label: 'cot=1/tan',
      strength: 0.08,
      restLength: 140,
      color: '#f59e0b',
    },
    { from: 'unit', to: 'sin', label: 'y', strength: 0.12, restLength: 100, color: '#3b82f6' },
    { from: 'unit', to: 'cos', label: 'x', strength: 0.12, restLength: 100, color: '#8b5cf6' },
    { from: 'pi', to: 'unit', label: '2π rad', strength: 0.06, restLength: 120, color: '#ec4899' },
  ];
  return { nodes, edges };
}

function buildAlgebraGraph(
  centerX: number,
  centerY: number
): { nodes: GraphNode[]; edges: GraphEdge[] } {
  const nodes: GraphNode[] = [
    {
      id: 'a',
      label: 'a',
      x: centerX - 180,
      y: centerY - 80,
      vx: 0,
      vy: 0,
      ox: centerX - 180,
      oy: centerY - 80,
      mass: 1.5,
      radius: 28,
      color: NODE_COLORS[0],
      glow: 0,
      pinned: false,
    },
    {
      id: 'b',
      label: 'b',
      x: centerX + 180,
      y: centerY - 80,
      vx: 0,
      vy: 0,
      ox: centerX + 180,
      oy: centerY - 80,
      mass: 1.5,
      radius: 28,
      color: NODE_COLORS[1],
      glow: 0,
      pinned: false,
    },
    {
      id: 'c',
      label: 'c',
      x: centerX,
      y: centerY - 160,
      vx: 0,
      vy: 0,
      ox: centerX,
      oy: centerY - 160,
      mass: 1.5,
      radius: 28,
      color: NODE_COLORS[2],
      glow: 0,
      pinned: false,
    },
    {
      id: 'quad',
      label: 'ax²+bx+c',
      x: centerX,
      y: centerY,
      vx: 0,
      vy: 0,
      ox: centerX,
      oy: centerY,
      mass: 3,
      radius: 45,
      color: NODE_COLORS[4],
      glow: 0,
      pinned: false,
    },
    {
      id: 'disc',
      label: 'b²-4ac',
      x: centerX - 120,
      y: centerY + 120,
      vx: 0,
      vy: 0,
      ox: centerX - 120,
      oy: centerY + 120,
      mass: 2,
      radius: 35,
      color: NODE_COLORS[5],
      glow: 0,
      pinned: false,
    },
    {
      id: 'roots',
      label: '(-b±√D)/2a',
      x: centerX + 120,
      y: centerY + 120,
      vx: 0,
      vy: 0,
      ox: centerX + 120,
      oy: centerY + 120,
      mass: 2,
      radius: 38,
      color: NODE_COLORS[7],
      glow: 0,
      pinned: false,
    },
    {
      id: 'vertex',
      label: '-b/2a',
      x: centerX,
      y: centerY + 160,
      vx: 0,
      vy: 0,
      ox: centerX,
      oy: centerY + 160,
      mass: 1.5,
      radius: 30,
      color: NODE_COLORS[8],
      glow: 0,
      pinned: false,
    },
  ];
  const edges: GraphEdge[] = [
    { from: 'a', to: 'quad', label: '', strength: 0.1, restLength: 100, color: '#3b82f6' },
    { from: 'b', to: 'quad', label: '', strength: 0.1, restLength: 100, color: '#8b5cf6' },
    { from: 'c', to: 'quad', label: '', strength: 0.1, restLength: 100, color: '#06b6d4' },
    {
      from: 'quad',
      to: 'disc',
      label: 'discriminant',
      strength: 0.1,
      restLength: 120,
      color: '#ef4444',
    },
    { from: 'disc', to: 'roots', label: '√D', strength: 0.12, restLength: 120, color: '#f59e0b' },
    {
      from: 'quad',
      to: 'roots',
      label: 'formula',
      strength: 0.08,
      restLength: 140,
      color: '#10b981',
    },
    {
      from: 'quad',
      to: 'vertex',
      label: 'axis',
      strength: 0.08,
      restLength: 100,
      color: '#ec4899',
    },
  ];
  return { nodes, edges };
}

// ═══════════════════════════════════════════════════════════════
//  COMPONENT
// ═══════════════════════════════════════════════════════════════

export default function MathGraph() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const nodesRef = useRef<GraphNode[]>([]);
  const edgesRef = useRef<GraphEdge[]>([]);
  const configRef = useRef<PhysicsConfig>({ ...DEFAULT_CONFIG });
  const draggingRef = useRef<string | null>(null);
  const mouseRef = useRef({ x: 0, y: 0 });
  const animRef = useRef<number>(0);
  const [running, setRunning] = useState(true);
  const [preset, setPreset] = useState<'mobius' | 'trig' | 'algebra'>('mobius');
  const [showLabels, setShowLabels] = useState(true);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  const loadPreset = useCallback((p: 'mobius' | 'trig' | 'algebra') => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;
    let result: { nodes: GraphNode[]; edges: GraphEdge[] };
    switch (p) {
      case 'trig':
        result = buildTrigGraph(cx, cy);
        break;
      case 'algebra':
        result = buildAlgebraGraph(cx, cy);
        break;
      default:
        result = buildMobiusGraph(cx, cy);
    }
    nodesRef.current = result.nodes;
    edgesRef.current = result.edges;
    setPreset(p);
  }, []);

  // Init canvas size
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const resize = () => {
      const rect = container.getBoundingClientRect();
      canvas.width = rect.width;
      canvas.height = rect.height;
    };
    resize();
    loadPreset('mobius');
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, [loadPreset]);

  // Physics + Render loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;

    const step = () => {
      if (!running) {
        animRef.current = requestAnimationFrame(step);
        return;
      }

      const nodes = nodesRef.current;
      const edges = edgesRef.current;
      const cfg = configRef.current;
      const dragId = draggingRef.current;

      // Physics: spring forces + return-to-rest + repulsion + damping
      for (const n of nodes) {
        if (n.pinned || n.id === dragId) continue;

        let fx = 0,
          fy = 0;

        // Return to rest position (rubber duck spring back)
        fx += (n.ox - n.x) * cfg.returnForce * n.mass;
        fy += (n.oy - n.y) * cfg.returnForce * n.mass;

        // Node-node repulsion
        for (const other of nodes) {
          if (other.id === n.id) continue;
          const dx = n.x - other.x;
          const dy = n.y - other.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < 250) {
            const f = cfg.repulsion / (dist * dist);
            fx += (dx / dist) * f;
            fy += (dy / dist) * f;
          }
        }

        // Edge spring forces
        for (const e of edges) {
          const otherId = e.from === n.id ? e.to : e.to === n.id ? e.from : null;
          if (!otherId) continue;
          const other = nodes.find((nn) => nn.id === otherId);
          if (!other) continue;
          const dx = other.x - n.x;
          const dy = other.y - n.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const stretch = dist - e.restLength;
          const f = stretch * e.strength;
          fx += (dx / dist) * f;
          fy += (dy / dist) * f;
        }

        // Wall containment
        const margin = n.radius + 10;
        if (n.x < margin) fx += (margin - n.x) * 0.1;
        if (n.x > canvas.width - margin) fx += (canvas.width - margin - n.x) * 0.1;
        if (n.y < margin) fy += (margin - n.y) * 0.1;
        if (n.y > canvas.height - margin) fy += (canvas.height - margin - n.y) * 0.1;

        // Apply
        n.vx += (fx / n.mass) * cfg.dt;
        n.vy += (fy / n.mass) * cfg.dt;
        n.vx *= cfg.damping;
        n.vy *= cfg.damping;
        const speed = Math.sqrt(n.vx * n.vx + n.vy * n.vy);
        if (speed > cfg.maxSpeed) {
          n.vx = (n.vx / speed) * cfg.maxSpeed;
          n.vy = (n.vy / speed) * cfg.maxSpeed;
        }
        n.x += n.vx * cfg.dt;
        n.y += n.vy * cfg.dt;

        // Decay glow
        n.glow *= 0.95;
      }

      // Dragging: node follows mouse with soft spring
      if (dragId) {
        const n = nodes.find((nn) => nn.id === dragId);
        if (n) {
          n.vx = (mouseRef.current.x - n.x) * 0.2;
          n.vy = (mouseRef.current.y - n.y) * 0.2;
          n.x += n.vx;
          n.y += n.vy;
          n.glow = Math.min(n.glow + 0.05, 1);
        }
      }

      // ─── RENDER ───
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Background grid
      ctx.strokeStyle = 'rgba(59, 130, 246, 0.03)';
      ctx.lineWidth = 1;
      for (let gx = 0; gx < canvas.width; gx += 40) {
        ctx.beginPath();
        ctx.moveTo(gx, 0);
        ctx.lineTo(gx, canvas.height);
        ctx.stroke();
      }
      for (let gy = 0; gy < canvas.height; gy += 40) {
        ctx.beginPath();
        ctx.moveTo(0, gy);
        ctx.lineTo(canvas.width, gy);
        ctx.stroke();
      }

      // Edges (rubber bands that stretch)
      for (const e of edges) {
        const from = nodes.find((n) => n.id === e.from);
        const to = nodes.find((n) => n.id === e.to);
        if (!from || !to) continue;

        const dx = to.x - from.x;
        const dy = to.y - from.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const stretch = Math.abs(dist - e.restLength);
        const stretchRatio = stretch / e.restLength;

        // Color shifts from cool (relaxed) to warm (stretched)
        const r = Math.min(255, 100 + stretchRatio * 155);
        const g = Math.max(50, 200 - stretchRatio * 150);
        const b = Math.max(50, 255 - stretchRatio * 200);
        const alpha = 0.2 + Math.min(stretchRatio * 0.5, 0.5);

        ctx.strokeStyle = `rgba(${r},${g},${b},${alpha})`;
        ctx.lineWidth = 2 + stretchRatio * 2;
        ctx.lineCap = 'round';

        // Quadratic curve for rubber effect
        const midX = (from.x + to.x) / 2;
        const midY = (from.y + to.y) / 2;
        const perpX = (-dy / dist) * stretch * 0.1;
        const perpY = (dx / dist) * stretch * 0.1;

        ctx.beginPath();
        ctx.moveTo(from.x, from.y);
        ctx.quadraticCurveTo(midX + perpX, midY + perpY, to.x, to.y);
        ctx.stroke();

        // Edge label
        if (showLabels && e.label) {
          ctx.fillStyle = `rgba(${r},${g},${b},${0.5 + stretchRatio * 0.3})`;
          ctx.font = '10px monospace';
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(e.label, midX + perpX * 0.5, midY + perpY * 0.5 - 8);
        }

        // Stretch indicator dots
        if (stretchRatio > 0.3) {
          const dotCount = Math.min(Math.floor(stretchRatio * 5), 5);
          for (let d = 1; d <= dotCount; d++) {
            const t = d / (dotCount + 1);
            const bx = (1 - t) * (1 - t) * from.x + 2 * (1 - t) * t * (midX + perpX) + t * t * to.x;
            const by = (1 - t) * (1 - t) * from.y + 2 * (1 - t) * t * (midY + perpY) + t * t * to.y;
            ctx.fillStyle = `rgba(${r},${g},${b},${0.3})`;
            ctx.beginPath();
            ctx.arc(bx, by, 2 + stretchRatio, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }

      // Nodes
      for (const n of nodes) {
        // Glow when dragged or active
        if (n.glow > 0.01 || n.id === dragId) {
          const glowR = n.radius + 15 + n.glow * 10;
          const grad = ctx.createRadialGradient(n.x, n.y, n.radius, n.x, n.y, glowR);
          grad.addColorStop(0, hexToRgba(n.color, 0.3));
          grad.addColorStop(1, hexToRgba(n.color, 0));
          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(n.x, n.y, glowR, 0, Math.PI * 2);
          ctx.fill();
        }

        // Node body
        const nodeGrad = ctx.createRadialGradient(
          n.x - n.radius * 0.3,
          n.y - n.radius * 0.3,
          0,
          n.x,
          n.y,
          n.radius
        );
        nodeGrad.addColorStop(0, hexToRgba(n.color, 0.9));
        nodeGrad.addColorStop(1, hexToRgba(n.color, 0.4));
        ctx.fillStyle = nodeGrad;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fill();

        // Border
        ctx.strokeStyle = hexToRgba(n.color, 0.8);
        ctx.lineWidth = n.id === dragId ? 2.5 : 1.5;
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.stroke();

        // Pin indicator
        if (n.pinned) {
          ctx.fillStyle = '#f59e0b';
          ctx.beginPath();
          ctx.arc(n.x, n.y - n.radius - 5, 4, 0, Math.PI * 2);
          ctx.fill();
        }

        // Label
        ctx.fillStyle = '#e2e8f0';
        ctx.font = `${n.radius > 35 ? 'bold 13px' : '12px'} system-ui, sans-serif`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(n.label, n.x, n.y);
      }

      // Help text when idle
      if (!dragId && nodes.every((n) => Math.sqrt(n.vx * n.vx + n.vy * n.vy) < 0.1)) {
        ctx.fillStyle = 'rgba(148, 163, 184, 0.15)';
        ctx.font = '11px system-ui';
        ctx.textAlign = 'center';
        ctx.fillText(
          'Drag nodes to stretch — release to bounce back',
          canvas.width / 2,
          canvas.height - 20
        );
      }

      animRef.current = requestAnimationFrame(step);
    };

    animRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(animRef.current);
  }, [running, showLabels]);

  // Mouse / touch handlers
  const getPos = (e: React.MouseEvent | React.TouchEvent) => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const clientX = 'touches' in e ? e.touches[0]?.clientX || 0 : e.clientX;
    const clientY = 'touches' in e ? e.touches[0]?.clientY || 0 : e.clientY;
    return { x: clientX - rect.left, y: clientY - rect.top };
  };

  const handleDown = (e: React.MouseEvent | React.TouchEvent) => {
    const pos = getPos(e);
    mouseRef.current = pos;
    for (const n of nodesRef.current) {
      const dx = pos.x - n.x;
      const dy = pos.y - n.y;
      if (dx * dx + dy * dy < (n.radius + 8) * (n.radius + 8)) {
        draggingRef.current = n.id;
        n.glow = 1;
        setSelectedNode(n.id);
        return;
      }
    }
    setSelectedNode(null);
  };

  const handleMove = (e: React.MouseEvent | React.TouchEvent) => {
    const pos = getPos(e);
    mouseRef.current = pos;
  };

  const handleUp = () => {
    draggingRef.current = null;
  };

  const togglePin = (id: string) => {
    const n = nodesRef.current.find((nn) => nn.id === id);
    if (n) {
      n.pinned = !n.pinned;
      n.vx = 0;
      n.vy = 0;
    }
  };

  const resetPositions = () => {
    for (const n of nodesRef.current) {
      if (!n.pinned) {
        n.x = n.ox;
        n.y = n.oy;
        n.vx = 0;
        n.vy = 0;
        n.glow = 0.5;
      }
    }
  };

  const addNode = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const id = `node_${Date.now()}`;
    const angle = Math.random() * Math.PI * 2;
    const dist = 100 + Math.random() * 150;
    const x = canvas.width / 2 + Math.cos(angle) * dist;
    const y = canvas.height / 2 + Math.sin(angle) * dist;
    nodesRef.current.push({
      id,
      label: `x${nodesRef.current.length}`,
      x,
      y,
      vx: 0,
      vy: 0,
      ox: x,
      oy: y,
      mass: 1.5,
      radius: 30,
      color: NODE_COLORS[nodesRef.current.length % NODE_COLORS.length],
      glow: 1,
      pinned: false,
    });
  };

  const selectedNodeData = selectedNode
    ? nodesRef.current.find((n) => n.id === selectedNode)
    : null;
  const connectedEdges = selectedNode
    ? edgesRef.current.filter((e) => e.from === selectedNode || e.to === selectedNode)
    : [];

  return (
    <div className="w-full h-full flex flex-col bg-[#0d1926] text-blue-100/80">
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-blue-500/10">
        <GitGraph size={16} className="text-blue-400" />
        <h2 className="text-sm text-blue-200 font-semibold">Math Graph</h2>
        <div className="flex gap-1 ml-2">
          {(['mobius', 'trig', 'algebra'] as const).map((p) => (
            <button
              key={p}
              onClick={() => loadPreset(p)}
              className={`px-2 py-0.5 rounded-lg text-[10px] transition-colors ${preset === p ? 'bg-blue-500/20 text-blue-200' : 'text-blue-300/30 hover:text-blue-200/60'}`}
            >
              {p === 'mobius' ? 'ζ Primes' : p}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <button
          onClick={() => setShowLabels(!showLabels)}
          className={`px-2 py-0.5 rounded-lg text-[10px] transition-colors ${showLabels ? 'bg-blue-500/20 text-blue-200' : 'text-blue-300/30'}`}
        >
          labels
        </button>
        <button
          onClick={() => setRunning(!running)}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
        >
          {running ? <Pause size={12} /> : <Play size={12} />}
        </button>
        <button
          onClick={resetPositions}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
          title="Reset"
        >
          <RotateCcw size={12} />
        </button>
        <button
          onClick={addNode}
          className="p-1 rounded hover:bg-blue-500/20 text-blue-300/40 hover:text-blue-300 transition-colors"
          title="Add node"
        >
          <Plus size={12} />
        </button>
      </div>

      <div className="flex-1 flex min-h-0">
        {/* Canvas */}
        <div ref={containerRef} className="flex-1 relative">
          <canvas
            ref={canvasRef}
            className="w-full h-full cursor-grab active:cursor-grabbing"
            onMouseDown={handleDown}
            onMouseMove={handleMove}
            onMouseUp={handleUp}
            onMouseLeave={handleUp}
            onTouchStart={handleDown}
            onTouchMove={handleMove}
            onTouchEnd={handleUp}
          />
        </div>

        {/* Sidebar */}
        {selectedNodeData && (
          <div className="w-48 border-l border-blue-500/10 bg-[#0a1420] flex flex-col overflow-hidden">
            <div className="px-3 py-2 border-b border-blue-500/10">
              <div className="flex items-center gap-2">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ background: selectedNodeData.color }}
                />
                <span className="text-xs text-blue-200 font-semibold">
                  {selectedNodeData.label}
                </span>
              </div>
            </div>
            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              <div className="text-[10px] text-blue-400/30 uppercase tracking-wider mb-1">
                Connections
              </div>
              {connectedEdges.map((e, i) => {
                const otherId = e.from === selectedNode ? e.to : e.from;
                const other = nodesRef.current.find((n) => n.id === otherId);
                return (
                  <div key={i} className="px-2 py-1 rounded bg-[#162032] text-[10px]">
                    <div className="flex items-center gap-1">
                      {other && (
                        <div className="w-2 h-2 rounded-full" style={{ background: other.color }} />
                      )}
                      <span className="text-blue-200/60">{other?.label || otherId}</span>
                    </div>
                    {e.label && <div className="text-blue-400/30 ml-3">{e.label}</div>}
                  </div>
                );
              })}
              {connectedEdges.length === 0 && (
                <div className="text-[10px] text-blue-400/20">No connections</div>
              )}
            </div>
            <div className="border-t border-blue-500/10 p-2 space-y-1">
              <button
                onClick={() => togglePin(selectedNode!)}
                className="w-full flex items-center gap-1.5 px-2 py-1 rounded bg-[#162032] hover:bg-blue-500/10 text-[10px] text-blue-300/50 hover:text-blue-200 transition-colors"
              >
                <Anchor size={10} />
                {selectedNodeData.pinned ? 'Unpin' : 'Pin'}
              </button>
              <button
                onClick={() => {
                  setSelectedNode(null);
                }}
                className="w-full flex items-center gap-1.5 px-2 py-1 rounded bg-[#162032] hover:bg-red-500/10 text-[10px] text-blue-300/50 hover:text-red-300 transition-colors"
              >
                <Trash2 size={10} /> Close
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Bottom bar */}
      <div className="flex items-center gap-3 px-3 py-1.5 border-t border-blue-500/10 text-[10px] text-blue-400/30">
        <Zap size={10} />
        <span>Spring physics active</span>
        <span className="text-blue-400/10">|</span>
        <span>{nodesRef.current.length} nodes</span>
        <span className="text-blue-400/10">|</span>
        <span>{edgesRef.current.length} edges</span>
        <div className="flex-1" />
        <span>Drag to stretch · Release to bounce</span>
      </div>
    </div>
  );
}
