import { storage } from "../storage";
import { getProviderAdapter } from "./providerAdapters";
import { getUserCredential } from "./vault";
import type { RoundtableMessage, RoundtableSession } from "@shared/schema";

export const AI_CONFIGS: Record<string, { name: string; model: string; role: string; signOff: string }> = {
  openai: { name: "GPT", model: "gpt-4o", role: "analytical strategist", signOff: "— GPT (OpenAI)" },
  anthropic: { name: "Claude", model: "claude-sonnet-4-20250514", role: "thoughtful advisor", signOff: "— Claude (Anthropic)" },
  xai: { name: "Grok", model: "grok-2", role: "creative challenger", signOff: "— Grok (xAI)" },
  perplexity: { name: "Sonar", model: "sonar", role: "research specialist", signOff: "— Sonar (Perplexity)" },
  google: { name: "Gemini", model: "gemini-2.0-flash", role: "multimodal expert", signOff: "— Gemini (Google)" },
};

function buildPrompt(
  session: RoundtableSession,
  messages: RoundtableMessage[],
  provider: string
): string {
  const config = AI_CONFIGS[provider];
  if (!config) {
    throw new Error(`Unknown provider: ${provider}`);
  }

  const conversationHistory = messages
    .map((m) => {
      const senderLabel = m.senderType === "user" 
        ? "User" 
        : m.senderType === "system" 
          ? "System" 
          : `${AI_CONFIGS[m.provider || ""]?.name || m.provider || "AI"}`;
      return `${senderLabel}: ${m.content}`;
    })
    .join("\n\n");

  const prompt = `You are ${config.name}, acting as the ${config.role} in a multi-AI roundtable discussion.

TOPIC: ${session.topic || session.title}

Your role is to be a ${config.role}. Contribute thoughtfully to the discussion, building on what others have said while bringing your unique perspective.

CONVERSATION SO FAR:
${conversationHistory || "(No messages yet - you are starting the discussion)"}

INSTRUCTIONS:
- Respond directly to the topic and previous messages
- Stay in character as a ${config.role}
- Be concise but insightful (aim for 2-4 paragraphs)
- You may reference or respond to points made by other AIs
- End your response with your signature: "${config.signOff}"

Your response:`;

  return prompt;
}

export async function processAITurn(
  sessionId: string,
  provider: string,
  userId: string
): Promise<RoundtableMessage> {
  const startTime = Date.now();
  
  const session = await storage.getRoundtableSession(sessionId);
  if (!session) {
    throw new Error(`Session not found: ${sessionId}`);
  }

  const config = AI_CONFIGS[provider];
  if (!config) {
    throw new Error(`Unknown provider: ${provider}`);
  }

  const messages = await storage.getRoundtableMessages(sessionId);
  const prompt = buildPrompt(session, messages, provider);

  console.log(`[Roundtable] Processing turn for ${config.name} in session ${sessionId}`);

  const apiKey = await getUserCredential(userId, provider);
  const adapter = getProviderAdapter(provider, apiKey || undefined);

  const response = await adapter.call(prompt, config.model);
  const responseTime = Date.now() - startTime;

  if (!response.success) {
    console.error(`[Roundtable] ${config.name} error:`, response.error);
    throw new Error(`${config.name} failed: ${response.error}`);
  }

  const sequenceNumber = await storage.getNextSequenceNumber(sessionId);

  const message = await storage.createRoundtableMessage({
    sessionId,
    senderType: "ai",
    senderId: null,
    provider,
    model: config.model,
    content: response.content || "",
    signature: config.signOff,
    sequenceNumber,
    tokensUsed: (response.usage?.inputTokens || 0) + (response.usage?.outputTokens || 0),
    responseTimeMs: responseTime,
    metadata: {
      inputTokens: response.usage?.inputTokens,
      outputTokens: response.usage?.outputTokens,
      costEstimate: response.usage?.costEstimate,
    },
  });

  await storage.updateRoundtableSession(sessionId, {
    currentTurn: session.currentTurn + 1,
  });

  // Track usage for cost analytics
  try {
    await storage.createUsageRecord({
      orgId: session.orgId,
      userId,
      provider,
      model: config.model,
      inputTokens: response.usage?.inputTokens || 0,
      outputTokens: response.usage?.outputTokens || 0,
      estimatedCostUsd: response.usage?.costEstimate || "0",
      metadata: { requestType: "roundtable", sessionId },
    });
  } catch (err) {
    console.error(`[Roundtable] Failed to record usage:`, err);
  }

  console.log(`[Roundtable] ${config.name} responded in ${responseTime}ms (${response.usage?.inputTokens || 0} + ${response.usage?.outputTokens || 0} tokens)`);

  return message;
}

export async function runRoundtableRound(
  sessionId: string,
  userId: string
): Promise<RoundtableMessage[]> {
  const session = await storage.getRoundtableSession(sessionId);
  if (!session) {
    throw new Error(`Session not found: ${sessionId}`);
  }

  if (session.status !== "active") {
    throw new Error(`Session is not active: ${session.status}`);
  }

  const maxTurns = session.maxTurns || 20;
  if (session.currentTurn >= maxTurns) {
    await storage.updateRoundtableSession(sessionId, { status: "completed" });
    throw new Error(`Session has reached maximum turns (${maxTurns})`);
  }

  const activeProviders = session.activeProviders || [];
  if (activeProviders.length === 0) {
    throw new Error("No active providers in session");
  }

  console.log(`[Roundtable] Running round with providers: ${activeProviders.join(", ")}`);

  const newMessages: RoundtableMessage[] = [];

  for (const provider of activeProviders) {
    try {
      const message = await processAITurn(sessionId, provider, userId);
      newMessages.push(message);
    } catch (error) {
      console.error(`[Roundtable] Error processing ${provider}:`, error);
      const sequenceNumber = await storage.getNextSequenceNumber(sessionId);
      const errorMessage = await storage.createRoundtableMessage({
        sessionId,
        senderType: "system",
        senderId: null,
        provider,
        model: null,
        content: `Error from ${AI_CONFIGS[provider]?.name || provider}: ${error instanceof Error ? error.message : "Unknown error"}`,
        signature: null,
        sequenceNumber,
        tokensUsed: null,
        responseTimeMs: null,
        metadata: { error: true },
      });
      newMessages.push(errorMessage);
    }
  }

  return newMessages;
}
