import type { ProviderResponse } from "./providerAdapters";

const HUGGINGFACE_API_URL = "https://api-inference.huggingface.co/models";
const DEFAULT_MODEL = "meta-llama/Meta-Llama-3-8B-Instruct";

let dailyRequestCount = 0;
let lastResetDate = new Date().toDateString();

const DAILY_LIMIT = 1000;

function checkAndResetDailyLimit(): void {
  const today = new Date().toDateString();
  if (today !== lastResetDate) {
    dailyRequestCount = 0;
    lastResetDate = today;
  }
}

export function getRateLimitStatus(): { used: number; limit: number; remaining: number } {
  checkAndResetDailyLimit();
  return {
    used: dailyRequestCount,
    limit: DAILY_LIMIT,
    remaining: DAILY_LIMIT - dailyRequestCount,
  };
}

export async function generateWithHuggingFace(
  prompt: string,
  model: string = DEFAULT_MODEL
): Promise<ProviderResponse> {
  checkAndResetDailyLimit();

  if (dailyRequestCount >= DAILY_LIMIT) {
    return {
      success: false,
      error: `Daily rate limit reached (${DAILY_LIMIT} requests/day). Try again tomorrow or use another provider.`,
    };
  }

  try {
    const response = await fetch(`${HUGGINGFACE_API_URL}/${model}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        inputs: prompt,
        parameters: {
          max_new_tokens: 2048,
          temperature: 0.7,
          top_p: 0.95,
          do_sample: true,
          return_full_text: false,
        },
      }),
    });

    dailyRequestCount++;

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      
      if (response.status === 503) {
        return {
          success: false,
          error: "Model is loading. Please try again in a few seconds.",
        };
      }
      
      if (response.status === 429) {
        return {
          success: false,
          error: "Rate limited by HuggingFace. Please wait a moment and try again.",
        };
      }

      return {
        success: false,
        error: errorData.error || `HuggingFace API error: ${response.status}`,
      };
    }

    const data = await response.json();

    let content = "";
    if (Array.isArray(data) && data.length > 0) {
      content = data[0].generated_text || "";
    } else if (typeof data === "object" && data.generated_text) {
      content = data.generated_text;
    } else if (typeof data === "string") {
      content = data;
    }

    const estimatedInputTokens = Math.ceil(prompt.length / 4);
    const estimatedOutputTokens = Math.ceil(content.length / 4);

    return {
      success: true,
      content,
      usage: {
        inputTokens: estimatedInputTokens,
        outputTokens: estimatedOutputTokens,
        costEstimate: "0.0000",
      },
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "HuggingFace API request failed",
    };
  }
}

export function isHuggingFaceAvailable(): boolean {
  checkAndResetDailyLimit();
  return dailyRequestCount < DAILY_LIMIT;
}
