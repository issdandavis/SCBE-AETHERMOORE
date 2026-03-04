const MCP_PROTOCOL_VERSION = "2025-06-18";

type JsonRpcRequest = {
  jsonrpc: "2.0";
  id: string | number;
  method: string;
  params?: unknown;
};

type JsonRpcResponse = {
  jsonrpc: "2.0";
  id: string | number | null;
  result?: unknown;
  error?: {
    code: number;
    message: string;
    data?: unknown;
  };
};

type McpTool = {
  name: string;
  title?: string;
  description: string;
  inputSchema: Record<string, unknown>;
  outputSchema?: Record<string, unknown>;
};

type ToolCallResult = {
  content: Array<{ type: string; text?: string; data?: string; mimeType?: string }>;
  structuredContent?: unknown;
  isError?: boolean;
};

export class FigmaMcpClient {
  private endpoint: string;
  private sessionId: string | null = null;
  private initialized = false;
  private cachedTools: McpTool[] = [];
  private requestId = 0;

  constructor(endpoint: string) {
    this.endpoint = endpoint;
  }

  private nextId(): number {
    return ++this.requestId;
  }

  private async sendRequest(method: string, params?: unknown): Promise<JsonRpcResponse> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      "MCP-Protocol-Version": MCP_PROTOCOL_VERSION,
    };

    if (this.sessionId) {
      headers["Mcp-Session-Id"] = this.sessionId;
    }

    const body: JsonRpcRequest = {
      jsonrpc: "2.0",
      id: this.nextId(),
      method,
      ...(params !== undefined ? { params } : {}),
    };

    const response = await fetch(this.endpoint, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    const sessionIdHeader = response.headers.get("Mcp-Session-Id");
    if (sessionIdHeader) {
      this.sessionId = sessionIdHeader;
    }

    if (!response.ok) {
      throw new Error(`Figma MCP request failed: ${response.status} ${response.statusText}`);
    }

    return response.json() as Promise<JsonRpcResponse>;
  }

  async initialize(): Promise<{
    protocolVersion: string;
    capabilities: unknown;
    serverInfo: unknown;
  }> {
    if (this.initialized) {
      return {
        protocolVersion: MCP_PROTOCOL_VERSION,
        capabilities: {},
        serverInfo: { name: "figma-mcp", cached: true },
      };
    }

    const response = await this.sendRequest("initialize", {
      protocolVersion: MCP_PROTOCOL_VERSION,
      capabilities: {},
      clientInfo: {
        name: "ai-orchestration-hub",
        version: "1.0.0",
      },
    });

    if (response.error) {
      throw new Error(`Figma MCP initialize failed: ${response.error.message}`);
    }

    this.initialized = true;

    await this.sendRequest("notifications/initialized");

    return response.result as {
      protocolVersion: string;
      capabilities: unknown;
      serverInfo: unknown;
    };
  }

  async listTools(): Promise<McpTool[]> {
    if (!this.initialized) {
      await this.initialize();
    }

    if (this.cachedTools.length > 0) {
      return this.cachedTools;
    }

    const response = await this.sendRequest("tools/list", {});

    if (response.error) {
      throw new Error(`Figma MCP tools/list failed: ${response.error.message}`);
    }

    const result = response.result as { tools: McpTool[]; nextCursor?: string | null };
    this.cachedTools = result.tools || [];
    return this.cachedTools;
  }

  async callTool(name: string, args: Record<string, unknown> = {}): Promise<ToolCallResult> {
    if (!this.initialized) {
      await this.initialize();
    }

    const response = await this.sendRequest("tools/call", {
      name,
      arguments: args,
    });

    if (response.error) {
      return {
        content: [{ type: "text", text: `Error: ${response.error.message}` }],
        isError: true,
      };
    }

    return response.result as ToolCallResult;
  }

  async getScreenshot(fileKey: string, nodeId: string): Promise<{
    success: boolean;
    imageData?: string;
    mimeType?: string;
    error?: string;
  }> {
    try {
      const result = await this.callTool("get_screenshot", {
        file_key: fileKey,
        node_id: nodeId,
      });

      if (result.isError) {
        const errorText = result.content.find(c => c.type === "text")?.text || "Unknown error";
        return { success: false, error: errorText };
      }

      const imageContent = result.content.find(c => c.type === "image");
      if (imageContent && imageContent.data) {
        return {
          success: true,
          imageData: imageContent.data,
          mimeType: imageContent.mimeType || "image/png",
        };
      }

      const textContent = result.content.find(c => c.type === "text");
      if (textContent?.text) {
        try {
          const parsed = JSON.parse(textContent.text);
          if (parsed.imageUrl) {
            return { success: true, imageData: parsed.imageUrl };
          }
        } catch {
        }
        return { success: false, error: textContent.text };
      }

      return { success: false, error: "No image data in response" };
    } catch (error: any) {
      return { success: false, error: error.message || String(error) };
    }
  }

  async ping(): Promise<boolean> {
    try {
      const response = await this.sendRequest("ping");
      return !response.error;
    } catch {
      return false;
    }
  }

  getSessionId(): string | null {
    return this.sessionId;
  }

  isInitialized(): boolean {
    return this.initialized;
  }

  clearCache(): void {
    this.cachedTools = [];
  }
}

let figmaClient: FigmaMcpClient | null = null;

export function getFigmaMcpClient(): FigmaMcpClient | null {
  if (figmaClient) {
    return figmaClient;
  }

  const endpoint = process.env.MCP_FIGMA_URL || process.env.FIGMA_MCP_ENDPOINT;
  if (!endpoint) {
    return null;
  }

  figmaClient = new FigmaMcpClient(endpoint);
  return figmaClient;
}

export async function testFigmaMcpConnection(): Promise<{
  success: boolean;
  tools?: McpTool[];
  error?: string;
}> {
  try {
    const client = getFigmaMcpClient();
    if (!client) {
      return { success: false, error: "Figma MCP endpoint not configured" };
    }
    await client.initialize();
    const tools = await client.listTools();
    return { success: true, tools };
  } catch (error: any) {
    return { success: false, error: error.message || String(error) };
  }
}
