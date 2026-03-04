import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { hashPassword, verifyPassword, requireAuth, attachUser, validateApiKey } from "./auth";
import { setupAuth, isAuthenticated } from "./replitAuth";
import { authLimiter, apiLimiter, agentLimiter } from "./middleware/rateLimiter";
import { checkBudget } from "./middleware/costGovernor";
import { orchestratorQueue } from "./services/orchestrator";
import { retryService } from "./services/retryService";
import { processGuideAgentRequest } from "./services/guideAgent";
import { createMcpRouter } from "./mcp";
import { getZapierMcpClient, testZapierMcpConnection } from "./services/zapierMcpClient";
import { getFigmaMcpClient } from "./services/figmaMcpClient";
import { dispatchEvent, generateSecretKey, getSampleData, SUPPORTED_EVENTS, type ZapierEventType } from "./services/zapierService";
import { z } from "zod";
import { insertUserSchema, insertOrgSchema, insertProjectSchema, insertIntegrationSchema, insertMemoryItemSchema, insertWorkspaceSchema } from "@shared/schema";
import { getProviderAdapter } from "./services/providerAdapters";
import { getAvailableProviders } from "./services/aiPriorityManager";
import crypto from "crypto";
import shopifyRouter from "./shopify";

const VERSION = "1.0.0";

// SSE connections for agent run streaming
const sseConnections = new Map<string, Response>();

// Setup SSE streaming for agent runs
orchestratorQueue.on("log", (runId: string, logEntry: any) => {
  const res = sseConnections.get(runId);
  if (res) {
    res.write(`data: ${JSON.stringify(logEntry)}\n\n`);
  }
});

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {
  
  // Setup Replit Auth (social login) BEFORE other routes - skip in dev if no REPL_ID
  if (process.env.REPL_ID && process.env.REPL_ID !== 'test-client-id-12345') {
    await setupAuth(app);
  } else {
    console.log('Skipping Replit auth setup for development');
    // Mock session middleware for development
    app.use((req, res, next) => {
      req.user = { id: 'dev-user', email: 'dev@example.com' };
      next();
    });
  }
  
  // Attach user to all requests
  app.use(attachUser);

  // MCP Protocol endpoint
  app.use("/mcp", createMcpRouter());

  // Shopify integration routes
  app.use("/api/shopify", shopifyRouter);

  // Health endpoint
  app.get("/api/health", (req, res) => {
    res.json({
      status: "ok",
      time: new Date().toISOString(),
      version: VERSION,
    });
  });

  // ===== FIGMA DESIGN PREVIEW ROUTE =====

  app.post("/api/figma/screenshot", apiLimiter, async (req: Request, res: Response) => {
    try {
      const { fileKey, nodeId } = z.object({
        fileKey: z.string().min(1, "File key is required"),
        nodeId: z.string().min(1, "Node ID is required"),
      }).parse(req.body);

      const figmaClient = getFigmaMcpClient();
      if (!figmaClient) {
        return res.status(503).json({ 
          error: "Figma MCP not configured", 
          message: "The Figma integration is not set up. Please configure the MCP_FIGMA_URL environment variable." 
        });
      }

      const result = await figmaClient.getScreenshot(fileKey, nodeId);

      if (!result.success) {
        return res.status(400).json({ 
          error: "Failed to fetch screenshot", 
          message: result.error 
        });
      }

      res.json({
        success: true,
        imageData: result.imageData,
        mimeType: result.mimeType || "image/png",
      });
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ 
          error: "Invalid request", 
          message: error.errors.map(e => e.message).join(", ") 
        });
      }
      console.error("[Figma Screenshot] Error:", error);
      res.status(500).json({ 
        error: "Failed to fetch Figma screenshot",
        message: error instanceof Error ? error.message : "Unknown error"
      });
    }
  });

  // ===== AI PROVIDERS ROUTE =====

  app.get("/api/ai/providers", apiLimiter, (req: Request, res: Response) => {
    try {
      const providers = getAvailableProviders();
      res.json({ 
        providers,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      res.status(500).json({ error: "Failed to get providers" });
    }
  });

  // ===== AUTH ROUTES =====
  
  app.post("/api/auth/signup", authLimiter, async (req: Request, res: Response) => {
    try {
      const { email, password, role } = z.object({
        email: z.string().email(),
        password: z.string().min(8),
        role: z.enum(["owner", "admin", "member", "viewer"]).optional(),
      }).parse(req.body);

      const existing = await storage.getUserByEmail(email);
      if (existing) {
        return res.status(409).json({ error: "Email already registered" });
      }

      const passwordHash = await hashPassword(password);
      const user = await storage.createUser({
        email,
        passwordHash,
        role: role || "owner",
      });

      // Always create a default org for new users
      const org = await storage.createOrg({
        name: `${email}'s Organization`,
        ownerUserId: user.id,
      });
      req.session.orgId = org.id;
      req.session.userId = user.id;
      
      dispatchEvent(org.id, "user.created", {
        id: user.id,
        email: user.email,
        role: user.role,
        createdAt: user.createdAt.toISOString(),
      }).catch(err => console.error("[Zapier] Failed to dispatch user.created:", err));
      
      res.json({ id: user.id, email: user.email, role: user.role, orgId: org.id });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.post("/api/auth/login", authLimiter, async (req: Request, res: Response) => {
    try {
      const { email, password } = z.object({
        email: z.string().email(),
        password: z.string(),
      }).parse(req.body);

      const user = await storage.getUserByEmail(email);
      if (!user) {
        return res.status(401).json({ error: "Invalid credentials" });
      }

      // Check if account is locked
      if (user.lockedUntil && new Date(user.lockedUntil) > new Date()) {
        const remainingMins = Math.ceil((new Date(user.lockedUntil).getTime() - Date.now()) / 60000);
        return res.status(423).json({ 
          error: `Account locked. Try again in ${remainingMins} minute${remainingMins > 1 ? 's' : ''}.` 
        });
      }

      const valid = await verifyPassword(password, user.passwordHash);
      if (!valid) {
        const newAttempts = (user.failedAttempts || 0) + 1;
        const maxAttempts = 10;
        
        if (newAttempts >= maxAttempts) {
          // Lock account for 15 minutes
          await storage.updateUserLoginAttempts(user.id, newAttempts, new Date(Date.now() + 15 * 60 * 1000));
          return res.status(423).json({ error: "Too many failed attempts. Account locked for 15 minutes." });
        }
        
        await storage.updateUserLoginAttempts(user.id, newAttempts, null);
        const remaining = maxAttempts - newAttempts;
        return res.status(401).json({ error: `Invalid credentials. ${remaining} attempts remaining.` });
      }

      // Reset failed attempts on successful login
      if (user.failedAttempts > 0) {
        await storage.updateUserLoginAttempts(user.id, 0, null);
      }

      req.session.userId = user.id;
      
      // Set org if user is owner
      const orgs = await storage.getOrgsByUser(user.id);
      if (orgs.length > 0) {
        req.session.orgId = orgs[0].id;
      }

      res.json({ id: user.id, email: user.email, role: user.role });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  // Guest login - creates a temporary viewer session
  app.post("/api/auth/guest", authLimiter, async (req: Request, res: Response) => {
    try {
      const guestId = `guest_${crypto.randomUUID()}`;
      const guestEmail = `${guestId}@guest.aicore.local`;
      
      // Create a guest user with viewer role
      const guestUser = await storage.createUser({
        email: guestEmail,
        passwordHash: "GUEST_NO_PASSWORD",
        role: "viewer",
        firstName: "Guest",
        lastName: "User",
      });

      // Create a demo org for the guest
      const org = await storage.createOrg({
        name: "Guest Demo Organization",
        ownerUserId: guestUser.id,
      });

      req.session.userId = guestUser.id;
      req.session.orgId = org.id;
      req.session.isGuest = true;

      res.json({ 
        id: guestUser.id, 
        email: guestUser.email, 
        role: guestUser.role,
        orgId: org.id,
        isGuest: true,
      });
    } catch (error) {
      console.error("[Guest Login] Error:", error);
      res.status(500).json({ error: "Failed to create guest session" });
    }
  });

  app.post("/api/auth/change-password", requireAuth, authLimiter, async (req: Request, res: Response) => {
    try {
      const { currentPassword, newPassword } = z.object({
        currentPassword: z.string().min(1, "Current password is required"),
        newPassword: z.string().min(8, "New password must be at least 8 characters"),
      }).parse(req.body);

      const userId = req.session.userId;
      if (!userId) {
        return res.status(401).json({ error: "Not authenticated" });
      }

      const user = await storage.getUser(userId);
      if (!user) {
        return res.status(404).json({ error: "User not found" });
      }

      // Verify current password (skip for guest or OAuth users without password)
      if (user.passwordHash && user.passwordHash !== "GUEST_NO_PASSWORD") {
        const valid = await verifyPassword(currentPassword, user.passwordHash);
        if (!valid) {
          return res.status(401).json({ error: "Current password is incorrect" });
        }
      }

      // Hash and update new password
      const newHash = await hashPassword(newPassword);
      await storage.updateUserPassword(userId, newHash);

      await storage.createAuditLog({
        orgId: req.session.orgId!,
        userId,
        action: "password_changed",
        target: user.email,
        detailJson: null,
      });

      res.json({ success: true, message: "Password changed successfully" });
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ error: error.errors[0].message });
      }
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to change password" });
    }
  });

  app.post("/api/auth/logout", requireAuth, (req: Request, res: Response) => {
    req.session.destroy((err) => {
      if (err) {
        return res.status(500).json({ error: "Logout failed" });
      }
      res.json({ success: true });
    });
  });

  app.get("/api/auth/me", requireAuth, async (req: Request, res: Response) => {
    const user = await storage.getUser(req.session.userId!);
    if (!user) {
      return res.status(404).json({ error: "User not found" });
    }
    res.json({ id: user.id, email: user.email, role: user.role });
  });

  // Social login user endpoint (Replit Auth)
  app.get("/api/auth/user", isAuthenticated, async (req: any, res: Response) => {
    try {
      const userId = req.user.claims.sub;
      const user = await storage.getUser(userId);
      
      if (!user) {
        return res.status(404).json({ message: "User not found" });
      }
      
      // Check if user has an org, if not create one
      let orgs = await storage.getOrgsByUser(user.id);
      if (orgs.length === 0) {
        const org = await storage.createOrg({
          name: `${user.email}'s Organization`,
          ownerUserId: user.id,
        });
        orgs = [org];
      }
      
      res.json({
        id: user.id,
        email: user.email,
        role: user.role,
        firstName: user.firstName,
        lastName: user.lastName,
        profileImageUrl: user.profileImageUrl,
        orgId: orgs[0]?.id,
      });
    } catch (error) {
      console.error("Error fetching user:", error);
      res.status(500).json({ message: "Failed to fetch user" });
    }
  });

  // ===== ASSISTANT CHAT ROUTES =====

  app.post("/api/assistant/chat", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { message, context } = z.object({
        message: z.string().min(1).max(2000),
        context: z.string().default("dashboard"),
      }).parse(req.body);

      const orgId = req.session.orgId;
      const userId = req.session.userId;

      if (!orgId || !userId) {
        return res.status(400).json({ error: "No organization or user context" });
      }

      const result = await processGuideAgentRequest({
        message,
        context,
        orgId,
        userId,
      });

      await storage.createAuditLog({
        orgId,
        userId,
        action: "assistant_chat",
        target: context,
        detailJson: { messageLength: message.length, actionsCount: result.actions?.length || 0 },
      });

      res.json(result);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  // ===== INTEGRATION VAULT ROUTES =====

  app.get("/api/integrations", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const integrations = await storage.getIntegrations(orgId);
      res.json(integrations);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch integrations" });
    }
  });

  app.post("/api/integrations/connect", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const { provider, metadataJson } = z.object({
        provider: z.string(),
        metadataJson: z.any().optional(),
      }).parse(req.body);

      const integration = await storage.createIntegration({
        orgId,
        provider,
        status: "connected",
        metadataJson: metadataJson || {},
      });

      await storage.createAuditLog({
        orgId,
        userId: req.session.userId || null,
        action: "integration_connected",
        target: provider,
        detailJson: { integrationId: integration.id },
      });

      dispatchEvent(orgId, "integration.connected", {
        id: integration.id,
        orgId: integration.orgId,
        provider: integration.provider,
        status: integration.status,
        createdAt: integration.createdAt.toISOString(),
      }).catch(err => console.error("[Zapier] Failed to dispatch integration.connected:", err));

      res.json(integration);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.post("/api/integrations/disconnect", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = z.object({ id: z.string() }).parse(req.body);
      
      const integration = await storage.getIntegration(id);
      if (!integration) {
        return res.status(404).json({ error: "Integration not found" });
      }

      if (integration.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      await storage.disconnectIntegration(id);

      await storage.createAuditLog({
        orgId: integration.orgId,
        userId: req.session.userId || null,
        action: "integration_disconnected",
        target: integration.provider,
        detailJson: { integrationId: id },
      });

      res.json({ success: true });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  // ===== CREDENTIAL VAULT ROUTES =====

  app.get("/api/vault/credentials", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const userId = req.session.userId;
      if (!userId) {
        return res.status(401).json({ error: "Unauthorized" });
      }

      const { listUserCredentials, SUPPORTED_PROVIDERS } = await import("./services/vault");
      const credentials = await listUserCredentials(userId);
      
      res.json({ 
        credentials,
        supportedProviders: SUPPORTED_PROVIDERS,
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to list credentials" });
    }
  });

  app.post("/api/vault/credentials", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { provider, apiKey, label } = z.object({
        provider: z.string(),
        apiKey: z.string().min(10, "API key too short"),
        label: z.string().optional(),
      }).parse(req.body);

      const userId = req.session.userId;
      if (!userId) {
        return res.status(401).json({ error: "Unauthorized" });
      }

      const { storeUserCredential, validateApiKeyFormat, maskApiKey } = await import("./services/vault");

      if (!validateApiKeyFormat(provider, apiKey)) {
        return res.status(400).json({ error: `Invalid API key format for ${provider}` });
      }

      const credential = await storeUserCredential(userId, provider, apiKey, label);

      await storage.createAuditLog({
        orgId: req.session.orgId!,
        userId,
        action: "credential_stored",
        target: provider,
        detailJson: { credentialId: credential.id, masked: maskApiKey(apiKey) },
      });

      res.json({ 
        success: true, 
        credential: {
          id: credential.id,
          provider: credential.provider,
          label: credential.label,
        },
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to store credential" });
    }
  });

  app.delete("/api/vault/credentials/:id", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const userId = req.session.userId;
      if (!userId) {
        return res.status(401).json({ error: "Unauthorized" });
      }

      const { deleteUserCredential } = await import("./services/vault");
      const deleted = await deleteUserCredential(userId, id);

      if (!deleted) {
        return res.status(404).json({ error: "Credential not found" });
      }

      await storage.createAuditLog({
        orgId: req.session.orgId!,
        userId,
        action: "credential_deleted",
        target: id,
        detailJson: null,
      });

      res.json({ success: true });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to delete credential" });
    }
  });

  app.post("/api/vault/credentials/test", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { provider, apiKey } = z.object({
        provider: z.string(),
        apiKey: z.string().min(10, "API key too short"),
      }).parse(req.body);

      const { validateApiKeyFormat, testApiKey } = await import("./services/vault");

      if (!validateApiKeyFormat(provider, apiKey)) {
        return res.status(400).json({ valid: false, error: `Invalid API key format for ${provider}` });
      }

      const result = await testApiKey(provider, apiKey);
      res.json(result);
    } catch (error) {
      res.status(400).json({ valid: false, error: error instanceof Error ? error.message : "Test failed" });
    }
  });

  app.get("/api/vault/usage", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

      const records = await storage.getUsageRecords(orgId, thirtyDaysAgo);
      const summary = await storage.getUsageSummary(orgId, thirtyDaysAgo);

      const byProvider: Record<string, { tokens: number; costUsd: number }> = {};
      for (const record of records) {
        if (!byProvider[record.provider]) {
          byProvider[record.provider] = { tokens: 0, costUsd: 0 };
        }
        byProvider[record.provider].tokens += record.inputTokens + record.outputTokens;
        byProvider[record.provider].costUsd += parseFloat(record.estimatedCostUsd || "0");
      }

      res.json({
        summary: {
          totalTokens: summary.totalTokens,
          totalCostUsd: summary.totalCostUsd,
          periodDays: 30,
        },
        byProvider,
        recentRecords: records.slice(0, 50),
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to get usage" });
    }
  });

  // ===== AUDIT LOG ROUTES =====

  app.get("/api/audit-logs", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const limit = parseInt(req.query.limit as string) || 50;
      const logs = await storage.getAuditLogs(orgId, Math.min(limit, 100));
      res.json(logs);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch audit logs" });
    }
  });

  // ===== DASHBOARD STATS ROUTE =====

  app.get("/api/dashboard/stats", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

      const [usageSummary, integrations, roundtableSessions] = await Promise.all([
        storage.getUsageSummary(orgId, thirtyDaysAgo),
        storage.getIntegrations(orgId),
        storage.getRoundtableSessions(orgId),
      ]);

      const connectedIntegrations = integrations.filter(i => i.status === "connected").length;
      const activeRoundtables = roundtableSessions.filter(s => s.status === "active").length;

      res.json({
        usage: {
          totalTokens: usageSummary.totalTokens,
          totalCostUsd: usageSummary.totalCostUsd,
          periodDays: 30,
        },
        integrations: {
          total: integrations.length,
          connected: connectedIntegrations,
        },
        roundtables: {
          total: roundtableSessions.length,
          active: activeRoundtables,
        },
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch dashboard stats" });
    }
  });

  // ===== AGENT ORCHESTRATION ROUTES =====

  app.post("/api/agents/run", requireAuth, agentLimiter, checkBudget, async (req: Request, res: Response) => {
    try {
      const { projectId, goal, mode, provider, model } = z.object({
        projectId: z.string(),
        goal: z.string(),
        mode: z.string().optional(),
        provider: z.string().default("openai"),
        model: z.string().default("gpt-4o"),
      }).parse(req.body);

      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const project = await storage.getProject(projectId);
      if (!project || project.orgId !== orgId) {
        return res.status(404).json({ error: "Project not found" });
      }

      const agentRun = await storage.createAgentRun({
        projectId,
        status: "queued",
        model,
        provider,
        inputJson: { goal, mode },
        outputJson: null,
        costEstimate: null,
      });

      orchestratorQueue.enqueue({
        runId: agentRun.id,
        projectId,
        orgId,
        goal,
        mode: mode || "default",
      });

      res.json({ runId: agentRun.id });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.get("/api/agents/run/:runId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { runId } = req.params;
      const agentRun = await storage.getAgentRun(runId);
      
      if (!agentRun) {
        return res.status(404).json({ error: "Agent run not found" });
      }

      const project = await storage.getProject(agentRun.projectId);
      if (!project || project.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      const messages = await storage.getMessagesByAgentRun(runId);

      res.json({ ...agentRun, messages });
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch agent run" });
    }
  });

  app.get("/api/agents/stream/:runId", requireAuth, async (req: Request, res: Response) => {
    const { runId } = req.params;

    res.setHeader("Content-Type", "text/event-stream");
    res.setHeader("Cache-Control", "no-cache");
    res.setHeader("Connection", "keep-alive");

    sseConnections.set(runId, res);

    req.on("close", () => {
      sseConnections.delete(runId);
    });
  });

  app.get("/api/agents/run/:runId/traces", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { runId } = req.params;
      const agentRun = await storage.getAgentRun(runId);
      
      if (!agentRun) {
        return res.status(404).json({ error: "Agent run not found" });
      }

      const project = await storage.getProject(agentRun.projectId);
      if (!project || project.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      const traces = await storage.getDecisionTraces(runId);
      res.json(traces);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch decision traces" });
    }
  });

  // ===== APPROVAL ROUTES =====

  app.get("/api/approvals/pending", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(403).json({ error: "No organization context" });
      }

      const pendingApprovals = await storage.getPendingApprovals(orgId);
      res.json(pendingApprovals);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch pending approvals" });
    }
  });

  app.post("/api/approvals/:traceId/approve", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { traceId } = req.params;
      const userId = req.session.userId;
      
      if (!userId) {
        return res.status(401).json({ error: "Not authenticated" });
      }

      const trace = await storage.getDecisionTrace(traceId);
      if (!trace) {
        return res.status(404).json({ error: "Decision trace not found" });
      }

      if (trace.approvalStatus !== "pending") {
        return res.status(400).json({ error: "Decision is not pending approval" });
      }

      const updated = await storage.approveDecision(traceId, userId);
      
      // Resume the agent run if it was awaiting approval
      const agentRun = await storage.getAgentRun(trace.agentRunId);
      if (agentRun && agentRun.status === "awaiting_approval") {
        await storage.updateAgentRun(trace.agentRunId, { status: "running" });
        orchestratorQueue.emit("approval_granted", trace.agentRunId);
      }

      await storage.createAuditLog({
        orgId: req.session.orgId!,
        userId,
        action: "decision_approved",
        target: traceId,
        detailJson: { decision: trace.decision, agentRunId: trace.agentRunId },
      });

      res.json(updated);
    } catch (error) {
      res.status(500).json({ error: "Failed to approve decision" });
    }
  });

  app.post("/api/approvals/:traceId/reject", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { traceId } = req.params;
      const { reason } = z.object({
        reason: z.string().min(1, "Rejection reason is required"),
      }).parse(req.body);
      
      const userId = req.session.userId;
      
      if (!userId) {
        return res.status(401).json({ error: "Not authenticated" });
      }

      const trace = await storage.getDecisionTrace(traceId);
      if (!trace) {
        return res.status(404).json({ error: "Decision trace not found" });
      }

      if (trace.approvalStatus !== "pending") {
        return res.status(400).json({ error: "Decision is not pending approval" });
      }

      const updated = await storage.rejectDecision(traceId, userId, reason);
      
      // Cancel the agent run if it was awaiting approval
      const agentRun = await storage.getAgentRun(trace.agentRunId);
      if (agentRun && agentRun.status === "awaiting_approval") {
        await storage.updateAgentRun(trace.agentRunId, { 
          status: "cancelled",
          outputJson: { error: `Decision rejected: ${reason}` },
        });
        orchestratorQueue.emit("approval_rejected", trace.agentRunId, reason);
      }

      await storage.createAuditLog({
        orgId: req.session.orgId!,
        userId,
        action: "decision_rejected",
        target: traceId,
        detailJson: { decision: trace.decision, reason, agentRunId: trace.agentRunId },
      });

      res.json(updated);
    } catch (error) {
      res.status(500).json({ error: "Failed to reject decision" });
    }
  });

  // ===== MEMORY ROUTES =====

  app.post("/api/memory/add", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { projectId, kind, source, content } = z.object({
        projectId: z.string(),
        kind: z.string(),
        source: z.string(),
        content: z.string(),
      }).parse(req.body);

      const project = await storage.getProject(projectId);
      if (!project || project.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      const memoryItem = await storage.createMemoryItem({
        projectId,
        kind,
        source,
        content,
        embeddingRef: null,
      });

      res.json(memoryItem);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.get("/api/memory/search", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { projectId, q } = z.object({
        projectId: z.string(),
        q: z.string().optional(),
      }).parse(req.query);

      const project = await storage.getProject(projectId);
      if (!project || project.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      const items = q
        ? await storage.searchMemoryItems(projectId, q)
        : await storage.getMemoryItems(projectId);

      res.json(items);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  // ===== GIT OPERATIONS ROUTES =====

  app.get("/api/repos", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    const githubConfigured = !!process.env.GITHUB_TOKEN;
    
    if (!githubConfigured) {
      return res.json({
        configured: false,
        message: "GitHub integration not configured. Add GITHUB_TOKEN to connect.",
        repos: [],
      });
    }

    // Stub for now
    res.json({
      configured: true,
      repos: [
        { name: "example-repo", branch: "main", url: "https://github.com/user/example-repo" },
      ],
    });
  });

  app.post("/api/repos/commit", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { repo, branch, message, files } = z.object({
        repo: z.string(),
        branch: z.string(),
        message: z.string(),
        files: z.array(z.object({
          path: z.string(),
          content: z.string(),
        })),
      }).parse(req.body);

      if (branch === "main" || branch === "master") {
        return res.status(400).json({
          error: "Direct commits to main/master are not allowed. Please use a feature branch.",
        });
      }

      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      await storage.createAuditLog({
        orgId,
        userId: req.session.userId || null,
        action: "git_commit_attempted",
        target: repo,
        detailJson: { branch, message, fileCount: files.length },
      });

      if (!process.env.GITHUB_TOKEN) {
        return res.status(501).json({
          configured: false,
          message: "GitHub integration not configured",
        });
      }

      // Stub response
      res.json({
        success: true,
        message: "Commit queued (stub implementation)",
        branch,
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  // ===== PROJECT ROUTES =====

  app.get("/api/projects", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    const orgId = req.session.orgId;
    if (!orgId) {
      return res.status(400).json({ error: "No organization set" });
    }

    const projects = await storage.getProjectsByOrg(orgId);
    res.json(projects);
  });

  app.post("/api/projects", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const { name } = z.object({ name: z.string() }).parse(req.body);
      
      const project = await storage.createProject({ orgId, name });
      res.json(project);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  // ===== WORKSPACE ROUTES =====

  app.get("/api/workspaces", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const workspaces = await storage.getWorkspacesByOrg(orgId);
      res.json(workspaces);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch workspaces" });
    }
  });

  app.get("/api/workspaces/:id", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const workspace = await storage.getWorkspace(id);
      
      if (!workspace) {
        return res.status(404).json({ error: "Workspace not found" });
      }

      if (workspace.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      res.json(workspace);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch workspace" });
    }
  });

  app.post("/api/workspaces", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      const userId = req.session.userId;
      if (!orgId || !userId) {
        return res.status(400).json({ error: "No organization or user context" });
      }

      const data = insertWorkspaceSchema.parse({
        ...req.body,
        orgId,
        createdBy: userId,
      });

      const workspace = await storage.createWorkspace(data);
      
      await storage.createAuditLog({
        orgId,
        userId,
        action: "workspace_created",
        target: workspace.id,
        detailJson: { name: workspace.name, type: workspace.type },
      });

      res.status(201).json(workspace);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.patch("/api/workspaces/:id", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const workspace = await storage.getWorkspace(id);
      
      if (!workspace) {
        return res.status(404).json({ error: "Workspace not found" });
      }

      if (workspace.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      const updateData = insertWorkspaceSchema.partial().parse(req.body);
      const updated = await storage.updateWorkspace(id, updateData);

      if (!updated) {
        return res.status(404).json({ error: "Workspace not found" });
      }

      await storage.createAuditLog({
        orgId: req.session.orgId!,
        userId: req.session.userId || null,
        action: "workspace_updated",
        target: id,
        detailJson: { updates: Object.keys(updateData) },
      });

      res.json(updated);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.delete("/api/workspaces/:id", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const workspace = await storage.getWorkspace(id);
      
      if (!workspace) {
        return res.status(404).json({ error: "Workspace not found" });
      }

      if (workspace.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      await storage.deleteWorkspace(id);

      await storage.createAuditLog({
        orgId: req.session.orgId!,
        userId: req.session.userId || null,
        action: "workspace_deleted",
        target: id,
        detailJson: { name: workspace.name },
      });

      res.json({ success: true });
    } catch (error) {
      res.status(500).json({ error: "Failed to delete workspace" });
    }
  });

  // ===== ZAPIER INTEGRATION ROUTES =====

  app.post("/api/zapier/apikey/generate", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const key = crypto.randomBytes(32).toString("hex");
      const apiKey = await storage.createApiKey({
        orgId,
        key,
        name: "Zapier",
      });

      res.json({
        key,
        keyId: apiKey.id,
        message: "Copy this key to Zapier settings in x-api-key header",
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.post("/api/zapier/trigger", validateApiKey, async (req: Request, res: Response) => {
    try {
      const { projectId, goal, provider, model, zapierData } = z.object({
        projectId: z.string(),
        goal: z.string(),
        provider: z.string().optional().default("gemini"),
        model: z.string().optional(),
        zapierData: z.any().optional(),
      }).parse(req.body);

      const orgId = (req as any).orgId;
      const project = await storage.getProject(projectId);
      if (!project || project.orgId !== orgId) {
        return res.status(404).json({ error: "Project not found" });
      }

      // Create agent run triggered by Zapier
      const agentRun = await storage.createAgentRun({
        projectId,
        status: "queued",
        model: model || "gemini-2.0-flash",
        provider: provider || "gemini",
        inputJson: { goal, zapierData, triggeredBy: "zapier" },
        outputJson: null,
        costEstimate: null,
      });

      orchestratorQueue.enqueue({
        runId: agentRun.id,
        projectId,
        orgId,
        goal,
        mode: "zapier",
      });

      // Return run ID to Zapier
      res.json({
        success: true,
        runId: agentRun.id,
        projectId,
        status: "queued",
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.get("/api/zapier/status/:runId", validateApiKey, async (req: Request, res: Response) => {
    try {
      const { runId } = req.params;
      const agentRun = await storage.getAgentRun(runId);
      
      if (!agentRun) {
        return res.status(404).json({ error: "Run not found" });
      }

      const messages = await storage.getMessagesByAgentRun(runId);

      res.json({
        runId: agentRun.id,
        projectId: agentRun.projectId,
        status: agentRun.status,
        provider: agentRun.provider,
        model: agentRun.model,
        result: agentRun.outputJson,
        costEstimate: agentRun.costEstimate,
        messagesCount: messages.length,
        createdAt: agentRun.createdAt,
      });
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch run status" });
    }
  });

  // ===== ZAPIER MCP CLIENT ROUTES =====

  app.post("/api/zapier-mcp/test", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { endpoint } = z.object({ endpoint: z.string().url() }).parse(req.body);
      const result = await testZapierMcpConnection(endpoint);
      res.json(result);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.post("/api/zapier-mcp/connect", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const { endpoint, name } = z.object({
        endpoint: z.string().url(),
        name: z.string().optional(),
      }).parse(req.body);

      const result = await testZapierMcpConnection(endpoint);
      if (!result.success) {
        return res.status(400).json({ error: result.error || "Connection failed" });
      }

      const integration = await storage.createIntegration({
        orgId,
        provider: "zapier-mcp",
        status: "connected",
        metadataJson: {
          endpoint,
          name: name || "Zapier MCP",
          toolCount: result.tools?.length || 0,
          connectedAt: new Date().toISOString(),
        },
      });

      await storage.createAuditLog({
        orgId,
        userId: req.session.userId || null,
        action: "zapier_mcp_connected",
        target: "zapier-mcp",
        detailJson: { integrationId: integration.id, endpoint, toolCount: result.tools?.length || 0 },
      });

      res.json({
        success: true,
        integration,
        tools: result.tools,
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.get("/api/zapier-mcp/tools", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const integrations = await storage.getIntegrations(orgId);
      const zapierIntegration = integrations.find(i => i.provider === "zapier-mcp" && i.status === "connected");

      if (!zapierIntegration) {
        return res.json({ connected: false, tools: [] });
      }

      const metadata = zapierIntegration.metadataJson as { endpoint?: string } | null;
      if (!metadata?.endpoint) {
        return res.json({ connected: false, tools: [], error: "No endpoint configured" });
      }

      try {
        const client = getZapierMcpClient(metadata.endpoint);
        const tools = await client.listTools();
        res.json({ connected: true, tools });
      } catch (error) {
        res.json({
          connected: true,
          tools: [],
          error: error instanceof Error ? error.message : "Failed to fetch tools",
        });
      }
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch Zapier tools" });
    }
  });

  app.post("/api/zapier-mcp/call", requireAuth, agentLimiter, checkBudget, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const { tool, args } = z.object({
        tool: z.string(),
        args: z.record(z.unknown()).optional(),
      }).parse(req.body);

      const integrations = await storage.getIntegrations(orgId);
      const zapierIntegration = integrations.find(i => i.provider === "zapier-mcp" && i.status === "connected");

      if (!zapierIntegration) {
        return res.status(400).json({ error: "Zapier MCP not connected" });
      }

      const metadata = zapierIntegration.metadataJson as { endpoint?: string } | null;
      if (!metadata?.endpoint) {
        return res.status(400).json({ error: "No endpoint configured" });
      }

      const client = getZapierMcpClient(metadata.endpoint);
      const result = await client.callTool(tool, args || {});

      await storage.createAuditLog({
        orgId,
        userId: req.session.userId || null,
        action: "zapier_mcp_tool_call",
        target: tool,
        detailJson: { args, isError: result.isError },
      });

      res.json(result);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Tool call failed" });
    }
  });

  // ===== ZAPIER WEBHOOK SUBSCRIPTION ROUTES (REST Hooks) =====

  app.post("/api/zapier/hooks/subscribe", validateApiKey, async (req: Request, res: Response) => {
    try {
      const orgId = (req as any).apiKeyOrgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization context" });
      }

      const { event, targetUrl, metadata } = z.object({
        event: z.enum(SUPPORTED_EVENTS as [string, ...string[]]),
        targetUrl: z.string().url(),
        metadata: z.record(z.unknown()).optional(),
      }).parse(req.body);

      const secretKey = generateSecretKey();

      const webhook = await storage.createZapierWebhook({
        orgId,
        event,
        targetUrl,
        isActive: true,
        secretKey,
        metadata: metadata || null,
      });

      await storage.createAuditLog({
        orgId,
        userId: null,
        action: "zapier_webhook_subscribed",
        target: event,
        detailJson: { webhookId: webhook.id, targetUrl },
      });

      res.json({
        id: webhook.id,
        event: webhook.event,
        createdAt: webhook.createdAt,
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.delete("/api/zapier/hooks/:id", validateApiKey, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const orgId = (req as any).apiKeyOrgId;

      const webhook = await storage.getZapierWebhook(id);
      if (!webhook) {
        return res.status(404).json({ error: "Webhook not found" });
      }

      if (webhook.orgId !== orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      await storage.deleteZapierWebhook(id);

      await storage.createAuditLog({
        orgId,
        userId: null,
        action: "zapier_webhook_unsubscribed",
        target: webhook.event,
        detailJson: { webhookId: id },
      });

      res.json({ success: true });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.get("/api/zapier/hooks", validateApiKey, async (req: Request, res: Response) => {
    try {
      const orgId = (req as any).apiKeyOrgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization context" });
      }

      const webhooks = await storage.getZapierWebhooks(orgId);
      res.json(webhooks.map(w => ({
        id: w.id,
        event: w.event,
        targetUrl: w.targetUrl,
        isActive: w.isActive,
        triggerCount: w.triggerCount,
        lastTriggeredAt: w.lastTriggeredAt,
        createdAt: w.createdAt,
      })));
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch webhooks" });
    }
  });

  app.get("/api/zapier/hooks/:id/logs", validateApiKey, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const orgId = (req as any).apiKeyOrgId;
      const limit = parseInt(req.query.limit as string) || 50;

      const webhook = await storage.getZapierWebhook(id);
      if (!webhook || webhook.orgId !== orgId) {
        return res.status(404).json({ error: "Webhook not found" });
      }

      const logs = await storage.getZapierWebhookLogs(id, Math.min(limit, 100));
      res.json(logs);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch webhook logs" });
    }
  });

  // ===== ZAPIER ACTION ROUTES =====

  app.post("/api/zapier/actions/create-project", validateApiKey, async (req: Request, res: Response) => {
    try {
      const orgId = (req as any).apiKeyOrgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization context" });
      }

      const { name } = z.object({
        name: z.string().min(1).max(255),
      }).parse(req.body);

      const project = await storage.createProject({ orgId, name });

      await dispatchEvent(orgId, "project.created", {
        id: project.id,
        name: project.name,
        orgId: project.orgId,
        createdAt: project.createdAt.toISOString(),
      });

      res.json(project);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.post("/api/zapier/actions/run-agent", validateApiKey, async (req: Request, res: Response) => {
    try {
      const orgId = (req as any).apiKeyOrgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization context" });
      }

      const { projectId, goal, provider, model } = z.object({
        projectId: z.string(),
        goal: z.string().min(1),
        provider: z.string().default("openai"),
        model: z.string().default("gpt-4o"),
      }).parse(req.body);

      const project = await storage.getProject(projectId);
      if (!project || project.orgId !== orgId) {
        return res.status(404).json({ error: "Project not found" });
      }

      const agentRun = await storage.createAgentRun({
        projectId,
        status: "queued",
        model,
        provider,
        inputJson: { goal },
        outputJson: null,
        costEstimate: null,
      });

      orchestratorQueue.enqueue({
        runId: agentRun.id,
        projectId,
        orgId,
        goal,
        mode: "default",
      });

      res.json({
        runId: agentRun.id,
        status: "queued",
        projectId,
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.post("/api/zapier/actions/add-memory", validateApiKey, async (req: Request, res: Response) => {
    try {
      const orgId = (req as any).apiKeyOrgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization context" });
      }

      const { projectId, kind, source, content } = z.object({
        projectId: z.string(),
        kind: z.string().default("note"),
        source: z.string().default("zapier"),
        content: z.string().min(1),
      }).parse(req.body);

      const project = await storage.getProject(projectId);
      if (!project || project.orgId !== orgId) {
        return res.status(404).json({ error: "Project not found" });
      }

      const memoryItem = await storage.createMemoryItem({
        projectId,
        kind,
        source,
        content,
      });

      res.json(memoryItem);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.post("/api/zapier/actions/create-roundtable", validateApiKey, async (req: Request, res: Response) => {
    try {
      const orgId = (req as any).apiKeyOrgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization context" });
      }

      const { title, topic, projectId, providers, orchestrationMode, maxTurns } = z.object({
        title: z.string().min(1),
        topic: z.string().optional(),
        projectId: z.string().optional(),
        providers: z.array(z.string()).default(["openai", "anthropic"]),
        orchestrationMode: z.enum(["round_robin", "topic_based", "free_form"]).default("round_robin"),
        maxTurns: z.number().int().min(1).max(100).default(20),
      }).parse(req.body);

      const org = await storage.getOrg(orgId);
      if (!org) {
        return res.status(404).json({ error: "Organization not found" });
      }

      const session = await storage.createRoundtableSession({
        orgId,
        projectId: projectId || null,
        title,
        topic: topic || null,
        status: "active",
        orchestrationMode,
        maxTurns,
        activeProviders: providers,
        createdBy: org.ownerUserId,
      });

      res.json(session);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  // ===== ZAPIER SEARCH ROUTES =====

  app.get("/api/zapier/search/projects", validateApiKey, async (req: Request, res: Response) => {
    try {
      const orgId = (req as any).apiKeyOrgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization context" });
      }

      const projects = await storage.getProjectsByOrg(orgId);
      res.json(projects);
    } catch (error) {
      res.status(500).json({ error: "Failed to search projects" });
    }
  });

  app.get("/api/zapier/search/agent-runs", validateApiKey, async (req: Request, res: Response) => {
    try {
      const orgId = (req as any).apiKeyOrgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization context" });
      }

      const { projectId, status } = z.object({
        projectId: z.string().optional(),
        status: z.string().optional(),
      }).parse(req.query);

      const projects = await storage.getProjectsByOrg(orgId);
      const projectIds = projectId ? [projectId] : projects.map(p => p.id);

      const allRuns = [];
      for (const pid of projectIds) {
        const runs = await storage.getAgentRunsByProject(pid);
        allRuns.push(...runs);
      }

      const filteredRuns = status 
        ? allRuns.filter(r => r.status === status)
        : allRuns;

      res.json(filteredRuns.slice(0, 100));
    } catch (error) {
      res.status(500).json({ error: "Failed to search agent runs" });
    }
  });

  app.get("/api/zapier/search/users", validateApiKey, async (req: Request, res: Response) => {
    try {
      const users = await storage.listAllUsers();
      res.json(users.map(u => ({
        id: u.id,
        email: u.email,
        role: u.role,
        createdAt: u.createdAt,
      })));
    } catch (error) {
      res.status(500).json({ error: "Failed to search users" });
    }
  });

  // ===== ZAPIER SAMPLE DATA ROUTE =====

  app.get("/api/zapier/sample/:event", validateApiKey, async (req: Request, res: Response) => {
    try {
      const { event } = req.params;
      
      if (!SUPPORTED_EVENTS.includes(event as ZapierEventType)) {
        return res.status(400).json({ 
          error: "Invalid event type",
          supportedEvents: SUPPORTED_EVENTS,
        });
      }

      const sampleData = getSampleData(event as ZapierEventType);
      res.json({
        event,
        timestamp: new Date().toISOString(),
        data: sampleData,
      });
    } catch (error) {
      res.status(500).json({ error: "Failed to get sample data" });
    }
  });

  app.get("/api/zapier/events", validateApiKey, async (req: Request, res: Response) => {
    res.json({ events: SUPPORTED_EVENTS });
  });

  // ===== USAGE DASHBOARD ROUTES =====

  app.get("/api/usage", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const days = parseInt(req.query.days as string) || 30;
      const since = new Date();
      since.setDate(since.getDate() - days);

      const records = await storage.getUsageRecords(orgId, since);
      const summary = await storage.getUsageSummary(orgId, since);

      const byProvider: Record<string, { tokens: number; costUsd: number }> = {};
      const dailyMap: Record<string, { tokens: number; cost: number }> = {};

      for (const record of records) {
        if (!byProvider[record.provider]) {
          byProvider[record.provider] = { tokens: 0, costUsd: 0 };
        }
        byProvider[record.provider].tokens += record.inputTokens + record.outputTokens;
        byProvider[record.provider].costUsd += parseFloat(record.estimatedCostUsd || "0");

        const dateKey = new Date(record.createdAt).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
        });
        if (!dailyMap[dateKey]) {
          dailyMap[dateKey] = { tokens: 0, cost: 0 };
        }
        dailyMap[dateKey].tokens += record.inputTokens + record.outputTokens;
        dailyMap[dateKey].cost += parseFloat(record.estimatedCostUsd || "0");
      }

      const dailyUsage = Object.entries(dailyMap)
        .map(([date, data]) => ({ date, ...data }))
        .reverse();

      res.json({
        summary: {
          totalTokens: summary.totalTokens,
          totalCostUsd: summary.totalCostUsd,
          periodDays: days,
        },
        byProvider,
        dailyUsage,
        recentRecords: records.slice(0, 50),
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to get usage" });
    }
  });

  // ===== BUDGET MANAGEMENT ROUTES =====

  app.get("/api/budgets", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const monthlyBudget = await storage.getBudget(orgId, "monthly");
      const dailyBudget = await storage.getBudget(orgId, "daily");

      const budgets = [];
      if (monthlyBudget) {
        budgets.push({
          ...monthlyBudget,
          limitUsd: parseFloat(monthlyBudget.limitUsd),
          spentUsd: parseFloat(monthlyBudget.spentUsd),
        });
      }
      if (dailyBudget) {
        budgets.push({
          ...dailyBudget,
          limitUsd: parseFloat(dailyBudget.limitUsd),
          spentUsd: parseFloat(dailyBudget.spentUsd),
        });
      }

      res.json({ budgets });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to get budgets" });
    }
  });

  app.post("/api/budgets", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const { period, limitUsd } = z.object({
        period: z.enum(["daily", "monthly"]),
        limitUsd: z.number().positive(),
      }).parse(req.body);

      const existingBudget = await storage.getBudget(orgId, period);

      if (existingBudget) {
        await storage.updateBudgetLimit(existingBudget.id, limitUsd.toString());
        res.json({ success: true, updated: true });
      } else {
        const budget = await storage.createBudget({
          orgId,
          period,
          limitUsd: limitUsd.toString(),
          spentUsd: "0",
          updatedAt: new Date(),
        });
        res.json({ success: true, budget });
      }

      await storage.createAuditLog({
        orgId,
        userId: req.session.userId || null,
        action: "budget_updated",
        target: period,
        detailJson: { limitUsd },
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to save budget" });
    }
  });

  // ===== CIRCUIT BREAKER STATUS ROUTES =====

  app.get("/api/circuits", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const status = retryService.getCircuitStatus();
      res.json({ circuits: status });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to get circuit status" });
    }
  });

  app.post("/api/circuits/reset", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const user = await storage.getUser(req.session.userId!);
      if (!user || !["owner", "admin"].includes(user.role || "")) {
        return res.status(403).json({ error: "Admin access required" });
      }

      const validProviders = ["openai", "anthropic", "google", "gemini", "perplexity", "xai"];
      const { provider } = req.body;
      
      if (provider && !validProviders.includes(provider.toLowerCase())) {
        return res.status(400).json({ error: `Invalid provider. Valid: ${validProviders.join(", ")}` });
      }

      if (provider) {
        retryService.resetCircuit(provider.toLowerCase());
      } else {
        retryService.resetAllCircuits();
      }

      const orgId = req.session.orgId;
      if (orgId) {
        await storage.createAuditLog({
          orgId,
          userId: req.session.userId || null,
          action: "circuit_reset",
          target: provider || "all",
          detailJson: {},
        });
      }

      res.json({ success: true, provider: provider || "all" });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to reset circuit" });
    }
  });

  // ===== GITHUB INTEGRATION ROUTES =====

  app.get("/api/github/user", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { getAuthenticatedUser } = await import("./services/githubClient");
      const user = await getAuthenticatedUser();
      res.json({ user });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "GitHub not connected" });
    }
  });

  app.get("/api/github/repos", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { listRepositories } = await import("./services/githubClient");
      const repos = await listRepositories();
      res.json({ repos: repos.map(r => ({ name: r.name, fullName: r.full_name, url: r.html_url, private: r.private })) });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "GitHub not connected" });
    }
  });

  app.post("/api/github/repo", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { name, description, isPrivate } = z.object({
        name: z.string().min(1).max(100),
        description: z.string().optional(),
        isPrivate: z.boolean().optional(),
      }).parse(req.body);

      const { createRepository } = await import("./services/githubClient");
      const repo = await createRepository(name, {
        description,
        private: isPrivate,
        autoInit: true,
      });

      res.json({ 
        success: true, 
        repo: { 
          name: repo.name, 
          fullName: repo.full_name, 
          url: repo.html_url,
          cloneUrl: repo.clone_url,
        } 
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create repository" });
    }
  });

  app.post("/api/github/file", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { owner, repo, path, content, message, branch } = z.object({
        owner: z.string(),
        repo: z.string(),
        path: z.string(),
        content: z.string(),
        message: z.string(),
        branch: z.string().optional(),
      }).parse(req.body);

      const { createOrUpdateFile, getFileContent } = await import("./services/githubClient");
      
      // Check if file exists to get SHA for update
      const existing = await getFileContent(owner, repo, path, branch);
      const sha = existing && 'sha' in existing ? existing.sha : undefined;

      const result = await createOrUpdateFile(owner, repo, path, content, message, branch || "main", sha);
      res.json({ success: true, commit: result.commit });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create file" });
    }
  });

  app.post("/api/github/branch", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { owner, repo, branchName, fromRef } = z.object({
        owner: z.string(),
        repo: z.string(),
        branchName: z.string(),
        fromRef: z.string().optional(),
      }).parse(req.body);

      const { createBranch } = await import("./services/githubClient");
      const result = await createBranch(owner, repo, branchName, fromRef || "main");
      res.json({ success: true, ref: result.ref });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create branch" });
    }
  });

  app.post("/api/github/pull-request", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { owner, repo, title, body, head, base } = z.object({
        owner: z.string(),
        repo: z.string(),
        title: z.string(),
        body: z.string(),
        head: z.string(),
        base: z.string().optional(),
      }).parse(req.body);

      const { createPullRequest } = await import("./services/githubClient");
      const pr = await createPullRequest(owner, repo, title, body, head, base || "main");
      res.json({ success: true, pullRequest: { number: pr.number, url: pr.html_url, title: pr.title } });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create pull request" });
    }
  });

  // ===== GOOGLE DRIVE INTEGRATION ROUTES =====

  app.get("/api/google-drive/status", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { isGoogleDriveConnected } = await import("./services/googleDriveClient");
      const connected = await isGoogleDriveConnected();
      res.json({ connected });
    } catch (error) {
      res.json({ connected: false });
    }
  });

  app.get("/api/google-drive/files", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { folderId, pageSize } = z.object({
        folderId: z.string().optional(),
        pageSize: z.coerce.number().optional().default(20),
      }).parse(req.query);

      const { listDriveFiles } = await import("./services/googleDriveClient");
      const files = await listDriveFiles(folderId, pageSize);
      res.json({ files });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list files" });
    }
  });

  app.get("/api/google-drive/file/:fileId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { fileId } = req.params;
      const { getDriveFile } = await import("./services/googleDriveClient");
      const file = await getDriveFile(fileId);
      res.json({ file });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get file" });
    }
  });

  app.get("/api/google-drive/quota", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { getDriveStorageQuota } = await import("./services/googleDriveClient");
      const quota = await getDriveStorageQuota();
      res.json({ quota });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get quota" });
    }
  });

  app.post("/api/google-drive/folder", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { name, parentFolderId } = z.object({
        name: z.string().min(1),
        parentFolderId: z.string().optional(),
      }).parse(req.body);

      const { createDriveFolder } = await import("./services/googleDriveClient");
      const folder = await createDriveFolder(name, parentFolderId);
      res.json({ folder });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create folder" });
    }
  });

  app.delete("/api/google-drive/file/:fileId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { fileId } = req.params;
      const { deleteDriveFile } = await import("./services/googleDriveClient");
      await deleteDriveFile(fileId);
      res.json({ success: true });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to delete file" });
    }
  });

  // ===== ONEDRIVE INTEGRATION ROUTES =====

  app.get("/api/onedrive/status", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { isOneDriveConnected } = await import("./services/oneDriveClient");
      const connected = await isOneDriveConnected();
      res.json({ connected });
    } catch (error) {
      res.json({ connected: false });
    }
  });

  app.get("/api/onedrive/user", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { getOneDriveUser } = await import("./services/oneDriveClient");
      const user = await getOneDriveUser();
      res.json({ user });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "OneDrive not connected" });
    }
  });

  app.get("/api/onedrive/files", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { folderId, pageSize } = z.object({
        folderId: z.string().optional(),
        pageSize: z.coerce.number().optional().default(20),
      }).parse(req.query);

      const { listOneDriveFiles } = await import("./services/oneDriveClient");
      const files = await listOneDriveFiles(folderId, pageSize);
      res.json({ files });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list files" });
    }
  });

  app.get("/api/onedrive/file/:fileId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { fileId } = req.params;
      const { getOneDriveFile } = await import("./services/oneDriveClient");
      const file = await getOneDriveFile(fileId);
      res.json({ file });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get file" });
    }
  });

  app.get("/api/onedrive/quota", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { getOneDriveStorageQuota } = await import("./services/oneDriveClient");
      const quota = await getOneDriveStorageQuota();
      res.json({ quota });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get quota" });
    }
  });

  app.post("/api/onedrive/folder", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { name, parentFolderId } = z.object({
        name: z.string().min(1),
        parentFolderId: z.string().optional(),
      }).parse(req.body);

      const { createOneDriveFolder } = await import("./services/oneDriveClient");
      const folder = await createOneDriveFolder(name, parentFolderId);
      res.json({ folder });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create folder" });
    }
  });

  app.delete("/api/onedrive/file/:fileId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { fileId } = req.params;
      const { deleteOneDriveFile } = await import("./services/oneDriveClient");
      await deleteOneDriveFile(fileId);
      res.json({ success: true });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to delete file" });
    }
  });

  // ===== NOTION ROUTES =====

  app.get("/api/notion/status", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { isNotionConnected } = await import("./services/notionClient");
      const connected = await isNotionConnected();
      res.json({ connected });
    } catch (error) {
      res.json({ connected: false });
    }
  });

  app.get("/api/notion/user", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { getNotionUser } = await import("./services/notionClient");
      const user = await getNotionUser();
      res.json({ user });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get user" });
    }
  });

  app.get("/api/notion/pages", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { listNotionPages } = await import("./services/notionClient");
      const pageSize = parseInt(req.query.pageSize as string) || 20;
      const pages = await listNotionPages(pageSize);
      res.json({ pages });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list pages" });
    }
  });

  app.get("/api/notion/databases", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { listNotionDatabases } = await import("./services/notionClient");
      const databases = await listNotionDatabases();
      res.json({ databases });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list databases" });
    }
  });

  app.get("/api/notion/page/:pageId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { pageId } = req.params;
      const { getNotionPage, getNotionPageContent } = await import("./services/notionClient");
      const [page, content] = await Promise.all([
        getNotionPage(pageId),
        getNotionPageContent(pageId),
      ]);
      res.json({ page, content });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get page" });
    }
  });

  app.get("/api/notion/database/:databaseId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { databaseId } = req.params;
      const { getNotionDatabase, queryNotionDatabase } = await import("./services/notionClient");
      const [database, items] = await Promise.all([
        getNotionDatabase(databaseId),
        queryNotionDatabase(databaseId),
      ]);
      res.json({ database, items });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get database" });
    }
  });

  app.post("/api/notion/page", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { parentId, properties, children } = z.object({
        parentId: z.string().min(1),
        properties: z.record(z.any()),
        children: z.array(z.any()).optional(),
      }).parse(req.body);

      const { createNotionPage } = await import("./services/notionClient");
      const page = await createNotionPage(parentId, properties, children);
      res.json({ page });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create page" });
    }
  });

  app.patch("/api/notion/page/:pageId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { pageId } = req.params;
      const { properties } = z.object({
        properties: z.record(z.any()),
      }).parse(req.body);

      const { updateNotionPage } = await import("./services/notionClient");
      const page = await updateNotionPage(pageId, properties);
      res.json({ page });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to update page" });
    }
  });

  app.delete("/api/notion/page/:pageId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { pageId } = req.params;
      const { archiveNotionPage } = await import("./services/notionClient");
      const page = await archiveNotionPage(pageId);
      res.json({ page });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to archive page" });
    }
  });

  // ===== STRIPE ROUTES =====

  app.get("/api/stripe/status", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { isStripeConnected } = await import("./services/stripeClient");
      const connected = await isStripeConnected();
      res.json({ connected });
    } catch (error) {
      res.json({ connected: false });
    }
  });

  app.get("/api/stripe/publishable-key", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { getStripePublishableKey } = await import("./services/stripeClient");
      const publishableKey = await getStripePublishableKey();
      res.json({ publishableKey });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get publishable key" });
    }
  });

  app.get("/api/stripe/products", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { listStripeProducts } = await import("./services/stripeClient");
      const products = await listStripeProducts();
      res.json({ products });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list products" });
    }
  });

  app.get("/api/stripe/prices", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { listStripePrices } = await import("./services/stripeClient");
      const productId = req.query.productId as string | undefined;
      const prices = await listStripePrices(productId);
      res.json({ prices });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list prices" });
    }
  });

  app.post("/api/stripe/checkout", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { priceId, customerId, mode } = z.object({
        priceId: z.string().min(1),
        customerId: z.string().min(1),
        mode: z.enum(["subscription", "payment"]).default("subscription"),
      }).parse(req.body);

      const { createStripeCheckoutSession } = await import("./services/stripeClient");
      const baseUrl = process.env.APP_ORIGIN || `http://localhost:5000`;
      const session = await createStripeCheckoutSession(
        customerId,
        priceId,
        `${baseUrl}/checkout/success`,
        `${baseUrl}/checkout/cancel`,
        mode
      );
      res.json({ url: session.url, sessionId: session.id });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create checkout session" });
    }
  });

  app.post("/api/stripe/customer", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { email, metadata } = z.object({
        email: z.string().email(),
        metadata: z.record(z.string()).optional(),
      }).parse(req.body);

      const { createStripeCustomer } = await import("./services/stripeClient");
      const customer = await createStripeCustomer(email, metadata);
      res.json({ customer });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create customer" });
    }
  });

  app.post("/api/stripe/portal", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { customerId } = z.object({
        customerId: z.string().min(1),
      }).parse(req.body);

      const { createStripePortalSession } = await import("./services/stripeClient");
      const baseUrl = process.env.APP_ORIGIN || `http://localhost:5000`;
      const session = await createStripePortalSession(customerId, `${baseUrl}/settings`);
      res.json({ url: session.url });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create portal session" });
    }
  });

  app.get("/api/stripe/subscription/:subscriptionId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { subscriptionId } = req.params;
      const { getStripeSubscription } = await import("./services/stripeClient");
      const subscription = await getStripeSubscription(subscriptionId);
      res.json({ subscription });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get subscription" });
    }
  });

  app.delete("/api/stripe/subscription/:subscriptionId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { subscriptionId } = req.params;
      const { cancelStripeSubscription } = await import("./services/stripeClient");
      const subscription = await cancelStripeSubscription(subscriptionId);
      res.json({ subscription });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to cancel subscription" });
    }
  });

  app.post("/api/stripe/product", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { name, description, metadata } = z.object({
        name: z.string().min(1),
        description: z.string().optional(),
        metadata: z.record(z.string()).optional(),
      }).parse(req.body);

      const { createStripeProduct } = await import("./services/stripeClient");
      const product = await createStripeProduct(name, description, metadata);
      res.json({ product });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create product" });
    }
  });

  app.post("/api/stripe/price", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { productId, unitAmount, currency, recurring } = z.object({
        productId: z.string().min(1),
        unitAmount: z.number().int().positive(),
        currency: z.string().default('usd'),
        recurring: z.object({ interval: z.enum(['month', 'year']) }).optional(),
      }).parse(req.body);

      const { createStripePrice } = await import("./services/stripeClient");
      const price = await createStripePrice(productId, unitAmount, currency, recurring);
      res.json({ price });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create price" });
    }
  });

  // ===== WORLD ANVIL ROUTES =====

  app.get("/api/world-anvil/status", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { isWorldAnvilConnected } = await import("./services/worldAnvilClient");
      const connected = await isWorldAnvilConnected();
      res.json({ connected });
    } catch (error) {
      res.json({ connected: false });
    }
  });

  app.get("/api/world-anvil/user", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { getWorldAnvilUser } = await import("./services/worldAnvilClient");
      const user = await getWorldAnvilUser();
      res.json({ user });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get user" });
    }
  });

  app.get("/api/world-anvil/worlds", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { listWorldAnvilWorlds } = await import("./services/worldAnvilClient");
      const worlds = await listWorldAnvilWorlds();
      res.json({ worlds });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list worlds" });
    }
  });

  app.get("/api/world-anvil/world/:worldId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { worldId } = req.params;
      const { getWorld } = await import("./services/worldAnvilClient");
      const world = await getWorld(worldId);
      res.json({ world });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get world" });
    }
  });

  app.get("/api/world-anvil/world/:worldId/articles", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { worldId } = req.params;
      const limit = parseInt(req.query.limit as string) || 25;
      const offset = parseInt(req.query.offset as string) || 0;
      const { listWorldArticles } = await import("./services/worldAnvilClient");
      const articles = await listWorldArticles(worldId, limit, offset);
      res.json({ articles });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list articles" });
    }
  });

  app.get("/api/world-anvil/article/:articleId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { articleId } = req.params;
      const { getArticle } = await import("./services/worldAnvilClient");
      const article = await getArticle(articleId);
      res.json({ article });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get article" });
    }
  });

  app.get("/api/world-anvil/world/:worldId/categories", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { worldId } = req.params;
      const { listWorldCategories } = await import("./services/worldAnvilClient");
      const categories = await listWorldCategories(worldId);
      res.json({ categories });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list categories" });
    }
  });

  app.get("/api/world-anvil/world/:worldId/maps", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { worldId } = req.params;
      const { listWorldMaps } = await import("./services/worldAnvilClient");
      const maps = await listWorldMaps(worldId);
      res.json({ maps });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list maps" });
    }
  });

  app.get("/api/world-anvil/world/:worldId/timelines", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { worldId } = req.params;
      const { listWorldTimelines } = await import("./services/worldAnvilClient");
      const timelines = await listWorldTimelines(worldId);
      res.json({ timelines });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list timelines" });
    }
  });

  app.get("/api/world-anvil/timeline/:timelineId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { timelineId } = req.params;
      const { getTimeline } = await import("./services/worldAnvilClient");
      const timeline = await getTimeline(timelineId);
      res.json({ timeline });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to get timeline" });
    }
  });

  app.get("/api/world-anvil/world/:worldId/search", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { worldId } = req.params;
      const query = req.query.q as string;
      if (!query) {
        return res.status(400).json({ error: "Search query required" });
      }
      const { searchArticles } = await import("./services/worldAnvilClient");
      const results = await searchArticles(worldId, query);
      res.json({ results });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to search articles" });
    }
  });

  // ===== WORKFLOW ROUTES =====

  app.get("/api/workflows", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }
      const workflows = await storage.getWorkflows(orgId);
      res.json(workflows);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch workflows" });
    }
  });

  app.get("/api/workflows/:id", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const workflow = await storage.getWorkflow(id);
      if (!workflow) {
        return res.status(404).json({ error: "Workflow not found" });
      }
      if (workflow.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }
      res.json(workflow);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch workflow" });
    }
  });

  app.post("/api/workflows", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      const userId = req.session.userId;
      if (!orgId || !userId) {
        return res.status(400).json({ error: "No organization or user context" });
      }

      const { name, description, trigger, steps, status } = z.object({
        name: z.string().min(1),
        description: z.string().optional(),
        trigger: z.enum(["manual", "schedule", "webhook"]).default("manual"),
        steps: z.array(z.object({
          id: z.string(),
          provider: z.string(),
          prompt: z.string(),
        })),
        status: z.enum(["active", "paused", "draft"]).default("draft"),
      }).parse(req.body);

      const workflow = await storage.createWorkflow({
        orgId,
        name,
        description,
        trigger,
        steps,
        status,
        createdBy: userId,
      });

      await storage.createAuditLog({
        orgId,
        userId,
        action: "workflow_created",
        target: workflow.id,
        detailJson: { name, trigger },
      });

      res.json(workflow);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.put("/api/workflows/:id", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const orgId = req.session.orgId;
      const userId = req.session.userId;

      const workflow = await storage.getWorkflow(id);
      if (!workflow) {
        return res.status(404).json({ error: "Workflow not found" });
      }
      if (workflow.orgId !== orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      const updates = z.object({
        name: z.string().min(1).optional(),
        description: z.string().optional(),
        trigger: z.enum(["manual", "schedule", "webhook"]).optional(),
        steps: z.array(z.object({
          id: z.string(),
          provider: z.string(),
          prompt: z.string(),
        })).optional(),
        status: z.enum(["active", "paused", "draft"]).optional(),
      }).parse(req.body);

      const updated = await storage.updateWorkflow(id, updates);

      if (userId && orgId) {
        await storage.createAuditLog({
          orgId,
          userId,
          action: "workflow_updated",
          target: id,
          detailJson: updates,
        });
      }

      res.json(updated);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  app.delete("/api/workflows/:id", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const orgId = req.session.orgId;
      const userId = req.session.userId;

      const workflow = await storage.getWorkflow(id);
      if (!workflow) {
        return res.status(404).json({ error: "Workflow not found" });
      }
      if (workflow.orgId !== orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      await storage.deleteWorkflow(id);

      if (userId && orgId) {
        await storage.createAuditLog({
          orgId,
          userId,
          action: "workflow_deleted",
          target: id,
          detailJson: { name: workflow.name },
        });
      }

      res.json({ success: true });
    } catch (error) {
      res.status(500).json({ error: "Failed to delete workflow" });
    }
  });

  app.post("/api/workflows/:id/run", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const orgId = req.session.orgId;
      const userId = req.session.userId;

      const workflow = await storage.getWorkflow(id);
      if (!workflow) {
        return res.status(404).json({ error: "Workflow not found" });
      }
      if (workflow.orgId !== orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      const run = await storage.createWorkflowRun({
        workflowId: id,
        status: "running",
        stepResults: null,
        completedAt: null,
        error: null,
      });

      if (userId && orgId) {
        await storage.createAuditLog({
          orgId,
          userId,
          action: "workflow_run_started",
          target: id,
          detailJson: { runId: run.id },
        });
      }

      res.json(run);
    } catch (error) {
      res.status(500).json({ error: "Failed to run workflow" });
    }
  });

  // ===== ROUNDTABLE ROUTES =====

  // Get available AI providers
  app.get("/api/roundtable/providers", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { AI_CONFIGS } = await import("./services/roundtableCoordinator");
      const providers = Object.entries(AI_CONFIGS).map(([id, config]) => ({
        id,
        name: config.name,
        role: config.role,
        signOff: config.signOff,
      }));
      res.json(providers);
    } catch (error) {
      res.status(500).json({ error: "Failed to get providers" });
    }
  });

  // Create a new roundtable session
  app.post("/api/roundtable/sessions", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const { AI_CONFIGS } = await import("./services/roundtableCoordinator");
      const validProviders = Object.keys(AI_CONFIGS);

      const { title, topic, activeProviders, orchestrationMode, maxTurns, projectId } = z.object({
        title: z.string().min(1),
        topic: z.string().optional(),
        activeProviders: z.array(z.string()).min(1).refine(
          (providers) => providers.every(p => validProviders.includes(p)),
          { message: "Invalid provider specified" }
        ),
        orchestrationMode: z.enum(["round_robin", "topic_based", "free_form"]).default("round_robin"),
        maxTurns: z.number().min(1).max(100).default(20),
        projectId: z.string().optional(),
      }).parse(req.body);

      if (projectId) {
        const project = await storage.getProject(projectId);
        if (!project || project.orgId !== orgId) {
          return res.status(403).json({ error: "Unauthorized access to project" });
        }
      }

      const userId = req.session.userId;
      if (!userId) {
        return res.status(401).json({ error: "Not authenticated" });
      }

      const session = await storage.createRoundtableSession({
        orgId,
        projectId: projectId || null,
        title,
        topic: topic || null,
        activeProviders,
        orchestrationMode,
        maxTurns,
        status: "active",
        createdBy: userId,
      });

      await storage.createAuditLog({
        orgId,
        userId: req.session.userId || null,
        action: "roundtable_session_created",
        target: session.id,
        detailJson: { title, providers: activeProviders },
      });

      res.json(session);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  // List roundtable sessions
  app.get("/api/roundtable/sessions", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const sessions = await storage.getRoundtableSessions(orgId);
      res.json(sessions);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch sessions" });
    }
  });

  // Get a specific session with messages
  app.get("/api/roundtable/sessions/:id", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const session = await storage.getRoundtableSession(id);
      
      if (!session) {
        return res.status(404).json({ error: "Session not found" });
      }

      if (session.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      const messages = await storage.getRoundtableMessages(id);
      res.json({ ...session, messages });
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch session" });
    }
  });

  // Add a user message to a session
  app.post("/api/roundtable/sessions/:id/message", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const { content } = z.object({
        content: z.string().min(1).max(10000),
      }).parse(req.body);

      const session = await storage.getRoundtableSession(id);
      if (!session) {
        return res.status(404).json({ error: "Session not found" });
      }

      if (session.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      if (session.status !== "active") {
        return res.status(400).json({ error: "Session is not active" });
      }

      const sequenceNumber = await storage.getNextSequenceNumber(id);
      const message = await storage.createRoundtableMessage({
        sessionId: id,
        senderType: "user",
        senderId: req.session.userId || null,
        provider: null,
        model: null,
        content,
        signature: null,
        sequenceNumber,
        tokensUsed: null,
        responseTimeMs: null,
        metadata: null,
      });

      dispatchEvent(session.orgId, "roundtable.message", {
        id: message.id,
        sessionId: message.sessionId,
        senderType: message.senderType,
        provider: message.provider,
        model: message.model,
        content: message.content,
        sequenceNumber: message.sequenceNumber,
        createdAt: message.createdAt.toISOString(),
      }).catch(err => console.error("[Zapier] Failed to dispatch roundtable.message:", err));

      res.json(message);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  // Trigger a single AI's turn
  app.post("/api/roundtable/sessions/:id/ai-turn", requireAuth, agentLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const { provider } = z.object({
        provider: z.string(),
      }).parse(req.body);

      const session = await storage.getRoundtableSession(id);
      if (!session) {
        return res.status(404).json({ error: "Session not found" });
      }

      if (session.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      if (session.status !== "active") {
        return res.status(400).json({ error: "Session is not active" });
      }

      const userId = req.session.userId;
      if (!userId) {
        return res.status(401).json({ error: "Not authenticated" });
      }

      const { processAITurn } = await import("./services/roundtableCoordinator");
      const message = await processAITurn(id, provider, userId);

      res.json(message);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "AI turn failed" });
    }
  });

  // Run a full round of all active AIs
  app.post("/api/roundtable/sessions/:id/round", requireAuth, agentLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;

      const session = await storage.getRoundtableSession(id);
      if (!session) {
        return res.status(404).json({ error: "Session not found" });
      }

      if (session.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      if (session.status !== "active") {
        return res.status(400).json({ error: "Session is not active" });
      }

      const userId = req.session.userId;
      if (!userId) {
        return res.status(401).json({ error: "Not authenticated" });
      }

      const { runRoundtableRound } = await import("./services/roundtableCoordinator");
      const messages = await runRoundtableRound(id, userId);

      res.json(messages);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Round failed" });
    }
  });

  // Update session status (pause/resume/complete)
  app.patch("/api/roundtable/sessions/:id", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const { status } = z.object({
        status: z.enum(["active", "paused", "completed"]),
      }).parse(req.body);

      const session = await storage.getRoundtableSession(id);
      if (!session) {
        return res.status(404).json({ error: "Session not found" });
      }

      if (session.orgId !== req.session.orgId) {
        return res.status(403).json({ error: "Unauthorized" });
      }

      const updated = await storage.updateRoundtableSession(id, { status });
      res.json(updated);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Invalid request" });
    }
  });

  // ===== AI WORKBENCH ROUTES =====
  
  // Multi-panel AI chat endpoint (allows guest access for demo)
  app.post("/api/workbench/chat", agentLimiter, async (req: Request, res: Response) => {
    try {
      const { provider, model, message, context, mode } = z.object({
        provider: z.string().min(1),
        model: z.string().min(1),
        message: z.string().min(1),
        context: z.string().optional(),
        mode: z.enum(["consensus", "expert", "debate", "synthesis"]).optional(),
      }).parse(req.body);

      // Use session context if available, otherwise use guest defaults
      const orgId = req.session.orgId || "guest-org";
      const userId = req.session.userId || "guest-user";

      const adapter = getProviderAdapter(provider);
      const startTime = Date.now();
      
      const systemPrompt = context 
        ? `You are participating in a multi-AI collaboration session. Context: ${context}. Mode: ${mode || 'synthesis'}. Provide your unique perspective based on your model's strengths.`
        : "You are a helpful AI assistant participating in a collaborative discussion.";
      
      const fullPrompt = `${systemPrompt}\n\nUser message: ${message}`;
      
      const response = await adapter.call(fullPrompt, model);
      const responseTime = Date.now() - startTime;

      if (!response.success) {
        return res.status(500).json({ error: response.error || "AI call failed" });
      }

      const tokensUsed = (response.usage?.inputTokens || 0) + (response.usage?.outputTokens || 0);

      // Track usage only for authenticated users (skip for guests)
      const isGuest = orgId === "guest-org";
      if (!isGuest && req.session.orgId && req.session.userId) {
        try {
          await storage.createUsageRecord({
            orgId,
            userId,
            provider,
            model,
            inputTokens: response.usage?.inputTokens || 0,
            outputTokens: response.usage?.outputTokens || 0,
            estimatedCostUsd: response.usage?.costEstimate || "0",
            metadata: { type: "workbench", mode: mode || "synthesis" },
          });
        } catch (usageError) {
          // Log but don't fail the request if usage tracking fails
          console.error("Failed to track usage:", usageError);
        }
      }

      res.json({
        content: response.content,
        provider,
        model,
        tokensUsed,
        responseTimeMs: responseTime,
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Chat failed" });
    }
  });

  // Synthesize multi-panel outputs (allows guest access for demo)
  app.post("/api/workbench/synthesize", agentLimiter, async (req: Request, res: Response) => {
    try {
      const { goal, mode, contributions } = z.object({
        goal: z.string().min(1),
        mode: z.enum(["consensus", "expert", "debate", "synthesis"]),
        contributions: z.string().min(1),
      }).parse(req.body);

      // Use session context if available, otherwise use guest defaults
      const orgId = req.session.orgId || "guest-org";
      const userId = req.session.userId || "guest-user";

      const modeInstructions: Record<string, string> = {
        consensus: "Identify areas of agreement among the AI contributions and highlight the consensus view. Note any minor disagreements.",
        expert: "Combine the expert insights from each AI, giving appropriate weight to each domain of expertise. Create a comprehensive expert panel summary.",
        debate: "Analyze the different positions presented, evaluate the strength of each argument, and provide a balanced assessment of the debate outcomes.",
        synthesis: "Merge all insights into a unified, coherent output. Eliminate redundancy while preserving unique perspectives. Create actionable recommendations.",
      };

      const synthesisPrompt = `You are synthesizing outputs from multiple AI agents working on a collaborative task.

MAIN GOAL: ${goal}

COLLABORATION MODE: ${mode}
${modeInstructions[mode]}

AI CONTRIBUTIONS:
${contributions}

Please provide:
1. A synthesized summary that combines all perspectives
2. Key insights from each contributor
3. A list of actionable items extracted from the discussion (as a JSON array in a section marked ACTION_ITEMS:)

Format the action items section like this:
ACTION_ITEMS:
["item 1", "item 2", "item 3"]`;

      // Use Anthropic for synthesis by default as it's good at following instructions
      const adapter = getProviderAdapter("anthropic");
      const response = await adapter.call(synthesisPrompt, "claude-sonnet-4-20250514");

      if (!response.success) {
        return res.status(500).json({ error: response.error || "Synthesis failed" });
      }

      // Extract action items from response
      let actionItems: string[] = [];
      const content = response.content || "";
      const actionMatch = content.match(/ACTION_ITEMS:\s*\n?\[([^\]]+)\]/);
      if (actionMatch) {
        try {
          actionItems = JSON.parse(`[${actionMatch[1]}]`);
        } catch {
          // Try to extract items manually
          const items = actionMatch[1].split(",").map(s => s.trim().replace(/^["']|["']$/g, ''));
          actionItems = items.filter(i => i.length > 0);
        }
      }

      // Remove the action items section from main synthesis for cleaner output
      const synthesis = content.replace(/ACTION_ITEMS:\s*\n?\[[^\]]+\]/, '').trim();

      // Track usage only for authenticated users (skip for guests)
      const isGuest = orgId === "guest-org";
      if (!isGuest && req.session.orgId && req.session.userId) {
        try {
          await storage.createUsageRecord({
            orgId,
            userId,
            provider: "anthropic",
            model: "claude-sonnet-4-20250514",
            inputTokens: response.usage?.inputTokens || 0,
            outputTokens: response.usage?.outputTokens || 0,
            estimatedCostUsd: response.usage?.costEstimate || "0",
            metadata: { type: "workbench_synthesis", mode },
          });
        } catch (usageError) {
          console.error("Failed to track synthesis usage:", usageError);
        }
      }

      res.json({
        synthesis,
        actionItems,
        tokensUsed: (response.usage?.inputTokens || 0) + (response.usage?.outputTokens || 0),
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Synthesis failed" });
    }
  });

  // ===== CODE IMPROVEMENT ROUTES =====

  // Analyze code and get improvement suggestions
  app.post("/api/code-improvement/analyze", requireAuth, agentLimiter, async (req: Request, res: Response) => {
    try {
      const { filePath, content, provider, improvementType } = z.object({
        filePath: z.string().min(1),
        content: z.string().min(1),
        provider: z.enum(["openai", "anthropic", "xai", "perplexity", "google"]).optional(),
        improvementType: z.enum(["refactor", "optimize", "security", "documentation", "all"]).optional(),
      }).parse(req.body);

      const orgId = req.session.orgId;
      const userId = req.session.userId;
      if (!orgId || !userId) {
        return res.status(400).json({ error: "No organization or user context" });
      }

      const { analyzeCode } = await import("./services/codeImprovement");
      const { analysis, result } = await analyzeCode({
        orgId,
        userId,
        filePath,
        content,
        provider,
        improvementType,
      });

      await storage.createAuditLog({
        orgId,
        userId,
        action: "code_analysis",
        target: filePath,
        detailJson: { analysisId: analysis.id, suggestionsCount: result.suggestions.length },
      });

      res.json({ analysis, result });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Analysis failed" });
    }
  });

  // Generate improvement proposal from a suggestion
  app.post("/api/code-improvement/generate", requireAuth, agentLimiter, async (req: Request, res: Response) => {
    try {
      const { analysisId, suggestionIndex, provider } = z.object({
        analysisId: z.number(),
        suggestionIndex: z.number(),
        provider: z.enum(["openai", "anthropic", "xai", "perplexity", "google"]).optional(),
      }).parse(req.body);

      const userId = req.session.userId;
      const orgId = req.session.orgId;
      if (!userId || !orgId) {
        return res.status(401).json({ error: "Not authenticated or no organization context" });
      }

      const { generateImprovement } = await import("./services/codeImprovement");
      const { suggestion, proposal } = await generateImprovement(userId, orgId, analysisId, suggestionIndex, provider);

      res.json({ suggestion, proposal });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Generation failed" });
    }
  });

  // Get proposals for the org
  app.get("/api/code-improvement/proposals", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization context" });
      }

      const { status } = z.object({
        status: z.enum(["pending", "approved", "rejected", "applied"]).optional(),
      }).parse(req.query);

      const proposals = await storage.getAgentProposalsByOrg(orgId, status);
      res.json(proposals);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch proposals" });
    }
  });

  // Get single proposal with details
  app.get("/api/code-improvement/proposals/:id", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const id = parseInt(req.params.id);
      const orgId = req.session.orgId;
      if (isNaN(id)) {
        return res.status(400).json({ error: "Invalid proposal ID" });
      }
      if (!orgId) {
        return res.status(400).json({ error: "No organization context" });
      }

      const proposal = await storage.getAgentProposal(id);
      if (!proposal) {
        return res.status(404).json({ error: "Proposal not found" });
      }

      if (proposal.orgId !== orgId) {
        return res.status(403).json({ error: "Access denied" });
      }

      res.json(proposal);
    } catch (error) {
      res.status(500).json({ error: "Failed to fetch proposal" });
    }
  });

  // Approve a proposal
  app.post("/api/code-improvement/proposals/:id/approve", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const id = parseInt(req.params.id);
      const userId = req.session.userId;
      const orgId = req.session.orgId;
      if (!userId || !orgId) {
        return res.status(401).json({ error: "Not authenticated or no organization context" });
      }

      const { approveProposal } = await import("./services/codeImprovement");
      const proposal = await approveProposal(id, orgId, userId);

      await storage.createAuditLog({
        orgId,
        userId,
        action: "proposal_approved",
        target: proposal.filePath,
        detailJson: { proposalId: id },
      });

      res.json(proposal);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Approval failed" });
    }
  });

  // Reject a proposal
  app.post("/api/code-improvement/proposals/:id/reject", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const id = parseInt(req.params.id);
      const userId = req.session.userId;
      const orgId = req.session.orgId;
      if (!userId || !orgId) {
        return res.status(401).json({ error: "Not authenticated or no organization context" });
      }

      const { rejectProposal } = await import("./services/codeImprovement");
      const proposal = await rejectProposal(id, orgId, userId);

      await storage.createAuditLog({
        orgId,
        userId,
        action: "proposal_rejected",
        target: proposal.filePath,
        detailJson: { proposalId: id },
      });

      res.json(proposal);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Rejection failed" });
    }
  });

  // Apply an approved proposal
  app.post("/api/code-improvement/proposals/:id/apply", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const id = parseInt(req.params.id);
      const userId = req.session.userId;
      const orgId = req.session.orgId;
      if (!userId || !orgId) {
        return res.status(401).json({ error: "Not authenticated or no organization context" });
      }

      const { applyProposal } = await import("./services/codeImprovement");
      const proposal = await applyProposal(id, orgId);

      await storage.createAuditLog({
        orgId,
        userId,
        action: "proposal_applied",
        target: proposal.filePath,
        detailJson: { proposalId: id },
      });

      res.json(proposal);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Apply failed" });
    }
  });

  // ===== CODE ASSISTANT ROUTES =====

  app.post("/api/code-assistant/generate", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { prompt, provider, model, conversationHistory } = z.object({
        prompt: z.string().min(1, "Prompt is required").max(10000),
        provider: z.enum(["openai", "anthropic", "xai", "perplexity", "google", "huggingface"]),
        model: z.string().optional(),
        conversationHistory: z.array(z.object({
          role: z.enum(["user", "assistant"]),
          content: z.string(),
        })).optional(),
      }).parse(req.body);

      const adapter = getProviderAdapter(provider);
      
      let fullPrompt = prompt;
      if (conversationHistory && conversationHistory.length > 0) {
        const historyText = conversationHistory
          .map(msg => `${msg.role === "user" ? "User" : "Assistant"}: ${msg.content}`)
          .join("\n\n");
        fullPrompt = `Previous conversation:\n${historyText}\n\nUser: ${prompt}`;
      }

      const systemPrompt = `You are an expert coding assistant. When asked to generate code, provide clean, well-commented, production-ready code. Format code blocks properly and explain your implementation choices briefly.\n\n${fullPrompt}`;

      const result = await adapter.call(systemPrompt, model || "");

      if (!result.success) {
        return res.status(400).json({ 
          error: result.error || "Failed to generate code",
          provider,
        });
      }

      await storage.createAuditLog({
        orgId: req.session.orgId!,
        userId: req.session.userId || null,
        action: "code_assistant_generate",
        target: provider,
        detailJson: { 
          promptLength: prompt.length,
          model: model || "default",
          inputTokens: result.usage?.inputTokens,
          outputTokens: result.usage?.outputTokens,
        },
      });

      res.json({
        content: result.content,
        usage: result.usage ? {
          inputTokens: result.usage.inputTokens,
          outputTokens: result.usage.outputTokens,
        } : undefined,
        provider,
      });
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ 
          error: error.errors.map(e => e.message).join(", "),
        });
      }
      res.status(500).json({ 
        error: error instanceof Error ? error.message : "An unexpected error occurred",
      });
    }
  });

  // ===== HUGGINGFACE AI ROUTES =====

  app.post("/api/ai/huggingface", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { prompt, model } = z.object({
        prompt: z.string().min(1, "Prompt is required").max(10000),
        model: z.string().optional(),
      }).parse(req.body);

      const { generateWithHuggingFace, getRateLimitStatus } = await import("./services/huggingfaceClient");
      
      const result = await generateWithHuggingFace(prompt, model);

      if (!result.success) {
        return res.status(400).json({ 
          error: result.error,
          rateLimitStatus: getRateLimitStatus(),
        });
      }

      await storage.createAuditLog({
        orgId: req.session.orgId!,
        userId: req.session.userId || null,
        action: "huggingface_generate",
        target: model || "meta-llama/Meta-Llama-3-8B-Instruct",
        detailJson: { 
          promptLength: prompt.length,
          inputTokens: result.usage?.inputTokens,
          outputTokens: result.usage?.outputTokens,
        },
      });

      res.json({
        content: result.content,
        usage: result.usage,
        provider: "huggingface",
        rateLimitStatus: getRateLimitStatus(),
      });
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ 
          error: error.errors.map(e => e.message).join(", "),
        });
      }
      res.status(500).json({ 
        error: error instanceof Error ? error.message : "An unexpected error occurred",
      });
    }
  });

  // ===== AGENT DEVELOPMENT ROUTES =====

  app.get("/api/agent-dev/analyze", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { filePath } = z.object({
        filePath: z.string().min(1, "File path is required"),
      }).parse(req.query);

      const orgId = req.session.orgId;
      const userId = req.session.userId;

      if (!orgId || !userId) {
        return res.status(400).json({ error: "No organization or user context" });
      }

      // Security: Prevent directory traversal
      if (filePath.includes("..") || filePath.startsWith("/")) {
        return res.status(400).json({ error: "Invalid file path - directory traversal not allowed" });
      }

      // For demo purposes, we'll read from the project root
      const fs = await import("fs/promises");
      const path = await import("path");
      
      // Secure path validation using resolve and relative
      const projectRoot = process.cwd();
      const resolvedPath = path.resolve(projectRoot, filePath);
      const relativePath = path.relative(projectRoot, resolvedPath);
      
      // Ensure the resolved path is still within project root
      if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
        return res.status(403).json({ error: "Access denied: path outside project" });
      }
      
      const safePath = resolvedPath;

      let content: string;
      let stats: any;
      try {
        content = await fs.readFile(safePath, "utf-8");
        stats = await fs.stat(safePath);
      } catch (err) {
        return res.status(404).json({ error: "File not found" });
      }

      const lines = content.split("\n").length;

      // Persist the analysis
      const analysis = await storage.createAgentAnalysis({
        orgId,
        projectId: null,
        userId,
        filePath,
        content,
        analysisResult: { lines, size: stats.size },
      });

      await storage.createAuditLog({
        orgId,
        userId,
        action: "agent_dev_analyze",
        target: filePath,
        detailJson: { lines, size: stats.size, analysisId: analysis.id },
      });

      res.json({
        analysisId: analysis.id,
        filePath,
        content,
        lines,
        size: stats.size,
      });
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ error: error.errors.map(e => e.message).join(", ") });
      }
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to analyze file" });
    }
  });

  app.post("/api/agent-dev/suggest", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { filePath, content, prompt, provider, model, analysisId } = z.object({
        filePath: z.string().min(1),
        content: z.string().min(1),
        prompt: z.string().min(1).max(5000),
        provider: z.enum(["openai", "anthropic", "xai", "perplexity", "google"]),
        model: z.string().optional(),
        analysisId: z.number().optional(),
      }).parse(req.body);

      const orgId = req.session.orgId;
      const userId = req.session.userId;

      if (!orgId || !userId) {
        return res.status(400).json({ error: "No organization or user context" });
      }

      // Create analysis record if not provided
      let finalAnalysisId = analysisId;
      if (!finalAnalysisId) {
        const analysis = await storage.createAgentAnalysis({
          orgId,
          projectId: null,
          userId,
          filePath,
          content,
          analysisResult: null,
        });
        finalAnalysisId = analysis.id;
      }

      const adapter = getProviderAdapter(provider);

      const systemPrompt = `You are an expert code reviewer and improvement assistant. Analyze the following code and provide specific, actionable improvement suggestions.

FILE: ${filePath}

CODE:
\`\`\`
${content}
\`\`\`

USER REQUEST: ${prompt}

Please provide 3-5 specific code improvement suggestions. For each suggestion:
1. Give it a clear, concise title
2. Explain why this improvement is beneficial
3. Provide the improved code block if applicable

Format your response as JSON with the following structure:
{
  "suggestions": [
    {
      "title": "Improvement title",
      "description": "Detailed explanation of why and how to improve",
      "codeBlock": "The improved code snippet (optional)"
    }
  ]
}`;

      const result = await adapter.call(systemPrompt, model || "");

      if (!result.success) {
        return res.status(400).json({
          error: result.error || "Failed to get suggestions",
          provider,
        });
      }

      // Try to parse JSON from response
      let suggestions = [];
      try {
        const jsonMatch = result.content?.match(/\{[\s\S]*"suggestions"[\s\S]*\}/);
        if (jsonMatch) {
          const parsed = JSON.parse(jsonMatch[0]);
          suggestions = parsed.suggestions || [];
        }
      } catch {
        // If JSON parsing fails, create a single suggestion from the raw response
        suggestions = [{
          title: "AI Analysis",
          description: result.content || "No suggestions available",
          codeBlock: null,
        }];
      }

      // Persist the suggestion
      const suggestion = await storage.createAgentSuggestion({
        analysisId: finalAnalysisId,
        provider,
        model: model || "default",
        prompt,
        suggestions,
        diffPreview: null,
      });

      await storage.createAuditLog({
        orgId,
        userId,
        action: "agent_dev_suggest",
        target: filePath,
        detailJson: {
          provider,
          model: model || "default",
          promptLength: prompt.length,
          suggestionsCount: suggestions.length,
          suggestionId: suggestion.id,
          inputTokens: result.usage?.inputTokens,
          outputTokens: result.usage?.outputTokens,
        },
      });

      res.json({
        suggestionId: suggestion.id,
        analysisId: finalAnalysisId,
        suggestions,
        provider,
        usage: result.usage ? {
          inputTokens: result.usage.inputTokens,
          outputTokens: result.usage.outputTokens,
        } : undefined,
      });
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ error: error.errors.map(e => e.message).join(", ") });
      }
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to get suggestions" });
    }
  });

  app.post("/api/agent-dev/apply", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { filePath, originalContent, proposedContent, description, suggestionId } = z.object({
        filePath: z.string().min(1),
        originalContent: z.string(),
        proposedContent: z.string().min(1),
        description: z.string().min(1).max(1000),
        suggestionId: z.number().optional(),
      }).parse(req.body);

      const orgId = req.session.orgId;
      const userId = req.session.userId;

      if (!orgId || !userId) {
        return res.status(400).json({ error: "No organization or user context" });
      }

      // Security: Prevent directory traversal
      if (filePath.includes("..") || filePath.startsWith("/")) {
        return res.status(400).json({ error: "Invalid file path" });
      }

      // Create the proposal with pending status
      const proposal = await storage.createAgentProposal({
        orgId,
        suggestionId: suggestionId || null,
        filePath,
        originalContent,
        proposedContent,
        status: "pending",
        approvedBy: null,
      });

      await storage.createAuditLog({
        orgId,
        userId,
        action: "agent_dev_proposal_created",
        target: filePath,
        detailJson: {
          proposalId: proposal.id,
          description,
          originalLength: originalContent.length,
          proposedLength: proposedContent.length,
        },
      });

      res.json({
        success: true,
        proposalId: proposal.id,
        message: "Proposal created successfully. Review and approve to apply changes.",
      });
    } catch (error) {
      if (error instanceof z.ZodError) {
        return res.status(400).json({ error: error.errors.map(e => e.message).join(", ") });
      }
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to create proposal" });
    }
  });

  // List proposals
  app.get("/api/agent-dev/proposals", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const { status } = z.object({
        status: z.enum(["pending", "approved", "rejected", "applied"]).optional(),
      }).parse(req.query);

      const proposals = await storage.getAgentProposalsByOrg(orgId, status);
      res.json(proposals);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch proposals" });
    }
  });

  // Approve a proposal
  app.post("/api/agent-dev/proposals/:id/approve", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const id = parseInt(req.params.id);
      const orgId = req.session.orgId;
      const userId = req.session.userId;

      if (!orgId || !userId) {
        return res.status(400).json({ error: "No organization or user context" });
      }

      const proposal = await storage.getAgentProposal(id);
      if (!proposal) {
        return res.status(404).json({ error: "Proposal not found" });
      }

      if (proposal.status !== "pending") {
        return res.status(400).json({ error: "Proposal is not pending" });
      }

      // Apply the changes to the file
      const fs = await import("fs/promises");
      const path = await import("path");
      
      // Secure path validation using resolve and relative
      const projectRoot = process.cwd();
      const resolvedPath = path.resolve(projectRoot, proposal.filePath);
      const relativePath = path.relative(projectRoot, resolvedPath);
      
      if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
        return res.status(403).json({ error: "Access denied: path outside project" });
      }
      
      const safePath = resolvedPath;

      try {
        await fs.writeFile(safePath, proposal.proposedContent, "utf-8");
      } catch (err) {
        return res.status(500).json({ error: "Failed to write file" });
      }

      const updated = await storage.updateAgentProposalStatus(id, "applied", userId);

      await storage.createAuditLog({
        orgId,
        userId,
        action: "agent_dev_proposal_approved",
        target: proposal.filePath,
        detailJson: { proposalId: id },
      });

      res.json({ success: true, proposal: updated });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to approve proposal" });
    }
  });

  // Reject a proposal
  app.post("/api/agent-dev/proposals/:id/reject", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const id = parseInt(req.params.id);
      const orgId = req.session.orgId;
      const userId = req.session.userId;

      if (!orgId || !userId) {
        return res.status(400).json({ error: "No organization or user context" });
      }

      // Parse optional reason from body
      const { reason } = z.object({
        reason: z.string().optional(),
      }).parse(req.body || {});

      const proposal = await storage.getAgentProposal(id);
      if (!proposal) {
        return res.status(404).json({ error: "Proposal not found" });
      }

      if (proposal.status !== "pending") {
        return res.status(400).json({ error: "Proposal is not pending" });
      }

      const updated = await storage.updateAgentProposalStatus(id, "rejected", userId);

      await storage.createAuditLog({
        orgId,
        userId,
        action: "agent_dev_proposal_rejected",
        target: proposal.filePath,
        detailJson: { proposalId: id, reason: reason || null },
      });

      res.json({ success: true, proposal: updated });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to reject proposal" });
    }
  });

  // ===== GEMINI AI ROUTES =====

  app.post("/api/gemini/chat", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { prompt, model, messages } = z.object({
        prompt: z.string().min(1).optional(),
        model: z.string().default("gemini-2.5-flash"),
        messages: z.array(z.object({
          role: z.string(),
          content: z.string(),
        })).optional(),
      }).parse(req.body);

      const { generateText, chat, isGeminiConfigured } = await import("./services/geminiClient");
      
      if (!isGeminiConfigured()) {
        return res.status(400).json({ error: "Gemini AI is not configured" });
      }

      let response: string;
      if (messages && messages.length > 0) {
        response = await chat(messages, model);
      } else if (prompt) {
        response = await generateText(prompt, model);
      } else {
        return res.status(400).json({ error: "Either prompt or messages is required" });
      }

      res.json({ content: response, model });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Gemini chat failed" });
    }
  });

  app.post("/api/gemini/image", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { prompt } = z.object({
        prompt: z.string().min(1, "Image prompt is required"),
      }).parse(req.body);

      const { generateImage, isGeminiConfigured } = await import("./services/geminiClient");
      
      if (!isGeminiConfigured()) {
        return res.status(400).json({ error: "Gemini AI is not configured" });
      }

      const imageDataUrl = await generateImage(prompt);
      res.json({ image: imageDataUrl });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Image generation failed" });
    }
  });

  app.get("/api/gemini/status", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { isGeminiConfigured } = await import("./services/geminiClient");
      res.json({ configured: isGeminiConfigured() });
    } catch (error) {
      res.json({ configured: false });
    }
  });

  // ===== USER PROFILE ROUTES =====

  const profileUpdateSchema = z.object({
    displayName: z.string().max(100).nullable().optional(),
    bio: z.string().max(2000).nullable().optional(),
    avatarUrl: z.string().url().nullable().optional(),
    backgroundUrl: z.string().url().nullable().optional(),
    youtubeVideos: z.array(z.string().url()).nullable().optional(),
    audioFiles: z.array(z.string()).nullable().optional(),
    theme: z.record(z.string()).nullable().optional(),
    socialLinks: z.record(z.string()).nullable().optional(),
  });

  app.get("/api/profile", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const userId = req.session.userId;
      if (!userId) {
        return res.status(401).json({ error: "Not authenticated" });
      }
      const profile = await storage.getUserProfile(userId);
      if (!profile) {
        return res.status(404).json({ error: "Profile not found" });
      }
      res.json({ profile });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch profile" });
    }
  });

  app.post("/api/profile", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const userId = req.session.userId;
      if (!userId) {
        return res.status(401).json({ error: "Not authenticated" });
      }
      const existing = await storage.getUserProfile(userId);
      if (existing) {
        return res.status(409).json({ error: "Profile already exists" });
      }
      const validated = profileUpdateSchema.parse(req.body);
      const profile = await storage.createUserProfile({ userId, ...validated });
      res.json({ profile });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create profile" });
    }
  });

  app.patch("/api/profile", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const userId = req.session.userId;
      if (!userId) {
        return res.status(401).json({ error: "Not authenticated" });
      }
      const validated = profileUpdateSchema.parse(req.body);
      let profile = await storage.getUserProfile(userId);
      if (!profile) {
        profile = await storage.createUserProfile({ userId, ...validated });
      } else {
        profile = await storage.updateUserProfile(userId, validated);
      }
      res.json({ profile });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to update profile" });
    }
  });

  // ===== UNIFIED STORAGE HUB ROUTES =====

  app.get("/api/storage/providers", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { getProviderStatuses } = await import("./services/storageHub");
      const providers = await getProviderStatuses();
      res.json({ providers });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to get providers" });
    }
  });

  app.get("/api/storage/files/:provider", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { provider } = req.params;
      const { folderId } = req.query;
      
      const validProviders = ['google-drive', 'onedrive', 'dropbox', 'github'];
      if (!validProviders.includes(provider)) {
        return res.status(400).json({ error: "Invalid provider" });
      }
      
      const { listFilesFromProvider } = await import("./services/storageHub");
      const files = await listFilesFromProvider(provider as any, folderId as string | undefined);
      res.json({ files });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list files" });
    }
  });

  app.get("/api/storage/download/:provider/:fileId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { provider, fileId } = req.params;
      
      const { downloadFile } = await import("./services/storageHub");
      const { data, name, mimeType } = await downloadFile(provider as any, decodeURIComponent(fileId));
      
      res.setHeader('Content-Disposition', `attachment; filename="${name}"`);
      res.setHeader('Content-Type', mimeType);
      res.send(data);
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to download file" });
    }
  });

  app.post("/api/storage/folder/:provider", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { provider } = req.params;
      const { name, parentFolderId } = z.object({
        name: z.string().min(1),
        parentFolderId: z.string().optional(),
      }).parse(req.body);
      
      const { createFolder } = await import("./services/storageHub");
      const folder = await createFolder(provider as any, parentFolderId, name);
      res.json({ folder });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to create folder" });
    }
  });

  app.delete("/api/storage/:provider/:fileId", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { provider, fileId } = req.params;
      
      const { deleteItem } = await import("./services/storageHub");
      await deleteItem(provider as any, decodeURIComponent(fileId));
      res.json({ success: true });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to delete item" });
    }
  });

  // ===== DROPBOX ROUTES =====

  app.get("/api/dropbox/status", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { getDropboxAccountInfo } = await import("./services/dropboxClient");
      const info = await getDropboxAccountInfo();
      res.json({ connected: true, ...info });
    } catch (error) {
      res.json({ connected: false });
    }
  });

  app.get("/api/dropbox/files", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const path = (req.query.path as string) || '';
      const { listDropboxFiles } = await import("./services/dropboxClient");
      const files = await listDropboxFiles(path);
      res.json({ files });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to list files" });
    }
  });

  // ===== SUBSCRIPTION ROUTES =====

  app.get("/api/subscription", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const subscription = await storage.getSubscriptionByOrgId(orgId);
      
      if (!subscription) {
        return res.json({
          plan: "free",
          status: "active",
          stripeCustomerId: null,
          stripeSubscriptionId: null,
          currentPeriodEnd: null,
        });
      }

      res.json({
        id: subscription.id,
        plan: subscription.plan,
        status: subscription.status,
        stripeCustomerId: subscription.stripeCustomerId,
        stripeSubscriptionId: subscription.stripeSubscriptionId,
        currentPeriodEnd: subscription.currentPeriodEnd,
        cancelAtPeriodEnd: subscription.cancelAtPeriodEnd === "true",
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to fetch subscription" });
    }
  });

  app.post("/api/subscription/portal", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const orgId = req.session.orgId;
      if (!orgId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const subscription = await storage.getSubscriptionByOrgId(orgId);
      
      if (!subscription || !subscription.stripeCustomerId) {
        return res.status(400).json({ error: "No active subscription found. Please upgrade first." });
      }

      const { createStripePortalSession } = await import("./services/stripeClient");
      const returnUrl = `${req.protocol}://${req.get("host")}/settings`;
      const session = await createStripePortalSession(subscription.stripeCustomerId, returnUrl);

      await storage.createAuditLog({
        orgId,
        userId: req.session.userId || null,
        action: "subscription_portal_opened",
        target: "stripe",
        detailJson: { subscriptionId: subscription.id },
      });

      res.json({ url: session.url });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to create portal session" });
    }
  });

  // ===== PROMO CODE ROUTES =====

  app.post("/api/promo/redeem", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { code } = z.object({
        code: z.string().min(1).max(50),
      }).parse(req.body);

      const orgId = req.session.orgId;
      const userId = req.session.userId;
      if (!orgId || !userId) {
        return res.status(400).json({ error: "No organization set" });
      }

      const promoCode = await storage.getPromoCodeByCode(code.toUpperCase());
      
      if (!promoCode) {
        return res.status(404).json({ error: "Invalid promo code" });
      }

      const now = new Date();
      if (promoCode.validFrom > now) {
        return res.status(400).json({ error: "This promo code is not yet valid" });
      }
      if (promoCode.validUntil && promoCode.validUntil < now) {
        return res.status(400).json({ error: "This promo code has expired" });
      }

      if (promoCode.maxUses !== null && promoCode.usedCount >= promoCode.maxUses) {
        return res.status(400).json({ error: "This promo code has reached its usage limit" });
      }

      const alreadyRedeemed = await storage.hasOrgRedeemedPromoCode(orgId, promoCode.id);
      if (alreadyRedeemed) {
        return res.status(400).json({ error: "You have already redeemed this promo code" });
      }

      const subscription = await storage.getSubscriptionByOrgId(orgId);
      
      await storage.createPromoRedemption({
        promoCodeId: promoCode.id,
        orgId,
        subscriptionId: subscription?.id || null,
      });
      
      await storage.incrementPromoCodeUsage(promoCode.id);

      await storage.createAuditLog({
        orgId,
        userId,
        action: "promo_code_redeemed",
        target: promoCode.code,
        detailJson: { 
          discountType: promoCode.discountType,
          discountValue: promoCode.discountValue,
        },
      });

      const discountText = promoCode.discountType === "percent" 
        ? `${promoCode.discountValue}% off`
        : `$${promoCode.discountValue} off`;

      res.json({ 
        success: true, 
        message: `Promo code applied! You get ${discountText}.`,
        discount: {
          type: promoCode.discountType,
          value: promoCode.discountValue,
        }
      });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to redeem promo code" });
    }
  });

  // ===== ADMIN ROUTES =====

  const requireAdmin = async (req: Request, res: Response, next: Function) => {
    const userId = req.session.userId;
    if (!userId) {
      return res.status(401).json({ error: "Not authenticated" });
    }
    const user = await storage.getUser(userId);
    if (!user || (user.role !== "owner" && user.role !== "admin")) {
      return res.status(403).json({ error: "Admin access required" });
    }
    next();
  };

  app.get("/api/admin/users", requireAuth, requireAdmin, apiLimiter, async (req: Request, res: Response) => {
    try {
      const users = await storage.listAllUsers();
      const usersWithOrgs = await Promise.all(
        users.map(async (user) => {
          const orgs = await storage.getOrgsByUser(user.id);
          return {
            id: user.id,
            email: user.email,
            role: user.role,
            createdAt: user.createdAt,
            orgs: orgs.map(o => ({ id: o.id, name: o.name })),
          };
        })
      );
      res.json(usersWithOrgs);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to list users" });
    }
  });

  app.delete("/api/admin/users/:id", requireAuth, requireAdmin, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { id } = req.params;
      const userId = req.session.userId;

      if (id === userId) {
        return res.status(400).json({ error: "Cannot delete yourself" });
      }

      const user = await storage.getUser(id);
      if (!user) {
        return res.status(404).json({ error: "User not found" });
      }

      await storage.deleteUser(id);

      await storage.createAuditLog({
        orgId: req.session.orgId!,
        userId: userId!,
        action: "admin_delete_user",
        target: id,
        detailJson: { deletedEmail: user.email },
      });

      res.json({ success: true });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to delete user" });
    }
  });

  app.get("/api/admin/stats", requireAuth, requireAdmin, apiLimiter, async (req: Request, res: Response) => {
    try {
      const thirtyDaysAgo = new Date();
      thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

      const [userCount, orgCount, usageSummary] = await Promise.all([
        storage.getUserCount(),
        storage.getOrgCount(),
        storage.getGlobalUsageSummary(thirtyDaysAgo),
      ]);

      res.json({
        totalUsers: userCount,
        totalOrgs: orgCount,
        totalTokens: usageSummary.totalTokens,
        totalCostUsd: usageSummary.totalCostUsd,
      });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to get admin stats" });
    }
  });

  app.get("/api/admin/audit-logs", requireAuth, requireAdmin, apiLimiter, async (req: Request, res: Response) => {
    try {
      const search = req.query.search as string | undefined;
      const limit = parseInt(req.query.limit as string) || 100;

      const logs = await storage.searchAuditLogs(search, Math.min(limit, 500));
      res.json(logs);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to search audit logs" });
    }
  });

  app.get("/api/admin/export", requireAuth, requireAdmin, apiLimiter, async (req: Request, res: Response) => {
    try {
      const userId = req.session.userId;
      const orgId = req.session.orgId;

      if (!userId || !orgId) {
        return res.status(400).json({ error: "No user or organization context" });
      }

      const user = await storage.getUser(userId);
      if (!user) {
        return res.status(404).json({ error: "User not found" });
      }

      const isOwner = user.role === "owner";
      const exportData = await storage.getExportData(orgId, isOwner);

      await storage.createAuditLog({
        orgId,
        userId,
        action: "data_export",
        target: isOwner ? "all_data" : "org_data",
        detailJson: { 
          isOwner,
          userCount: exportData.users.length,
          orgCount: exportData.orgs.length,
          projectCount: exportData.projects.length,
        },
      });

      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      res.setHeader("Content-Type", "application/json");
      res.setHeader("Content-Disposition", `attachment; filename="orchestration-hub-export-${timestamp}.json"`);
      res.json(exportData);
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to export data" });
    }
  });

  // ===== PUBLIC STATUS ENDPOINT =====

  app.get("/api/status", (req: Request, res: Response) => {
    const circuitStatus = retryService.getCircuitStatus();
    res.json({
      status: "ok",
      timestamp: new Date().toISOString(),
      circuits: circuitStatus,
    });
  });

  // ===== CIRCUIT MANAGEMENT =====

  app.post("/api/circuits/reset", requireAuth, requireAdmin, apiLimiter, async (req: Request, res: Response) => {
    try {
      const { provider } = z.object({
        provider: z.string().optional(),
      }).parse(req.body);

      if (provider) {
        retryService.resetCircuit(provider);
      } else {
        retryService.resetAllCircuits();
      }

      await storage.createAuditLog({
        orgId: req.session.orgId!,
        userId: req.session.userId!,
        action: "circuit_reset",
        target: provider || "all",
        detailJson: null,
      });

      res.json({ success: true, circuits: retryService.getCircuitStatus() });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to reset circuit" });
    }
  });

  // ===== USER PROFILE & SOCIAL LINKS =====

  app.get("/api/profile", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const userId = req.session.userId!;
      const profile = await storage.getUserProfile(userId);
      res.json({ profile: profile || null });
    } catch (error) {
      res.status(500).json({ error: error instanceof Error ? error.message : "Failed to get profile" });
    }
  });

  app.post("/api/profile", requireAuth, apiLimiter, async (req: Request, res: Response) => {
    try {
      const userId = req.session.userId!;
      const { displayName, bio, socialLinks } = z.object({
        displayName: z.string().optional(),
        bio: z.string().optional(),
        socialLinks: z.object({
          linktree: z.string().url().optional().or(z.literal("")),
          orchid: z.string().url().optional().or(z.literal("")),
          twitter: z.string().url().optional().or(z.literal("")),
          github: z.string().url().optional().or(z.literal("")),
          linkedin: z.string().url().optional().or(z.literal("")),
          website: z.string().url().optional().or(z.literal("")),
          instagram: z.string().url().optional().or(z.literal("")),
          facebook: z.string().url().optional().or(z.literal("")),
          youtube: z.string().url().optional().or(z.literal("")),
          tiktok: z.string().url().optional().or(z.literal("")),
          discord: z.string().url().optional().or(z.literal("")),
          twitch: z.string().url().optional().or(z.literal("")),
          medium: z.string().url().optional().or(z.literal("")),
          substack: z.string().url().optional().or(z.literal("")),
          behance: z.string().url().optional().or(z.literal("")),
          dribbble: z.string().url().optional().or(z.literal("")),
          kofi: z.string().url().optional().or(z.literal("")),
          patreon: z.string().url().optional().or(z.literal("")),
          mastodon: z.string().url().optional().or(z.literal("")),
          bluesky: z.string().url().optional().or(z.literal("")),
          threads: z.string().url().optional().or(z.literal("")),
          pinterest: z.string().url().optional().or(z.literal("")),
          reddit: z.string().url().optional().or(z.literal("")),
          spotify: z.string().url().optional().or(z.literal("")),
          soundcloud: z.string().url().optional().or(z.literal("")),
          bandcamp: z.string().url().optional().or(z.literal("")),
          devto: z.string().url().optional().or(z.literal("")),
          hashnode: z.string().url().optional().or(z.literal("")),
          codepen: z.string().url().optional().or(z.literal("")),
          stackoverflow: z.string().url().optional().or(z.literal("")),
          figma: z.string().url().optional().or(z.literal("")),
        }).optional(),
      }).parse(req.body);

      let profile = await storage.getUserProfile(userId);
      
      const profileData = {
        displayName,
        bio,
        socialLinks: socialLinks || {},
      };

      if (profile) {
        profile = await storage.updateUserProfile(userId, profileData);
      } else {
        profile = await storage.createUserProfile({
          userId,
          ...profileData,
        });
      }

      res.json({ profile });
    } catch (error) {
      res.status(400).json({ error: error instanceof Error ? error.message : "Failed to update profile" });
    }
  });

  return httpServer;
}
