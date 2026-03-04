import { db } from "../db";
import { roundtableSessions, roundtableMessages } from "@shared/schema";
import type { RoundtableSession, RoundtableMessage, InsertRoundtableSession, InsertRoundtableMessage } from "@shared/schema";
import { eq, asc, desc } from "drizzle-orm";
import { getProviderAdapter } from "./providerAdapters";
import { trackUsage, estimateCost, estimateTokens, checkBudgetAllowance } from "./cost-calculator";

export interface RoundtableConfig {
  title: string;
  topic?: string;
  providers: string[];
  orchestrationMode?: "round_robin" | "topic_based" | "free_form";
  maxTurns?: number;
}

export interface TurnResult {
  provider: string;
  model: string;
  content: string;
  signature?: string;
  tokensUsed: number;
  responseTimeMs: number;
  success: boolean;
  error?: string;
}

const PROVIDER_SIGNATURES: Record<string, string> = {
  openai: "— GPT",
  anthropic: "— Claude",
  xai: "— Grok",
  perplexity: "— Perplexity",
  google: "— Gemini",
  gemini: "— Gemini",
  groq: "— Groq",
  ollama: "— Ollama",
  huggingface: "— HuggingFace",
};

const PROVIDER_MODELS: Record<string, string> = {
  openai: "gpt-4o",
  anthropic: "claude-sonnet-4-20250514",
  xai: "grok-2",
  perplexity: "sonar",
  google: "gemini-2.0-flash",
  gemini: "gemini-2.0-flash",
  groq: "llama3-8b-8192",
  ollama: "llama3.1:8b",
  huggingface: "meta-llama/Meta-Llama-3-8B-Instruct",
};

export async function createSession(
  orgId: string,
  userId: string,
  projectId: string | null,
  config: RoundtableConfig
): Promise<RoundtableSession> {
  const [session] = await db
    .insert(roundtableSessions)
    .values({
      orgId,
      projectId,
      title: config.title,
      topic: config.topic || null,
      orchestrationMode: config.orchestrationMode || "round_robin",
      maxTurns: config.maxTurns || 20,
      activeProviders: config.providers,
      createdBy: userId,
      status: "active",
    })
    .returning();

  return session;
}

export async function getSession(sessionId: string): Promise<RoundtableSession | null> {
  const [session] = await db
    .select()
    .from(roundtableSessions)
    .where(eq(roundtableSessions.id, sessionId));
  return session || null;
}

export async function getSessionMessages(sessionId: string): Promise<RoundtableMessage[]> {
  return db
    .select()
    .from(roundtableMessages)
    .where(eq(roundtableMessages.sessionId, sessionId))
    .orderBy(asc(roundtableMessages.sequenceNumber));
}

export async function addUserMessage(
  sessionId: string,
  userId: string,
  content: string
): Promise<RoundtableMessage> {
  const messages = await getSessionMessages(sessionId);
  const sequenceNumber = messages.length + 1;

  const [message] = await db
    .insert(roundtableMessages)
    .values({
      sessionId,
      senderType: "user",
      senderId: userId,
      content,
      sequenceNumber,
    })
    .returning();

  return message;
}

export async function executeNextTurn(
  sessionId: string,
  orgId: string,
  userId: string
): Promise<TurnResult> {
  const session = await getSession(sessionId);
  if (!session) {
    return { provider: "", model: "", content: "", tokensUsed: 0, responseTimeMs: 0, success: false, error: "Session not found" };
  }

  if (session.status !== "active") {
    return { provider: "", model: "", content: "", tokensUsed: 0, responseTimeMs: 0, success: false, error: "Session is not active" };
  }

  if (session.currentTurn >= (session.maxTurns || 20)) {
    await db.update(roundtableSessions).set({ status: "completed" }).where(eq(roundtableSessions.id, sessionId));
    return { provider: "", model: "", content: "", tokensUsed: 0, responseTimeMs: 0, success: false, error: "Maximum turns reached" };
  }

  const providers = session.activeProviders || [];
  if (providers.length === 0) {
    return { provider: "", model: "", content: "", tokensUsed: 0, responseTimeMs: 0, success: false, error: "No providers configured" };
  }

  const provider = selectNextProvider(session, providers);
  const model = PROVIDER_MODELS[provider] || "default";

  const messages = await getSessionMessages(sessionId);
  const prompt = buildPrompt(session, messages, provider);

  const estimatedInputTokens = estimateTokens(prompt);
  const estimatedOutputTokens = 500;
  const estimatedCost = estimateCost(provider, model, estimatedInputTokens, estimatedOutputTokens);
  
  const budgetCheck = await checkBudgetAllowance(orgId, estimatedCost);
  if (!budgetCheck.allowed) {
    return {
      provider,
      model,
      content: "",
      tokensUsed: 0,
      responseTimeMs: 0,
      success: false,
      error: budgetCheck.reason || "Budget limit exceeded",
    };
  }

  const startTime = Date.now();
  const adapter = getProviderAdapter(provider);
  const response = await adapter.call(prompt, model);
  const responseTimeMs = Date.now() - startTime;

  if (!response.success) {
    return {
      provider,
      model,
      content: "",
      tokensUsed: 0,
      responseTimeMs,
      success: false,
      error: response.error,
    };
  }

  const signature = PROVIDER_SIGNATURES[provider] || `— ${provider}`;
  const tokensUsed = (response.usage?.inputTokens || 0) + (response.usage?.outputTokens || 0);
  const sequenceNumber = messages.length + 1;

  await db.insert(roundtableMessages).values({
    sessionId,
    senderType: "ai",
    provider,
    model,
    content: response.content || "",
    signature,
    sequenceNumber,
    tokensUsed,
    responseTimeMs,
  });

  await db
    .update(roundtableSessions)
    .set({ currentTurn: session.currentTurn + 1, updatedAt: new Date() })
    .where(eq(roundtableSessions.id, sessionId));

  await trackUsage(
    orgId,
    userId,
    provider,
    model,
    response.usage?.inputTokens || 0,
    response.usage?.outputTokens || 0,
    { sessionId, type: "roundtable" }
  );

  return {
    provider,
    model,
    content: response.content || "",
    signature,
    tokensUsed,
    responseTimeMs,
    success: true,
  };
}

function selectNextProvider(session: RoundtableSession, providers: string[]): string {
  const mode = session.orchestrationMode || "round_robin";
  
  switch (mode) {
    case "round_robin":
      return providers[session.currentTurn % providers.length];
    
    case "topic_based":
      return providers[session.currentTurn % providers.length];
    
    case "free_form":
      const randomIndex = Math.floor(Math.random() * providers.length);
      return providers[randomIndex];
    
    default:
      return providers[session.currentTurn % providers.length];
  }
}

function buildPrompt(session: RoundtableSession, messages: RoundtableMessage[], currentProvider: string): string {
  const topic = session.topic || "the topic at hand";
  const conversationHistory = messages
    .map((m) => {
      if (m.senderType === "user") {
        return `User: ${m.content}`;
      }
      return `${m.provider || "AI"}: ${m.content}`;
    })
    .join("\n\n");

  return `You are participating in a roundtable discussion as ${currentProvider}.
Topic: ${topic}

Previous conversation:
${conversationHistory || "(No messages yet)"}

Provide your perspective on this topic. Be concise but insightful. End with "${PROVIDER_SIGNATURES[currentProvider] || `— ${currentProvider}`}".`;
}

export async function pauseSession(sessionId: string): Promise<void> {
  await db.update(roundtableSessions).set({ status: "paused", updatedAt: new Date() }).where(eq(roundtableSessions.id, sessionId));
}

export async function resumeSession(sessionId: string): Promise<void> {
  await db.update(roundtableSessions).set({ status: "active", updatedAt: new Date() }).where(eq(roundtableSessions.id, sessionId));
}

export async function completeSession(sessionId: string): Promise<void> {
  await db.update(roundtableSessions).set({ status: "completed", updatedAt: new Date() }).where(eq(roundtableSessions.id, sessionId));
}

export async function listOrgSessions(orgId: string): Promise<RoundtableSession[]> {
  return db
    .select()
    .from(roundtableSessions)
    .where(eq(roundtableSessions.orgId, orgId))
    .orderBy(desc(roundtableSessions.createdAt));
}
