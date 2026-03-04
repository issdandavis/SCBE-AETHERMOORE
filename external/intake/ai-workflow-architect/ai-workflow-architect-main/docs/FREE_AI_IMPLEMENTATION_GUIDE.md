# Free-First AI Strategy - Implementation Guide

This guide provides practical code templates and implementation steps for developers working on the free-first AI strategy.

---

## Quick Start

### 1. Install Ollama (Development)

```bash
# On macOS/Linux
curl https://ollama.ai/install.sh | sh

# Pull essential models
ollama pull llama3.1:8b
ollama pull codellama:13b
ollama pull mistral:7b
ollama pull phi-3

# Start server
ollama serve
```

### 2. Update Environment Variables

```bash
# .env or Replit Secrets

# Ollama (Free)
OLLAMA_BASE_URL=http://localhost:11434

# Groq (Cheap fallback)
GROQ_API_KEY=gsk_your_key_here

# Together AI (Cheap fallback)
TOGETHER_API_KEY=your_together_key

# HuggingFace (Free tier)
HUGGINGFACE_TOKEN=hf_your_token
```

---

## File Structure

```
server/
├── services/
│   ├── free-model-config.ts        [NEW] Model definitions
│   ├── model-selector.ts           [NEW] Smart selection logic
│   ├── cost-calculator.ts          [NEW] Cost tracking
│   ├── providerAdapters.ts         [UPDATE] Add new adapters
│   └── ollama-client.ts            [NEW] Ollama integration
├── middleware/
│   └── costGovernor.ts             [UPDATE] Add free-first logic
└── routes/
    └── models.ts                   [NEW] Model management API

shared/
└── pricing.ts                      [NEW] Pricing constants

client/src/
├── pages/
│   ├── CostDashboard.tsx           [NEW] Cost monitoring UI
│   └── ModelSettings.tsx           [NEW] Model configuration
└── components/
    ├── CostTracker.tsx             [NEW] Real-time cost display
    └── ModelSelector.tsx           [NEW] Model selection UI
```

---

## Implementation Templates

### 1. Free Model Configuration

**File**: `server/services/free-model-config.ts`

```typescript
export interface ModelConfig {
  provider: string;
  model: string;
  costPer1kInputTokens: number;
  costPer1kOutputTokens: number;
  speedRating: 'very-fast' | 'fast' | 'medium' | 'slow';
  qualityRating: 'excellent' | 'good' | 'decent' | 'basic';
  bestFor: string[];
}

export const FREE_MODELS: Record<string, ModelConfig> = {
  'ollama/llama3.1:8b': {
    provider: 'ollama',
    model: 'llama3.1:8b',
    costPer1kInputTokens: 0,
    costPer1kOutputTokens: 0,
    speedRating: 'fast',
    qualityRating: 'good',
    bestFor: ['chat', 'general'],
  },
  'ollama/codellama:13b': {
    provider: 'ollama',
    model: 'codellama:13b',
    costPer1kInputTokens: 0,
    costPer1kOutputTokens: 0,
    speedRating: 'medium',
    qualityRating: 'excellent',
    bestFor: ['code', 'debugging'],
  },
  'ollama/mistral:7b': {
    provider: 'ollama',
    model: 'mistral:7b',
    costPer1kInputTokens: 0,
    costPer1kOutputTokens: 0,
    speedRating: 'fast',
    qualityRating: 'good',
    bestFor: ['analysis', 'reasoning'],
  },
  'ollama/phi-3': {
    provider: 'ollama',
    model: 'phi-3',
    costPer1kInputTokens: 0,
    costPer1kOutputTokens: 0,
    speedRating: 'very-fast',
    qualityRating: 'decent',
    bestFor: ['quick-responses', 'simple-tasks'],
  },
};

export const CHEAP_MODELS: Record<string, ModelConfig> = {
  'groq/llama-3.1-70b': {
    provider: 'groq',
    model: 'llama-3.1-70b-versatile',
    costPer1kInputTokens: 0.00059,
    costPer1kOutputTokens: 0.00079,
    speedRating: 'very-fast',
    qualityRating: 'excellent',
    bestFor: ['code', 'chat', 'analysis'],
  },
  'groq/mixtral-8x7b': {
    provider: 'groq',
    model: 'mixtral-8x7b-32768',
    costPer1kInputTokens: 0.00024,
    costPer1kOutputTokens: 0.00024,
    speedRating: 'very-fast',
    qualityRating: 'good',
    bestFor: ['chat', 'general'],
  },
  'together/qwen-2.5-72b': {
    provider: 'together',
    model: 'Qwen/Qwen2.5-72B-Instruct-Turbo',
    costPer1kInputTokens: 0.0009,
    costPer1kOutputTokens: 0.0009,
    speedRating: 'fast',
    qualityRating: 'excellent',
    bestFor: ['analysis', 'reasoning', 'code'],
  },
  'perplexity/pplx-7b': {
    provider: 'perplexity',
    model: 'pplx-7b-online',
    costPer1kInputTokens: 0.00005,
    costPer1kOutputTokens: 0.00005,
    speedRating: 'fast',
    qualityRating: 'good',
    bestFor: ['search', 'research', 'web'],
  },
};

export const EXPENSIVE_MODELS: Record<string, ModelConfig> = {
  'openai/gpt-4o': {
    provider: 'openai',
    model: 'gpt-4o',
    costPer1kInputTokens: 0.003,
    costPer1kOutputTokens: 0.01,
    speedRating: 'medium',
    qualityRating: 'excellent',
    bestFor: ['complex-reasoning', 'creative-writing'],
  },
  'anthropic/claude-3-sonnet': {
    provider: 'anthropic',
    model: 'claude-3-sonnet-20240229',
    costPer1kInputTokens: 0.003,
    costPer1kOutputTokens: 0.015,
    speedRating: 'medium',
    qualityRating: 'excellent',
    bestFor: ['analysis', 'coding', 'writing'],
  },
};

export function isModelFree(modelKey: string): boolean {
  return modelKey in FREE_MODELS;
}

export function isModelCheap(modelKey: string): boolean {
  return modelKey in CHEAP_MODELS;
}

export function isModelExpensive(modelKey: string): boolean {
  return modelKey in EXPENSIVE_MODELS;
}
```

---

### 2. Model Selector

**File**: `server/services/model-selector.ts`

```typescript
import { FREE_MODELS, CHEAP_MODELS, EXPENSIVE_MODELS } from './free-model-config';

export type TaskType = 'code' | 'chat' | 'analysis' | 'search' | 'general';
export type TaskComplexity = 'simple' | 'medium' | 'complex';

export interface ModelSelection {
  provider: string;
  model: string;
  reason: string;
  tier: 'free' | 'cheap' | 'expensive';
  estimatedCost: number;
}

export interface SelectionOptions {
  taskType: TaskType;
  complexity?: TaskComplexity;
  userPreference?: string;
  maxCostPer1k?: number;
  requireQuality?: 'decent' | 'good' | 'excellent';
}

export async function selectBestModel(
  options: SelectionOptions
): Promise<ModelSelection> {
  const {
    taskType,
    complexity = 'medium',
    userPreference,
    maxCostPer1k = 0.001, // Default max: $0.001/1k tokens
    requireQuality = 'good',
  } = options;

  // 1. Check user preference first
  if (userPreference) {
    const modelConfig = findModelConfig(userPreference);
    if (modelConfig) {
      return {
        provider: modelConfig.provider,
        model: modelConfig.model,
        reason: 'User specified preference',
        tier: getTier(userPreference),
        estimatedCost: modelConfig.costPer1kInputTokens,
      };
    }
  }

  // 2. Try free models first
  const freeModel = findBestFreeModel(taskType, complexity, requireQuality);
  if (freeModel && await isOllamaAvailable()) {
    return {
      provider: freeModel.provider,
      model: freeModel.model,
      reason: `Free model optimized for ${taskType}`,
      tier: 'free',
      estimatedCost: 0,
    };
  }

  // 3. Fall back to cheap models
  const cheapModel = findBestCheapModel(taskType, complexity, maxCostPer1k);
  if (cheapModel) {
    return {
      provider: cheapModel.provider,
      model: cheapModel.model,
      reason: `Affordable cloud model for ${taskType} (${cheapModel.costPer1kInputTokens * 1000}/1M tokens)`,
      tier: 'cheap',
      estimatedCost: cheapModel.costPer1kInputTokens,
    };
  }

  // 4. Last resort: expensive models (should rarely happen)
  console.warn('No free or cheap models available, falling back to expensive model');
  const expensiveModel = findBestExpensiveModel(taskType);
  return {
    provider: expensiveModel.provider,
    model: expensiveModel.model,
    reason: `Premium model required for ${taskType}`,
    tier: 'expensive',
    estimatedCost: expensiveModel.costPer1kInputTokens,
  };
}

function findBestFreeModel(
  taskType: TaskType,
  complexity: TaskComplexity,
  minQuality: string
) {
  const candidates = Object.values(FREE_MODELS).filter(
    (m) => m.bestFor.includes(taskType) || m.bestFor.includes('general')
  );

  // Sort by quality and speed
  return candidates.sort((a, b) => {
    const qualityScore = { excellent: 3, good: 2, decent: 1, basic: 0 };
    const speedScore = { 'very-fast': 3, fast: 2, medium: 1, slow: 0 };

    const scoreA = qualityScore[a.qualityRating] + speedScore[a.speedRating];
    const scoreB = qualityScore[b.qualityRating] + speedScore[b.speedRating];

    return scoreB - scoreA;
  })[0];
}

function findBestCheapModel(
  taskType: TaskType,
  complexity: TaskComplexity,
  maxCost: number
) {
  const candidates = Object.values(CHEAP_MODELS).filter(
    (m) =>
      m.costPer1kInputTokens <= maxCost &&
      (m.bestFor.includes(taskType) || m.bestFor.includes('general'))
  );

  return candidates.sort((a, b) => {
    // Sort by quality first, then cost
    const qualityScore = { excellent: 3, good: 2, decent: 1, basic: 0 };
    const qualityDiff = qualityScore[b.qualityRating] - qualityScore[a.qualityRating];

    if (qualityDiff !== 0) return qualityDiff;
    return a.costPer1kInputTokens - b.costPer1kInputTokens;
  })[0];
}

function findBestExpensiveModel(taskType: TaskType) {
  const candidates = Object.values(EXPENSIVE_MODELS).filter(
    (m) => m.bestFor.includes(taskType) || m.bestFor.includes('general')
  );

  return candidates[0] || Object.values(EXPENSIVE_MODELS)[0];
}

async function isOllamaAvailable(): Promise<boolean> {
  try {
    const ollamaUrl = process.env.OLLAMA_BASE_URL || 'http://localhost:11434';
    const response = await fetch(`${ollamaUrl}/api/tags`, {
      signal: AbortSignal.timeout(2000),
    });
    return response.ok;
  } catch {
    return false;
  }
}

function findModelConfig(modelKey: string) {
  return (
    FREE_MODELS[modelKey] ||
    CHEAP_MODELS[modelKey] ||
    EXPENSIVE_MODELS[modelKey]
  );
}

function getTier(modelKey: string): 'free' | 'cheap' | 'expensive' {
  if (modelKey in FREE_MODELS) return 'free';
  if (modelKey in CHEAP_MODELS) return 'cheap';
  return 'expensive';
}
```

---

### 3. Ollama Adapter

**File**: `server/services/ollama-client.ts`

```typescript
import { ProviderResponse } from './providerAdapters';

export class OllamaClient {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || process.env.OLLAMA_BASE_URL || 'http://localhost:11434';
  }

  async generate(
    model: string,
    prompt: string,
    options?: {
      temperature?: number;
      maxTokens?: number;
      stream?: boolean;
    }
  ): Promise<ProviderResponse> {
    try {
      const response = await fetch(`${this.baseUrl}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model,
          prompt,
          stream: false,
          options: {
            temperature: options?.temperature || 0.7,
            num_predict: options?.maxTokens || 2048,
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`Ollama API error: ${response.statusText}`);
      }

      const data = await response.json();

      return {
        success: true,
        content: data.response,
        usage: {
          inputTokens: data.prompt_eval_count || 0,
          outputTokens: data.eval_count || 0,
          costEstimate: '0.00', // FREE!
        },
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Ollama request failed',
      };
    }
  }

  async listModels(): Promise<string[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/tags`);
      const data = await response.json();
      return data.models?.map((m: any) => m.name) || [];
    } catch {
      return [];
    }
  }

  async pullModel(model: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/pull`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: model }),
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  async isAvailable(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/tags`, {
        signal: AbortSignal.timeout(2000),
      });
      return response.ok;
    } catch {
      return false;
    }
  }
}

// Add to providerAdapters.ts
export class OllamaAdapter extends BaseProviderAdapter {
  private client: OllamaClient;

  constructor() {
    super('Ollama', 'available');
    this.client = new OllamaClient();
  }

  async call(prompt: string, model: string): Promise<ProviderResponse> {
    const isAvailable = await this.client.isAvailable();
    
    if (!isAvailable) {
      return {
        success: false,
        error: 'Ollama is not running. Please start Ollama with: ollama serve',
      };
    }

    return this.client.generate(model, prompt);
  }
}
```

---

### 4. Cost Calculator

**File**: `server/services/cost-calculator.ts`

```typescript
import { FREE_MODELS, CHEAP_MODELS, EXPENSIVE_MODELS } from './free-model-config';

export interface CostCalculation {
  inputTokens: number;
  outputTokens: number;
  inputCost: number;
  outputCost: number;
  totalCost: number;
  provider: string;
  model: string;
  tier: 'free' | 'cheap' | 'expensive';
}

export function calculateCost(
  provider: string,
  model: string,
  inputTokens: number,
  outputTokens: number
): CostCalculation {
  const modelKey = `${provider}/${model}`;
  const modelConfig =
    FREE_MODELS[modelKey] ||
    CHEAP_MODELS[modelKey] ||
    EXPENSIVE_MODELS[modelKey];

  if (!modelConfig) {
    console.warn(`Unknown model: ${modelKey}, assuming expensive pricing`);
    return {
      inputTokens,
      outputTokens,
      inputCost: (inputTokens / 1000) * 0.003,
      outputCost: (outputTokens / 1000) * 0.01,
      totalCost: (inputTokens / 1000) * 0.003 + (outputTokens / 1000) * 0.01,
      provider,
      model,
      tier: 'expensive',
    };
  }

  const inputCost = (inputTokens / 1000) * modelConfig.costPer1kInputTokens;
  const outputCost = (outputTokens / 1000) * modelConfig.costPer1kOutputTokens;

  let tier: 'free' | 'cheap' | 'expensive' = 'expensive';
  if (modelKey in FREE_MODELS) tier = 'free';
  else if (modelKey in CHEAP_MODELS) tier = 'cheap';

  return {
    inputTokens,
    outputTokens,
    inputCost,
    outputCost,
    totalCost: inputCost + outputCost,
    provider,
    model,
    tier,
  };
}

export async function estimateMonthlyCost(
  userId: string,
  storage: any
): Promise<{ total: number; byProvider: Record<string, number> }> {
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  const records = await storage.getUsageRecords({
    userId,
    startDate: thirtyDaysAgo,
  });

  const byProvider: Record<string, number> = {};
  let total = 0;

  for (const record of records) {
    const cost = calculateCost(
      record.provider,
      record.model,
      record.inputTokens,
      record.outputTokens
    );

    byProvider[record.provider] = (byProvider[record.provider] || 0) + cost.totalCost;
    total += cost.totalCost;
  }

  return { total, byProvider };
}

export function formatCost(costUsd: number): string {
  if (costUsd === 0) return 'FREE';
  if (costUsd < 0.01) return `$${costUsd.toFixed(4)}`;
  return `$${costUsd.toFixed(2)}`;
}
```

---

### 5. Update Cost Governor Middleware

**File**: `server/middleware/costGovernor.ts` (UPDATE)

```typescript
// Add to existing costGovernor.ts

import { selectBestModel } from '../services/model-selector';
import { calculateCost } from '../services/cost-calculator';

export async function enforceFreeTierFirst(
  req: Request,
  res: Response,
  next: NextFunction
) {
  const { taskType, model: requestedModel } = req.body;
  
  // If user explicitly requested a model, check if they can afford it
  if (requestedModel) {
    const modelTier = getModelTier(requestedModel);
    
    if (modelTier === 'expensive') {
      const hasUserKey = await hasUserProvidedKey(req.user.id, getProvider(requestedModel));
      
      if (!hasUserKey) {
        return res.status(403).json({
          error: 'Expensive model requires your own API key',
          suggestion: 'Add your API key in Settings, or use a free/cheap model',
          freeAlternatives: suggestFreeAlternatives(taskType),
        });
      }
    }
  }
  
  // Auto-select best free model if no model specified
  if (!requestedModel && taskType) {
    const selection = await selectBestModel({ taskType });
    req.body.provider = selection.provider;
    req.body.model = selection.model;
    req.body.modelSelectionReason = selection.reason;
  }
  
  next();
}

function suggestFreeAlternatives(taskType: string): string[] {
  const suggestions: Record<string, string[]> = {
    code: ['ollama/codellama:13b', 'groq/llama-3.1-70b'],
    chat: ['ollama/llama3.1:8b', 'groq/mixtral-8x7b'],
    analysis: ['ollama/mistral:7b', 'together/qwen-2.5-72b'],
    search: ['perplexity/pplx-7b', 'ollama/llama3.1:8b'],
  };
  
  return suggestions[taskType] || suggestions.chat;
}
```

---

## Testing

### Test Ollama Connection

```bash
# Test if Ollama is running
curl http://localhost:11434/api/tags

# Test a simple generation
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.1:8b",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

### Test Model Selection

```typescript
// test/model-selector.test.ts
import { selectBestModel } from '../server/services/model-selector';

describe('Model Selection', () => {
  it('should prefer free models for code tasks', async () => {
    const result = await selectBestModel({ taskType: 'code' });
    expect(result.tier).toBe('free');
    expect(result.model).toContain('codellama');
  });

  it('should fall back to cheap models if Ollama unavailable', async () => {
    // Mock Ollama as unavailable
    jest.spyOn(global, 'fetch').mockRejectedValue(new Error('Connection refused'));
    
    const result = await selectBestModel({ taskType: 'code' });
    expect(result.tier).toBe('cheap');
    expect(result.provider).toBe('groq');
  });

  it('should respect user preference', async () => {
    const result = await selectBestModel({
      taskType: 'code',
      userPreference: 'groq/llama-3.1-70b',
    });
    expect(result.model).toBe('llama-3.1-70b-versatile');
  });
});
```

---

## Deployment Checklist

- [ ] Install Ollama on production server
- [ ] Pull required models (llama3.1:8b, codellama:13b, mistral:7b)
- [ ] Set OLLAMA_BASE_URL in environment
- [ ] Add Groq API key for fallback
- [ ] Configure cost limits in database
- [ ] Test model selection logic
- [ ] Verify free models work end-to-end
- [ ] Monitor costs in production

---

## Monitoring

### Key Metrics to Track

```typescript
// Log these metrics
{
  freeModelUsagePercent: 95, // Target: >90%
  averageCostPerUser: 0.50,  // Target: <$5/month
  ollamaAvailability: 99.5,  // Target: >99%
  averageResponseTime: 850,  // Target: <2000ms
  costSavingsVsOpenAI: 180   // $ saved per month
}
```

---

## Troubleshooting

### Ollama Not Starting
```bash
# Check if Ollama is installed
ollama --version

# Check if service is running
ps aux | grep ollama

# Restart Ollama
killall ollama
ollama serve
```

### Models Not Found
```bash
# List installed models
ollama list

# Pull missing model
ollama pull llama3.1:8b
```

### Slow Response Times
```bash
# Check model size (smaller = faster)
ollama show llama3.1:8b

# Consider using smaller models for simple tasks
ollama pull phi-3  # Much faster for simple queries
```

---

## Next Steps

1. Implement `free-model-config.ts` with all model definitions
2. Create `model-selector.ts` with intelligent selection logic
3. Add `ollama-client.ts` for Ollama integration
4. Update `costGovernor.ts` middleware
5. Test locally with Ollama
6. Deploy to staging
7. Monitor costs and performance
8. Roll out to production

---

**Happy Coding! 🚀**
