import { App } from "@modelcontextprotocol/ext-apps";
import { wavelengthToRgb, type LayoutResult, type Mode } from "./spectralGraph.js";

const flowCountInput = document.getElementById("flow-count") as HTMLInputElement;
const modeInput = document.getElementById("mode") as HTMLSelectElement;
const atUnixMsInput = document.getElementById("at-unix-ms") as HTMLInputElement;
const windowMsInput = document.getElementById("window-ms") as HTMLInputElement;
const regenBtn = document.getElementById("regen") as HTMLButtonElement;
const metricsEl = document.getElementById("metrics") as HTMLElement;
const collisionsEl = document.getElementById("collisions") as HTMLElement;
const voxelsEl = document.getElementById("voxels") as HTMLElement;
const canvas = document.getElementById("graph") as HTMLCanvasElement;
const ctx = canvas.getContext("2d");

if (!ctx) {
  throw new Error("Canvas rendering context is unavailable");
}

const app = new App({ name: "Cymatic Voxel Graph App", version: "0.1.0" });
app.connect();
atUnixMsInput.value = String(Date.now());

function draw(layout: LayoutResult): void {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const xFrom = (x: number) => (x + 1) * 0.5 * (canvas.width - 120) + 60;
  const yFrom = (y: number) => (1 - (y + 1) * 0.5) * (canvas.height - 80) + 40;

  ctx.strokeStyle = "rgba(120,170,210,0.25)";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(canvas.width / 2, canvas.height / 2, 170, 0, Math.PI * 2);
  ctx.stroke();

  for (const edge of layout.edges) {
    const a = layout.nodes.find((n) => n.id === edge.from);
    const b = layout.nodes.find((n) => n.id === edge.to);
    if (!a || !b) continue;
    ctx.strokeStyle = "rgba(120,170,210,0.25)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(xFrom(a.x), yFrom(a.y));
    ctx.lineTo(xFrom(b.x), yFrom(b.y));
    ctx.stroke();
  }

  for (const flow of layout.flows) {
    const rgb = wavelengthToRgb(flow.wavelengthNm);
    ctx.strokeStyle = `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, 0.8)`;
    ctx.lineWidth = 2;
    ctx.beginPath();
    flow.path.forEach((nodeId, index) => {
      const node = layout.nodes.find((n) => n.id === nodeId);
      if (!node) return;
      const px = xFrom(node.x);
      const py = yFrom(node.y);
      if (index === 0) {
        ctx.moveTo(px, py);
      } else {
        ctx.lineTo(px, py);
      }
    });
    ctx.stroke();
  }

  for (const node of layout.nodes) {
    const px = xFrom(node.x);
    const py = yFrom(node.y);
    ctx.beginPath();
    ctx.fillStyle = node.isMerge ? "#ffffff" : "#58a6d8";
    ctx.arc(px, py, node.isMerge ? 8 : 6, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#d8ecff";
    ctx.font = "12px IBM Plex Sans, sans-serif";
    ctx.fillText(node.label, px + 10, py - 8);
  }
}

function renderText(layout: LayoutResult): void {
  metricsEl.textContent = JSON.stringify(
    {
      dimensions: layout.dimensions,
      metrics: layout.metrics,
      temporal: layout.temporal,
    },
    null,
    2,
  );

  collisionsEl.textContent =
    layout.collisions.length === 0
      ? "No collisions."
      : layout.collisions.map((c) => `- [${c.type}] ${c.flows.join(" vs ")} :: ${c.detail}`).join("\n");

  voxelsEl.textContent = JSON.stringify(layout.voxels.slice(0, 14), null, 2);
}

function parseLayoutFromResult(result: unknown): LayoutResult | null {
  const toolResult = result as { content?: Array<{ type?: string; text?: string }> };
  const text = toolResult.content?.find((c) => c.type === "text")?.text;
  if (!text) return null;
  try {
    return JSON.parse(text) as LayoutResult;
  } catch {
    return null;
  }
}

async function requestLayout(): Promise<void> {
  const flowCount = Number(flowCountInput.value) || 8;
  const mode = (modeInput.value || "default") as Mode;
  const atUnixMs = Number(atUnixMsInput.value) || Date.now();
  const windowMs = Number(windowMsInput.value) || 60000;

  const result = await app.callServerTool({
    name: "cymatic-voxel-layout",
    arguments: { flowCount, mode, atUnixMs, windowMs },
  });

  const layout = parseLayoutFromResult(result);
  if (!layout) {
    metricsEl.textContent = "Failed to parse layout payload.";
    collisionsEl.textContent = "Failed to parse layout payload.";
    voxelsEl.textContent = "Failed to parse layout payload.";
    return;
  }

  draw(layout);
  renderText(layout);
}

app.ontoolresult = (result) => {
  const layout = parseLayoutFromResult(result);
  if (!layout) return;
  draw(layout);
  renderText(layout);
};

regenBtn.addEventListener("click", () => {
  requestLayout().catch((err: unknown) => {
    const message = err instanceof Error ? err.message : String(err);
    metricsEl.textContent = `Error requesting layout: ${message}`;
  });
});
