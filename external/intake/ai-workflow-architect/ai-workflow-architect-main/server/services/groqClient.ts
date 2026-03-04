import Groq from "groq-sdk";
import type { ProviderResponse } from "./providerAdapters";
import { getModelById } from "./free-models-config";

let groqClient: Groq | null = null;

function getClient(): Groq | null {
  if (!process.env.GROQ_API_KEY) {
    return null;
  }
  if (!groqClient) {
    groqClient = new Groq({
      apiKey: process.env.GROQ_API_KEY,
    });
  }
  return groqClient;
}

export function isGroqAvailable(): boolean {
  return !!process.env.GROQ_API_KEY;
}

export async function generateWithGroq(
  prompt: string,
  model: string = "llama3-8b-8192"
): Promise<ProviderResponse> {
  const client = getClient();
  if (!client) {
    return {
      success: false,
      error: "Groq API key not configured. Add GROQ_API_KEY to your secrets.",
    };
  }

  try {
    const chatCompletion = await client.chat.completions.create({
      messages: [{ role: "user", content: prompt }],
      model,
      temperature: 0.7,
      max_tokens: 4096,
      top_p: 0.95,
    });

    const content = chatCompletion.choices[0]?.message?.content || "";
    const usage = chatCompletion.usage;

    const modelConfig = getModelById(model);
    const inputTokens = usage?.prompt_tokens || 0;
    const outputTokens = usage?.completion_tokens || 0;
    const costPer1k = modelConfig?.costPer1kTokens || 0.0001;
    const totalCost = ((inputTokens + outputTokens) / 1000) * costPer1k;

    return {
      success: true,
      content,
      usage: {
        inputTokens,
        outputTokens,
        costEstimate: totalCost.toFixed(6),
      },
    };
  } catch (error) {
    if (error instanceof Error) {
      if (error.message.includes("rate_limit")) {
        return {
          success: false,
          error: "Groq rate limit reached. Please wait a moment and try again.",
        };
      }
      if (error.message.includes("invalid_api_key")) {
        return {
          success: false,
          error: "Invalid Groq API key. Please check your GROQ_API_KEY secret.",
        };
      }
      return {
        success: false,
        error: error.message,
      };
    }
    return {
      success: false,
      error: "Groq request failed",
    };
  }
}

export async function listGroqModels(): Promise<string[]> {
  const client = getClient();
  if (!client) return [];

  try {
    const models = await client.models.list();
    return models.data.map((m) => m.id);
  } catch {
    return [];
  }
}

export function getGroqModelCost(model: string): number {
  const modelConfig = getModelById(model);
  return modelConfig?.costPer1kTokens || 0.0001;
}
