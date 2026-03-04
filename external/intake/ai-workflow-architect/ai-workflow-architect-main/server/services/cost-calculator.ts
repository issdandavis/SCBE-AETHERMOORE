import { db } from "../db";
import { usageRecords, budgets } from "@shared/schema";
import { eq, and, gte, sql } from "drizzle-orm";
import { getModelById, estimateTokens as estimateTokenCount } from "./free-models-config";

export interface UsageMetrics {
  inputTokens: number;
  outputTokens: number;
  estimatedCostUsd: number;
  provider: string;
  model: string;
}

export interface BudgetStatus {
  period: "daily" | "monthly";
  limitUsd: number;
  spentUsd: number;
  remainingUsd: number;
  percentUsed: number;
  isExceeded: boolean;
}

const PROVIDER_COSTS: Record<string, Record<string, { input: number; output: number }>> = {
  openai: {
    "gpt-4o": { input: 0.0025, output: 0.01 },
    "gpt-4o-mini": { input: 0.00015, output: 0.0006 },
    "gpt-4-turbo": { input: 0.01, output: 0.03 },
    default: { input: 0.002, output: 0.006 },
  },
  anthropic: {
    "claude-sonnet-4-20250514": { input: 0.003, output: 0.015 },
    "claude-3-haiku": { input: 0.00025, output: 0.00125 },
    default: { input: 0.003, output: 0.015 },
  },
  xai: {
    "grok-2": { input: 0.002, output: 0.01 },
    default: { input: 0.002, output: 0.01 },
  },
  perplexity: {
    sonar: { input: 0.001, output: 0.001 },
    default: { input: 0.001, output: 0.001 },
  },
  google: {
    "gemini-2.0-flash": { input: 0.000075, output: 0.0003 },
    "gemini-1.5-pro": { input: 0.00125, output: 0.005 },
    default: { input: 0.0001, output: 0.0003 },
  },
  groq: {
    "llama3-8b-8192": { input: 0.00005, output: 0.00008 },
    "mixtral-8x7b-32768": { input: 0.00024, output: 0.00024 },
    "llama-3.3-70b-versatile": { input: 0.00059, output: 0.00079 },
    default: { input: 0.0001, output: 0.0001 },
  },
  ollama: {
    default: { input: 0, output: 0 },
  },
  huggingface: {
    default: { input: 0, output: 0 },
  },
};

export function estimateCost(
  provider: string,
  model: string,
  inputTokens: number,
  outputTokens: number
): number {
  const freeModel = getModelById(model);
  if (freeModel) {
    return ((inputTokens + outputTokens) / 1000) * freeModel.costPer1kTokens;
  }

  const providerCosts = PROVIDER_COSTS[provider.toLowerCase()];
  if (!providerCosts) {
    console.warn(`Unknown provider "${provider}" - defaulting to zero cost. Add it to PROVIDER_COSTS.`);
    return 0;
  }
  const modelCosts = providerCosts[model] || providerCosts.default;

  const inputCost = (inputTokens / 1000) * modelCosts.input;
  const outputCost = (outputTokens / 1000) * modelCosts.output;

  return inputCost + outputCost;
}

export function estimateTokens(text: string): number {
  return estimateTokenCount(text);
}

export async function trackUsage(
  orgId: string,
  userId: string,
  provider: string,
  model: string,
  inputTokens: number,
  outputTokens: number,
  metadata?: Record<string, unknown>
): Promise<void> {
  const cost = estimateCost(provider, model, inputTokens, outputTokens);

  await db.insert(usageRecords).values({
    orgId,
    userId,
    provider,
    model,
    inputTokens,
    outputTokens,
    estimatedCostUsd: cost.toFixed(6),
    metadata: metadata || null,
  });

  await updateBudgetSpend(orgId, cost);
}

async function updateBudgetSpend(orgId: string, costUsd: number): Promise<void> {
  const orgBudgets = await db
    .select()
    .from(budgets)
    .where(eq(budgets.orgId, orgId));

  for (const budget of orgBudgets) {
    const currentSpent = parseFloat(budget.spentUsd || "0");
    const newSpent = currentSpent + costUsd;

    await db
      .update(budgets)
      .set({
        spentUsd: newSpent.toFixed(2),
        updatedAt: new Date(),
      })
      .where(eq(budgets.id, budget.id));
  }
}

export async function getBudgetStatus(
  orgId: string,
  period: "daily" | "monthly"
): Promise<BudgetStatus | null> {
  const [budget] = await db
    .select()
    .from(budgets)
    .where(and(eq(budgets.orgId, orgId), eq(budgets.period, period)));

  if (!budget) return null;

  const limitUsd = parseFloat(budget.limitUsd || "0");
  const spentUsd = parseFloat(budget.spentUsd || "0");
  const remainingUsd = Math.max(0, limitUsd - spentUsd);
  const percentUsed = limitUsd > 0 ? (spentUsd / limitUsd) * 100 : 0;

  return {
    period,
    limitUsd,
    spentUsd,
    remainingUsd,
    percentUsed,
    isExceeded: spentUsd >= limitUsd,
  };
}

export async function checkBudgetAllowance(
  orgId: string,
  estimatedCost: number
): Promise<{ allowed: boolean; reason?: string }> {
  const dailyBudget = await getBudgetStatus(orgId, "daily");
  const monthlyBudget = await getBudgetStatus(orgId, "monthly");

  if (dailyBudget?.isExceeded) {
    return {
      allowed: false,
      reason: `Daily budget exceeded ($${dailyBudget.spentUsd.toFixed(2)} of $${dailyBudget.limitUsd.toFixed(2)})`,
    };
  }

  if (monthlyBudget?.isExceeded) {
    return {
      allowed: false,
      reason: `Monthly budget exceeded ($${monthlyBudget.spentUsd.toFixed(2)} of $${monthlyBudget.limitUsd.toFixed(2)})`,
    };
  }

  if (dailyBudget && dailyBudget.remainingUsd < estimatedCost) {
    return {
      allowed: false,
      reason: `Request would exceed daily budget (remaining: $${dailyBudget.remainingUsd.toFixed(4)})`,
    };
  }

  if (monthlyBudget && monthlyBudget.remainingUsd < estimatedCost) {
    return {
      allowed: false,
      reason: `Request would exceed monthly budget (remaining: $${monthlyBudget.remainingUsd.toFixed(4)})`,
    };
  }

  return { allowed: true };
}

export async function getUsageSummary(
  orgId: string,
  startDate: Date,
  endDate: Date
): Promise<{
  totalCost: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  byProvider: Record<string, { cost: number; requests: number }>;
}> {
  const records = await db
    .select()
    .from(usageRecords)
    .where(
      and(
        eq(usageRecords.orgId, orgId),
        gte(usageRecords.createdAt, startDate)
      )
    );

  const filteredRecords = records.filter((r) => r.createdAt <= endDate);

  let totalCost = 0;
  let totalInputTokens = 0;
  let totalOutputTokens = 0;
  const byProvider: Record<string, { cost: number; requests: number }> = {};

  for (const record of filteredRecords) {
    const cost = parseFloat(record.estimatedCostUsd || "0");
    totalCost += cost;
    totalInputTokens += record.inputTokens || 0;
    totalOutputTokens += record.outputTokens || 0;

    if (!byProvider[record.provider]) {
      byProvider[record.provider] = { cost: 0, requests: 0 };
    }
    byProvider[record.provider].cost += cost;
    byProvider[record.provider].requests += 1;
  }

  return {
    totalCost,
    totalInputTokens,
    totalOutputTokens,
    byProvider,
  };
}

export async function resetDailyBudgets(): Promise<void> {
  await db
    .update(budgets)
    .set({ spentUsd: "0", updatedAt: new Date() })
    .where(eq(budgets.period, "daily"));
}

export async function resetMonthlyBudgets(): Promise<void> {
  await db
    .update(budgets)
    .set({ spentUsd: "0", updatedAt: new Date() })
    .where(eq(budgets.period, "monthly"));
}
