import type { ProviderResponse } from "./providerAdapters";
import { PROVIDER_CONFIGS } from "./free-models-config";

const config = PROVIDER_CONFIGS.ollama;

let isHealthy: boolean | null = null;
let lastHealthCheck = 0;
const HEALTH_CHECK_INTERVAL = 30000;

export async function checkOllamaHealth(): Promise<boolean> {
  const now = Date.now();
  if (isHealthy !== null && now - lastHealthCheck < HEALTH_CHECK_INTERVAL) {
    return isHealthy;
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${config.baseUrl}${config.healthEndpoint}`, {
      method: "GET",
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    isHealthy = response.ok;
    lastHealthCheck = now;
    return isHealthy;
  } catch {
    isHealthy = false;
    lastHealthCheck = now;
    return false;
  }
}

export async function listOllamaModels(): Promise<string[]> {
  try {
    const response = await fetch(`${config.baseUrl}/api/tags`);
    if (!response.ok) return [];
    const data = await response.json();
    return (data.models || []).map((m: { name: string }) => m.name);
  } catch {
    return [];
  }
}

export async function generateWithOllama(
  prompt: string,
  model: string = "llama3.1:8b"
): Promise<ProviderResponse> {
  const isAvailable = await checkOllamaHealth();
  if (!isAvailable) {
    return {
      success: false,
      error: "Ollama is not available. Please ensure it's running locally.",
    };
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), config.defaultTimeout);

    const response = await fetch(`${config.baseUrl}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        prompt,
        stream: false,
        options: {
          temperature: 0.7,
          top_p: 0.95,
          num_predict: 2048,
        },
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        error: errorData.error || `Ollama error: ${response.status}`,
      };
    }

    const data = await response.json();
    const content = data.response || "";

    const estimatedInputTokens = Math.ceil(prompt.length / 4);
    const estimatedOutputTokens = Math.ceil(content.length / 4);

    return {
      success: true,
      content,
      usage: {
        inputTokens: data.prompt_eval_count || estimatedInputTokens,
        outputTokens: data.eval_count || estimatedOutputTokens,
        costEstimate: "0.0000",
      },
    };
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      return {
        success: false,
        error: "Ollama request timed out. Try a shorter prompt or smaller model.",
      };
    }
    return {
      success: false,
      error: error instanceof Error ? error.message : "Ollama request failed",
    };
  }
}

export function isOllamaAvailable(): boolean {
  return isHealthy === true;
}

export function getOllamaBaseUrl(): string {
  return config.baseUrl || "http://localhost:11434";
}
