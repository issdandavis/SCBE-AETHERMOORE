/**
 * @file TopologyCanvas.js
 * @module extension/components/TopologyCanvas
 *
 * Poincare disk topology renderer for the AetherBrowser sidepanel.
 * Renders web content as nodes in hyperbolic space instead of flat lists.
 *
 * "Mirrors are like browsers kinda" — Issac Davis
 * A flat browser flattens. A curved browser reveals topology.
 */

const DISK_PADDING = 16;
const NODE_RADIUS = 5;
const CENTER_RADIUS = 8;
const LABEL_FONT = '10px monospace';
const TITLE_FONT = 'bold 11px monospace';

const ZONE_COLORS = {
  GREEN: { fill: 'rgba(63, 185, 80, 0.08)', stroke: 'rgba(63, 185, 80, 0.3)', node: '#3fb950' },
  YELLOW: { fill: 'rgba(210, 153, 34, 0.06)', stroke: 'rgba(210, 153, 34, 0.25)', node: '#d29922' },
  RED: { fill: 'rgba(248, 81, 73, 0.05)', stroke: 'rgba(248, 81, 73, 0.2)', node: '#f85149' },
};

const CENTER_COLOR = '#58a6ff';
const BG_COLOR = '#0d1117';
const GRID_COLOR = 'rgba(139, 148, 158, 0.08)';
const TEXT_COLOR = '#e6edf3';
const MUTED_COLOR = '#8b949e';

let _canvas = null;
let _ctx = null;
let _topology = null;
let _hoveredNode = null;
let _diskRadius = 0;
let _centerX = 0;
let _centerY = 0;
let _onNodeClick = null;
let _tooltipEl = null;

function diskToPixel(x, y) {
  return [
    _centerX + x * _diskRadius,
    _centerY - y * _diskRadius, // flip y for canvas coords
  ];
}

function pixelToDisk(px, py) {
  return [
    (px - _centerX) / _diskRadius,
    -((py - _centerY) / _diskRadius),
  ];
}

function drawBackground() {
  const ctx = _ctx;
  const r = _diskRadius;

  // Dark background
  ctx.fillStyle = BG_COLOR;
  ctx.fillRect(0, 0, _canvas.width, _canvas.height);

  // Cost gradient (radial, darker toward edges)
  if (_topology && _topology.langues_cost) {
    const gradient = ctx.createRadialGradient(_centerX, _centerY, 0, _centerX, _centerY, r);
    const stops = _topology.langues_cost;
    const maxCost = Math.max(...stops.map(s => s.cost), 1);

    for (const stop of stops) {
      const opacity = Math.min(0.15, (stop.cost / maxCost) * 0.15);
      gradient.addColorStop(stop.radius, `rgba(248, 81, 73, ${opacity})`);
    }
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(_centerX, _centerY, r, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawZoneRings() {
  const ctx = _ctx;
  if (!_topology || !_topology.zone_rings) return;

  for (const ring of _topology.zone_rings) {
    const innerR = ring.inner_radius * _diskRadius;
    const outerR = ring.outer_radius * _diskRadius;
    const colors = ZONE_COLORS[ring.zone] || ZONE_COLORS.RED;

    // Fill zone
    ctx.beginPath();
    ctx.arc(_centerX, _centerY, outerR, 0, Math.PI * 2);
    if (innerR > 0) {
      ctx.arc(_centerX, _centerY, innerR, 0, Math.PI * 2, true);
    }
    ctx.fillStyle = colors.fill;
    ctx.fill();

    // Zone boundary
    ctx.beginPath();
    ctx.arc(_centerX, _centerY, outerR, 0, Math.PI * 2);
    ctx.strokeStyle = colors.stroke;
    ctx.lineWidth = 1;
    ctx.stroke();
  }

  // Outer boundary (the Poincare disk edge)
  ctx.beginPath();
  ctx.arc(_centerX, _centerY, _diskRadius, 0, Math.PI * 2);
  ctx.strokeStyle = 'rgba(139, 148, 158, 0.3)';
  ctx.lineWidth = 1.5;
  ctx.stroke();
}

function drawGridLines() {
  const ctx = _ctx;
  const r = _diskRadius;

  // Draw 4 diameter geodesics (through origin = straight lines in Poincare disk)
  ctx.strokeStyle = GRID_COLOR;
  ctx.lineWidth = 0.5;

  for (let i = 0; i < 4; i++) {
    const angle = (Math.PI * i) / 4;
    const x1 = _centerX + r * Math.cos(angle);
    const y1 = _centerY + r * Math.sin(angle);
    const x2 = _centerX - r * Math.cos(angle);
    const y2 = _centerY - r * Math.sin(angle);

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }

  // Concentric reference circles at 0.25, 0.5, 0.75
  for (const frac of [0.25, 0.5, 0.75]) {
    ctx.beginPath();
    ctx.arc(_centerX, _centerY, frac * r, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function drawNodes() {
  const ctx = _ctx;
  if (!_topology) return;

  // Draw connecting lines from center to each node
  for (const node of _topology.nodes) {
    const [px, py] = diskToPixel(node.x, node.y);
    const colors = ZONE_COLORS[node.zone] || ZONE_COLORS.RED;

    ctx.beginPath();
    ctx.moveTo(_centerX, _centerY);
    ctx.lineTo(px, py);
    ctx.strokeStyle = `${colors.stroke}`;
    ctx.lineWidth = 0.5;
    ctx.stroke();
  }

  // Draw node circles
  for (const node of _topology.nodes) {
    const [px, py] = diskToPixel(node.x, node.y);
    const colors = ZONE_COLORS[node.zone] || ZONE_COLORS.RED;
    const isHovered = _hoveredNode && _hoveredNode.id === node.id;
    const r = isHovered ? NODE_RADIUS + 3 : NODE_RADIUS;

    // Node circle
    ctx.beginPath();
    ctx.arc(px, py, r, 0, Math.PI * 2);
    ctx.fillStyle = colors.node;
    ctx.globalAlpha = isHovered ? 1.0 : 0.7;
    ctx.fill();
    ctx.globalAlpha = 1.0;

    // Label (only if not too crowded)
    if (isHovered || _topology.nodes.length < 20) {
      ctx.font = LABEL_FONT;
      ctx.fillStyle = isHovered ? TEXT_COLOR : MUTED_COLOR;
      ctx.textAlign = 'left';
      ctx.fillText(node.label, px + r + 4, py + 3);
    }
  }

  // Draw center node (on top)
  if (_topology.center) {
    ctx.beginPath();
    ctx.arc(_centerX, _centerY, CENTER_RADIUS, 0, Math.PI * 2);
    ctx.fillStyle = CENTER_COLOR;
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Center label
    ctx.font = TITLE_FONT;
    ctx.fillStyle = TEXT_COLOR;
    ctx.textAlign = 'center';
    ctx.fillText(_topology.center.label, _centerX, _centerY + CENTER_RADIUS + 14);
  }
}

function drawTrustCone(mouseX, mouseY) {
  if (!mouseX || !mouseY) return;
  const ctx = _ctx;

  const [mx, my] = pixelToDisk(mouseX, mouseY);
  const dist = Math.sqrt(mx * mx + my * my);

  if (dist > 1.0) return;

  // Trust cone angle: narrow near boundary, wide near center
  // theta = theta_base / max(confidence, 0.1)
  // confidence increases with distance from center (more specific = more confident)
  const confidence = Math.max(0.1, dist);
  const halfAngle = Math.min(Math.PI / 3, (Math.PI / 6) / confidence);

  const angle = Math.atan2(-my, mx); // flip y back
  const startAngle = -(angle - halfAngle);
  const endAngle = -(angle + halfAngle);

  ctx.beginPath();
  ctx.moveTo(_centerX, _centerY);
  ctx.arc(_centerX, _centerY, _diskRadius, startAngle, endAngle, true);
  ctx.closePath();
  ctx.fillStyle = 'rgba(88, 166, 255, 0.06)';
  ctx.fill();
  ctx.strokeStyle = 'rgba(88, 166, 255, 0.15)';
  ctx.lineWidth = 1;
  ctx.stroke();
}

function drawStats() {
  const ctx = _ctx;
  if (!_topology) return;

  ctx.font = '9px monospace';
  ctx.fillStyle = MUTED_COLOR;
  ctx.textAlign = 'left';
  ctx.fillText(`${_topology.node_count} links`, 8, _canvas.height - 8);

  const greenCount = _topology.nodes.filter(n => n.zone === 'GREEN').length;
  const yellowCount = _topology.nodes.filter(n => n.zone === 'YELLOW').length;
  const redCount = _topology.nodes.filter(n => n.zone === 'RED').length;

  ctx.textAlign = 'right';
  ctx.fillText(`G:${greenCount} Y:${yellowCount} R:${redCount}`, _canvas.width - 8, _canvas.height - 8);
}

function render(mouseX, mouseY) {
  if (!_ctx || !_topology) return;

  _ctx.clearRect(0, 0, _canvas.width, _canvas.height);
  drawBackground();
  drawZoneRings();
  drawGridLines();
  drawTrustCone(mouseX, mouseY);
  drawNodes();
  drawStats();
}

function hitTest(px, py) {
  if (!_topology) return null;

  for (const node of _topology.nodes) {
    const [nx, ny] = diskToPixel(node.x, node.y);
    const dx = px - nx;
    const dy = py - ny;
    if (dx * dx + dy * dy < 144) { // 12px radius
      return node;
    }
  }
  return null;
}

function showTooltip(node, x, y) {
  if (!_tooltipEl) return;

  const zoneColors = { GREEN: '#3fb950', YELLOW: '#d29922', RED: '#f85149' };
  const zoneColor = zoneColors[node.zone] || '#8b949e';

  _tooltipEl.innerHTML = `
    <div style="font-weight:700;margin-bottom:4px">${escapeHtml(node.label)}</div>
    <div style="color:#8b949e;font-size:10px;margin-bottom:4px">${escapeHtml(node.url.slice(0, 50))}</div>
    <div><span style="color:${zoneColor};font-weight:700">${node.zone}</span> zone | Risk: ${node.risk_tier}</div>
    <div>Distance: ${node.semantic_dist.toFixed(3)} | r=${node.radius.toFixed(3)}</div>
    ${node.topics.length ? `<div style="color:#8b949e;margin-top:2px">Topics: ${node.topics.join(', ')}</div>` : ''}
  `;

  const rect = _canvas.getBoundingClientRect();
  _tooltipEl.style.left = `${Math.min(x + 12, rect.width - 180)}px`;
  _tooltipEl.style.top = `${Math.max(y - 60, 4)}px`;
  _tooltipEl.classList.remove('hidden');
}

function hideTooltip() {
  if (_tooltipEl) {
    _tooltipEl.classList.add('hidden');
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function renderTopologyCanvas(container, topologyData, opts = {}) {
  _topology = topologyData;
  _onNodeClick = opts.onNodeClick || null;

  if (!_canvas) {
    _canvas = document.createElement('canvas');
    _canvas.style.borderRadius = '8px';
    _canvas.style.cursor = 'crosshair';
    container.appendChild(_canvas);

    _tooltipEl = document.createElement('div');
    _tooltipEl.className = 'ab-topology-tooltip hidden';
    container.appendChild(_tooltipEl);

    // Events
    _canvas.addEventListener('mousemove', (e) => {
      const rect = _canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      const node = hitTest(mx, my);
      _hoveredNode = node;

      if (node) {
        showTooltip(node, mx, my);
        _canvas.style.cursor = 'pointer';
      } else {
        hideTooltip();
        _canvas.style.cursor = 'crosshair';
      }

      render(mx, my);
    });

    _canvas.addEventListener('mouseleave', () => {
      _hoveredNode = null;
      hideTooltip();
      render();
    });

    _canvas.addEventListener('click', (e) => {
      const rect = _canvas.getBoundingClientRect();
      const node = hitTest(e.clientX - rect.left, e.clientY - rect.top);
      if (node && _onNodeClick) {
        _onNodeClick(node);
      }
    });
  }

  // Size canvas to container
  const width = Math.min(container.clientWidth || 380, 400);
  const height = width; // square
  const dpr = window.devicePixelRatio || 1;

  _canvas.width = width * dpr;
  _canvas.height = height * dpr;
  _canvas.style.width = `${width}px`;
  _canvas.style.height = `${height}px`;

  _ctx = _canvas.getContext('2d');
  _ctx.scale(dpr, dpr);

  _diskRadius = (width / 2) - DISK_PADDING;
  _centerX = width / 2;
  _centerY = height / 2;

  render();
}

export function updateTopology(topologyData) {
  _topology = topologyData;
  if (_ctx) render();
}

export function destroyTopologyCanvas(container) {
  if (_canvas && _canvas.parentNode === container) {
    container.removeChild(_canvas);
  }
  if (_tooltipEl && _tooltipEl.parentNode === container) {
    container.removeChild(_tooltipEl);
  }
  _canvas = null;
  _ctx = null;
  _topology = null;
  _tooltipEl = null;
}
