export interface ModelConfig {
  id: string;
  name: string;
  provider: "ollama" | "groq" | "huggingface";
  contextLength: number;
  costPer1kTokens: number;
  capabilities: ("chat" | "code" | "reasoning" | "vision")[];
  priority: number;
}

export interface ProviderConfig {
  name: string;
  type: "local" | "api";
  baseUrl?: string;
  apiKeyEnvVar?: string;
  healthEndpoint?: string;
  defaultTimeout: number;
  costTier: "free" | "cheap" | "standard" | "premium";
}

export const PROVIDER_CONFIGS: Record<string, ProviderConfig> = {
  ollama: {
    name: "Ollama",
    type: "local",
    baseUrl: process.env.OLLAMA_BASE_URL || "http://localhost:11434",
    healthEndpoint: "/api/tags",
    defaultTimeout: 60000,
    costTier: "free",
  },
  groq: {
    name: "Groq",
    type: "api",
    apiKeyEnvVar: "GROQ_API_KEY",
    defaultTimeout: 30000,
    costTier: "cheap",
  },
  huggingface: {
    name: "HuggingFace",
    type: "api",
    defaultTimeout: 45000,
    costTier: "free",
  },
};

export const FREE_MODELS: ModelConfig[] = [
  {
    id: "llama3.1:8b",
    name: "Llama 3.1 8B",
    provider: "ollama",
    contextLength: 8192,
    costPer1kTokens: 0,
    capabilities: ["chat", "code", "reasoning"],
    priority: 1,
  },
  {
    id: "mistral:7b",
    name: "Mistral 7B",
    provider: "ollama",
    contextLength: 8192,
    costPer1kTokens: 0,
    capabilities: ["chat", "code"],
    priority: 2,
  },
  {
    id: "codellama:13b",
    name: "Code Llama 13B",
    provider: "ollama",
    contextLength: 16384,
    costPer1kTokens: 0,
    capabilities: ["code"],
    priority: 3,
  },
  {
    id: "llama-3.3-70b-versatile",
    name: "Llama 3.3 70B Versatile",
    provider: "groq",
    contextLength: 32768,
    costPer1kTokens: 0.00059,
    capabilities: ["chat", "code", "reasoning"],
    priority: 10,
  },
  {
    id: "llama3-8b-8192",
    name: "Llama 3 8B",
    provider: "groq",
    contextLength: 8192,
    costPer1kTokens: 0.00005,
    capabilities: ["chat", "code"],
    priority: 11,
  },
  {
    id: "mixtral-8x7b-32768",
    name: "Mixtral 8x7B",
    provider: "groq",
    contextLength: 32768,
    costPer1kTokens: 0.00024,
    capabilities: ["chat", "code", "reasoning"],
    priority: 12,
  },
  {
    id: "gemma2-9b-it",
    name: "Gemma 2 9B",
    provider: "groq",
    contextLength: 8192,
    costPer1kTokens: 0.0002,
    capabilities: ["chat"],
    priority: 13,
  },
];

export function getModelsByProvider(provider: string): ModelConfig[] {
  return FREE_MODELS.filter((m) => m.provider === provider).sort(
    (a, b) => a.priority - b.priority
  );
}

export function getModelById(modelId: string): ModelConfig | undefined {
  return FREE_MODELS.find((m) => m.id === modelId);
}

export function getCheapestModelForCapability(
  capability: ModelConfig["capabilities"][number]
): ModelConfig | undefined {
  return FREE_MODELS.filter((m) => m.capabilities.includes(capability)).sort(
    (a, b) => a.costPer1kTokens - b.costPer1kTokens
  )[0];
}

export function getProviderPriority(): string[] {
  return ["ollama", "huggingface", "groq"];
}

export function estimateTokens(text: string): number {
  return Math.ceil(text.length / 4);
}

export function estimateCost(
  modelId: string,
  inputTokens: number,
  outputTokens: number
): number {
  const model = getModelById(modelId);
  if (!model) return 0;
  const totalTokens = inputTokens + outputTokens;
  return (totalTokens / 1000) * model.costPer1kTokens;
}
