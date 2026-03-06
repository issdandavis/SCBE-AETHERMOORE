import cors from "cors";
import express from "express";
import fs from "node:fs/promises";
import path from "node:path";

import {
  registerAppResource,
  registerAppTool,
  RESOURCE_MIME_TYPE,
} from "@modelcontextprotocol/ext-apps/server";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";

import { buildCymaticVoxelLayout, type Mode } from "./src/spectralGraph.js";

const server = new McpServer({
  name: "SCBE Cymatic Voxel MCP App",
  version: "0.1.0",
});

const resourceUri = "ui://cymatic-voxel/mcp-app.html";

registerAppTool(
  server,
  "cymatic-voxel-layout",
  {
    title: "Cymatic Voxel Layout",
    description:
      "Generates spectral-flow graph routing with merge-node-only intersections and voxelized lane output.",
    inputSchema: {
      type: "object",
      properties: {
        flowCount: {
          type: "integer",
          minimum: 1,
          maximum: 32,
          default: 8,
        },
        mode: {
          type: "string",
          enum: ["default", "quasi", "dense"],
          default: "default",
        },
        atUnixMs: {
          type: "number",
          description: "Temporal slice center in Unix milliseconds.",
        },
        windowMs: {
          type: "number",
          minimum: 1000,
          maximum: 86400000,
          default: 60000,
          description: "Temporal slice window width in milliseconds.",
        },
      },
      additionalProperties: false,
    },
    _meta: {
      ui: { resourceUri },
    },
  },
  async (args) => {
    const rawFlowCount = typeof args?.flowCount === "number" ? args.flowCount : 8;
    const flowCount = Math.max(1, Math.min(32, Math.floor(rawFlowCount)));
    const rawMode = typeof args?.mode === "string" ? args.mode : "default";
    const mode: Mode = rawMode === "quasi" || rawMode === "dense" ? rawMode : "default";
    const atUnixMs = typeof args?.atUnixMs === "number" ? args.atUnixMs : undefined;
    const windowMs = typeof args?.windowMs === "number" ? args.windowMs : undefined;

    const layout = buildCymaticVoxelLayout(flowCount, mode, {
      atUnixMs,
      windowMs,
    });
    const payload = JSON.stringify(layout);

    return {
      content: [
        {
          type: "text",
          text: payload,
        },
      ],
    };
  },
);

registerAppResource(
  server,
  resourceUri,
  resourceUri,
  { mimeType: RESOURCE_MIME_TYPE },
  async () => {
    const htmlPath = path.join(import.meta.dirname, "dist", "mcp-app.html");
    const html = await fs.readFile(htmlPath, "utf-8");

    return {
      contents: [
        {
          uri: resourceUri,
          mimeType: RESOURCE_MIME_TYPE,
          text: html,
        },
      ],
    };
  },
);

const app = express();
app.use(cors());
app.use(express.json({ limit: "1mb" }));

app.post("/mcp", async (req, res) => {
  const transport = new StreamableHTTPServerTransport({
    sessionIdGenerator: undefined,
    enableJsonResponse: true,
  });

  res.on("close", () => transport.close());
  await server.connect(transport);
  await transport.handleRequest(req, res, req.body);
});

app.listen(3001, (err?: Error) => {
  if (err) {
    console.error("Failed to start MCP App server:", err);
    process.exit(1);
  }
  console.log("Cymatic Voxel MCP App listening at http://localhost:3001/mcp");
});
