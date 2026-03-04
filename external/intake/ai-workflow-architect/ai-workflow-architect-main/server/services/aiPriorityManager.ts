// AI Priority Manager - Prioritizes cost-free options first
// Priority: FREE > YOUR_KEY > CREDITS (avoid Replit's paid integrations)

import { getProviderAdapter, type ProviderResponse } from "./providerAdapters";
import { isHuggingFaceAvailable, getRateLimitStatus } from "./huggingfaceClient";

export type CostTier = "free" | "your_key" | "credits";

export interface ProviderInfo {
  id: string;
  name: string;
  costTier: CostTier;
  available: boolean;
  models: string[];
  description: string;
  priority: number;
}

// Provider definitions in priority order
const PROVIDER_DEFINITIONS: Omit<ProviderInfo, "available">[] = [
  {
    id: "huggingface",
    name: "HuggingFace",
    costTier: "free",
    models: ["meta-llama/Meta-Llama-3-8B-Instruct", "mistralai/Mistral-7B-Instruct-v0.2"],
    description: "Free Llama 3 - 1000 req/day",
    priority: 1,
  },
  {
    id: "gemini",
    name: "Google Gemini Flash",
    costTier: "free",
    models: ["gemini-2.0-flash", "gemini-1.5-flash"],
    description: "Free tier - generous limits with your API key",
    priority: 2,
  },
  {
    id: "anthropic",
    name: "Anthropic Claude",
    costTier: "your_key",
    models: ["claude-sonnet-4-20250514", "claude-3-haiku-20240307"],
    description: "Your API key - high quality responses",
    priority: 3,
  },
  {
    id: "xai",
    name: "xAI Grok",
    costTier: "your_key",
    models: ["grok-2", "grok-2-mini"],
    description: "Your API key - fast and capable",
    priority: 4,
  },
  {
    id: "perplexity",
    name: "Perplexity",
    costTier: "your_key",
    models: ["sonar", "sonar-pro"],
    description: "Your API key - search-enhanced AI",
    priority: 5,
  },
  {
    id: "openai",
    name: "OpenAI (Replit)",
    costTier: "credits",
    models: ["gpt-4o", "gpt-4o-mini"],
    description: "Uses Replit credits - AVOID if possible",
    priority: 99,
  },
];

// Check if a provider is available based on env vars (NOT AI_INTEGRATIONS_* vars)
function checkProviderAvailability(providerId: string): boolean {
  switch (providerId) {
    case "huggingface":
      return isHuggingFaceAvailable();
    case "gemini":
      return !!process.env.GOOGLE_API_KEY;
    case "anthropic":
      return !!process.env.ANTHROPIC_API_KEY;
    case "xai":
      return !!process.env.XAI_API_KEY;
    case "perplexity":
      return !!process.env.PERPLEXITY_API_KEY;
    case "openai":
      // Only check user's own key, NOT Replit's AI_INTEGRATIONS_OPENAI_API_KEY
      return !!process.env.OPENAI_API_KEY;
    default:
      return false;
  }
}

/**
 * Get all available providers with their status and cost tier
 */
export function getAvailableProviders(): ProviderInfo[] {
  return PROVIDER_DEFINITIONS.map((provider) => ({
    ...provider,
    available: checkProviderAvailability(provider.id),
  })).sort((a, b) => a.priority - b.priority);
}

/**
 * Get the best available provider based on priority
 * @param preferQuality - If true, prioritize Claude/Grok over free options
 */
export function getBestProvider(preferQuality: boolean = false): ProviderInfo | null {
  const providers = getAvailableProviders().filter((p) => p.available);

  if (providers.length === 0) {
    return null;
  }

  if (preferQuality) {
    // Quality priority: anthropic > xai > gemini > huggingface > perplexity
    const qualityOrder = ["anthropic", "xai", "gemini", "huggingface", "perplexity"];
    for (const id of qualityOrder) {
      const provider = providers.find((p) => p.id === id);
      if (provider) {
        return provider;
      }
    }
  }

  // Default: return first available (already sorted by priority)
  // Filter out credits tier unless nothing else available
  const nonCreditsProviders = providers.filter((p) => p.costTier !== "credits");
  if (nonCreditsProviders.length > 0) {
    return nonCreditsProviders[0];
  }

  return providers[0];
}

/**
 * Generate a response using providers in priority order until one succeeds
 * @param prompt - The prompt to send
 * @param preferQuality - If true, prioritize quality providers over free ones
 */
export async function generateWithPriority(
  prompt: string,
  preferQuality: boolean = false
): Promise<ProviderResponse & { providerId?: string }> {
  let providers = getAvailableProviders().filter((p) => p.available);

  // Filter out credits tier providers (avoid Replit's paid integrations)
  providers = providers.filter((p) => p.costTier !== "credits");

  if (providers.length === 0) {
    return {
      success: false,
      error: "No AI providers available. Please configure at least one API key in Settings.",
    };
  }

  if (preferQuality) {
    // Reorder to prioritize quality
    const qualityOrder = ["anthropic", "xai", "gemini", "huggingface", "perplexity"];
    providers.sort((a, b) => {
      const aIndex = qualityOrder.indexOf(a.id);
      const bIndex = qualityOrder.indexOf(b.id);
      return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex);
    });
  }

  const errors: string[] = [];

  for (const provider of providers) {
    try {
      const adapter = getProviderAdapter(provider.id);
      const response = await adapter.call(prompt, provider.models[0]);

      if (response.success) {
        return {
          ...response,
          providerId: provider.id,
        };
      }

      errors.push(`${provider.name}: ${response.error}`);
    } catch (error) {
      errors.push(
        `${provider.name}: ${error instanceof Error ? error.message : "Unknown error"}`
      );
    }
  }

  return {
    success: false,
    error: `All providers failed:\n${errors.join("\n")}`,
  };
}

/**
 * Get rate limit status for HuggingFace (the free provider with limits)
 */
export function getHuggingFaceRateLimitStatus() {
  return getRateLimitStatus();
}

/**
 * Get a summary of provider availability for display
 */
export function getProviderSummary(): {
  freeAvailable: number;
  yourKeyAvailable: number;
  total: number;
  recommended: ProviderInfo | null;
} {
  const providers = getAvailableProviders();
  const available = providers.filter((p) => p.available && p.costTier !== "credits");

  return {
    freeAvailable: available.filter((p) => p.costTier === "free").length,
    yourKeyAvailable: available.filter((p) => p.costTier === "your_key").length,
    total: available.length,
    recommended: getBestProvider(),
  };
}
