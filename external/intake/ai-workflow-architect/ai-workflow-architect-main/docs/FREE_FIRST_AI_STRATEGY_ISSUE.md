# GitHub Issue: Implement Free-First AI Model Strategy to Reduce Costs

**Labels**: `enhancement`, `cost-optimization`, `ai-providers`
**Priority**: High
**Effort**: 4 weeks
**Impact**: Massive cost savings ($180/year per user)

---

## 🎯 Overview

This issue tracks the implementation of a **free-first AI model strategy** to make the AI Orchestration Hub affordable and sustainable. The goal is to minimize or eliminate expensive API costs (especially OpenAI) by prioritizing free and open-source models while maintaining powerful AI capabilities.

## 💡 Problem Statement

Currently, the app relies on expensive commercial AI providers:
- **OpenAI GPT-4o**: $0.003/1k input tokens ($3,000 per 1M tokens)
- **Anthropic Claude**: $0.003-0.015/1k tokens
- **Risk**: Users can quickly accumulate $50-500/month bills without realizing it

**Solution**: Implement a tiered model strategy with free/cheap options as defaults.

---

## 🚀 Proposed Architecture

### Tier 1: Completely Free (Primary) 🎉
Use **Ollama** running locally or on the server:
- **codellama:13b** - FREE, excellent for code tasks
- **llama3.1:8b** - FREE, fast general chat
- **mistral:7b** - FREE, good reasoning
- **phi-3** - FREE, very fast responses

**Cost**: $0 (only server costs if self-hosted)

### Tier 2: Cheap Fallback (When Free Unavailable) 💰
Use affordable commercial APIs:
- **Groq (llama-3.1-70b)**: $0.00059/1k input (5x cheaper than OpenAI)
- **Together AI (qwen-2.5-72b)**: $0.0009/1k input (3x cheaper)
- **Perplexity (pplx-7b)**: $0.00005/1k input (60x cheaper)
- **HuggingFace Free Inference API**: 1,000 requests/day FREE

**Cost**: $0-5/month for typical usage

### Tier 3: User-Provided Keys Only 🔑
- **OpenAI, Anthropic, Google**: Only if user brings their own API key
- App never charges users for these expensive services
- Users control their own spending

---

## 📋 Implementation Checklist

### Phase 1: Model Configuration (Week 1)
- [ ] Create `server/services/free-model-config.ts`
  - [ ] Define FREE_MODELS constant with Ollama models
  - [ ] Define CHEAP_MODELS constant with Groq/Together/Perplexity
  - [ ] Define EXPENSIVE_MODELS_TO_AVOID constant
  - [ ] Add model selection logic based on task type
- [ ] Update `server/services/providerAdapters.ts`
  - [ ] Add OllamaAdapter class for local model calls
  - [ ] Add GroqAdapter class for Groq API
  - [ ] Add TogetherAdapter class for Together AI
  - [ ] Add HuggingFaceAdapter class for free inference
- [ ] Create model pricing matrix in `shared/pricing.ts`

### Phase 2: Cost Calculator Enhancement (Week 1)
- [ ] Update `server/middleware/costGovernor.ts`
  - [ ] Implement intelligent model selection (prefer free models)
  - [ ] Add automatic fallback from expensive to cheap models
  - [ ] Track cost per provider and model
  - [ ] Alert users when approaching budget limits
- [ ] Create `server/services/cost-calculator.ts`
  - [ ] Calculate cost for each provider/model
  - [ ] Suggest cheapest model for given task
  - [ ] Estimate monthly costs based on usage patterns
  - [ ] Provide cost breakdown by provider

### Phase 3: Ollama Integration (Week 2)
- [ ] Add Ollama setup documentation
  - [ ] Installation instructions for Replit/VPS
  - [ ] Model pulling commands
  - [ ] Configuration in .env
- [ ] Implement OllamaAdapter
  - [ ] Connect to local Ollama API
  - [ ] Handle model loading and unloading
  - [ ] Implement retry logic for model startup
  - [ ] Add fallback to cloud models if Ollama unavailable
- [ ] Test Ollama integration
  - [ ] Code generation with codellama
  - [ ] Chat with llama3.1
  - [ ] Reasoning with mistral

### Phase 4: Cheap Cloud Fallbacks (Week 2)
- [ ] Implement Groq integration
  - [ ] Add GROQ_API_KEY to environment
  - [ ] Create GroqAdapter with rate limiting
  - [ ] Test llama-3.1-70b and mixtral-8x7b
- [ ] Implement Together AI integration
  - [ ] Add TOGETHER_API_KEY to environment
  - [ ] Create TogetherAdapter
  - [ ] Test qwen-2.5-72b and llama-3.1-405b
- [ ] Implement HuggingFace free tier
  - [ ] Use HuggingFace Inference API
  - [ ] Handle rate limits (1000 req/day)
  - [ ] Add caching for repeated queries

### Phase 5: Smart Model Selection (Week 3)
- [ ] Create `server/services/model-selector.ts`
  - [ ] Analyze task type (code, chat, search, analysis)
  - [ ] Select optimal free model for task
  - [ ] Fallback to cheap model if free unavailable
  - [ ] Never use expensive models without explicit approval
- [ ] Implement task-based routing:
  - [ ] **Code tasks** → codellama:13b (free) or groq/llama-3.1-70b (cheap)
  - [ ] **Chat tasks** → llama3.1:8b (free) or groq/mixtral-8x7b (cheap)
  - [ ] **Search tasks** → perplexity/pplx-7b (basically free)
  - [ ] **Analysis tasks** → mistral:7b (free) or together/qwen-2.5-72b (cheap)

### Phase 6: Cost Dashboard UI (Week 3)
- [ ] Create `client/src/pages/CostDashboard.tsx`
  - [ ] Real-time cost tracking by provider
  - [ ] Monthly spending forecast
  - [ ] Cost breakdown by model
  - [ ] Alerts at 50%, 80%, 100% of budget
- [ ] Add cost display to Roundtable UI
  - [ ] Show cost per AI turn
  - [ ] Display cumulative session cost
  - [ ] Show which model was used (free/cheap/expensive)
- [ ] Create budget management UI
  - [ ] Set daily/monthly budgets
  - [ ] Configure auto-fallback rules
  - [ ] Enable/disable expensive models

### Phase 7: User-Provided Keys (Week 4)
- [ ] Update `server/services/vault.ts`
  - [ ] Store user-provided API keys securely
  - [ ] Support OpenAI, Anthropic, Google keys
  - [ ] Never charge user's account for these calls
- [ ] Add API key management UI
  - [ ] Page for users to add their own keys
  - [ ] Test connection to verify keys
  - [ ] Toggle between platform keys and user keys
- [ ] Update cost tracking
  - [ ] Track costs separately for user-provided keys
  - [ ] Show "Your API Key" vs "Platform Costs"

### Phase 8: Documentation (Week 4)
- [ ] Create `docs/FREE_AI_STRATEGY.md`
  - [ ] Explain free-first philosophy
  - [ ] Document all supported free models
  - [ ] Show cost comparison vs OpenAI
  - [ ] Provide Ollama setup guide
- [ ] Update README.md
  - [ ] Highlight free tier availability
  - [ ] Show estimated costs ($0-5/month)
  - [ ] Link to cost optimization docs
- [ ] Create migration guide
  - [ ] How to switch from OpenAI to free models
  - [ ] Performance comparison
  - [ ] When to use each tier

---

## 💰 Cost Comparison

| Provider | Model | Input Cost (per 1k tokens) | Output Cost (per 1k tokens) | Relative to OpenAI |
|----------|-------|---------------------------|----------------------------|-------------------|
| **FREE TIER** | | | | |
| Ollama | llama3.1:8b | $0.00 | $0.00 | ∞x cheaper |
| Ollama | codellama:13b | $0.00 | $0.00 | ∞x cheaper |
| HuggingFace | Free API | $0.00 | $0.00 | ∞x cheaper |
| **CHEAP TIER** | | | | |
| Groq | llama-3.1-70b | $0.00059 | $0.00079 | 5x cheaper |
| Groq | mixtral-8x7b | $0.00024 | $0.00024 | 12x cheaper |
| Together | qwen-2.5-72b | $0.00090 | $0.00090 | 3x cheaper |
| Perplexity | pplx-7b | $0.00005 | $0.00005 | 60x cheaper |
| **EXPENSIVE** | | | | |
| OpenAI | gpt-4o | $0.00300 | $0.01000 | baseline |
| Anthropic | claude-3-sonnet | $0.00300 | $0.01500 | similar |
| Anthropic | claude-3-opus | $0.01500 | $0.07500 | 5x more |

### Real-World Example
For **1 million tokens** (typical monthly usage):
- **Ollama (self-hosted)**: $0 🎉
- **Groq (llama-3.1-70b)**: $0.59
- **Together (qwen-2.5-72b)**: $0.90
- **OpenAI (gpt-4o)**: $3.00
- **Anthropic (claude-3-opus)**: $15.00

**Savings**: Up to $15/month per user or $180/year! 💸

---

## 🔧 Technical Implementation Details

### Ollama Setup (Self-Hosted)
```bash
# Install Ollama on server/Replit
curl https://ollama.ai/install.sh | sh

# Pull recommended models
ollama pull llama3.1:8b      # General chat
ollama pull codellama:13b    # Code tasks
ollama pull mistral:7b       # Reasoning
ollama pull phi-3            # Fast responses

# Start Ollama server
ollama serve
```

### Environment Variables
```bash
# Add to .env or Replit Secrets

# Free Tier (Ollama)
OLLAMA_BASE_URL=http://localhost:11434

# Cheap Tier (Commercial but affordable)
GROQ_API_KEY=your_groq_key_here
TOGETHER_API_KEY=your_together_key_here
HUGGINGFACE_TOKEN=your_hf_token_here

# Expensive Tier (User-provided only)
# Do NOT set these as platform defaults:
# OPENAI_API_KEY=...
# ANTHROPIC_API_KEY=...
```

### Model Selection Logic
```typescript
// server/services/model-selector.ts
export interface TaskType {
  type: 'code' | 'chat' | 'search' | 'analysis';
  complexity: 'simple' | 'medium' | 'complex';
}

export function selectModel(task: TaskType, userPreference?: string) {
  // 1. Check if user has explicit preference
  if (userPreference) return userPreference;
  
  // 2. Try free models first
  const freeModel = getFreeModelForTask(task);
  if (isOllamaAvailable()) return { provider: 'ollama', model: freeModel };
  
  // 3. Fallback to cheap cloud models
  const cheapModel = getCheapModelForTask(task);
  return cheapModel;
  
  // 4. NEVER auto-select expensive models
}

function getFreeModelForTask(task: TaskType): string {
  switch (task.type) {
    case 'code':
      return task.complexity === 'complex' ? 'codellama:13b' : 'codellama:7b';
    case 'chat':
      return 'llama3.1:8b';
    case 'analysis':
      return 'mistral:7b';
    case 'search':
      return 'llama3.1:8b';
  }
}

function getCheapModelForTask(task: TaskType) {
  switch (task.type) {
    case 'code':
      return { provider: 'groq', model: 'llama-3.1-70b' };
    case 'chat':
      return { provider: 'groq', model: 'mixtral-8x7b' };
    case 'search':
      return { provider: 'perplexity', model: 'pplx-7b-online' };
    case 'analysis':
      return { provider: 'together', model: 'qwen-2.5-72b' };
  }
}
```

### Cost Tracking Example
```typescript
// Track every AI call
await trackCost({
  provider: 'ollama',
  model: 'llama3.1:8b',
  inputTokens: 150,
  outputTokens: 80,
  costUsd: 0.00, // FREE!
  userId,
  projectId,
  timestamp: new Date(),
});

// Calculate and warn about approaching limits
const monthlyCost = await calculateMonthlyCost(userId);
if (monthlyCost > 4.00) {
  await sendCostAlert(userId, {
    current: monthlyCost,
    limit: 5.00,
    percentUsed: 80,
  });
}
```

### Provider Adapter Structure
```typescript
// server/services/providerAdapters.ts

export class OllamaAdapter extends BaseProviderAdapter {
  constructor() {
    super('Ollama', process.env.OLLAMA_BASE_URL || 'http://localhost:11434');
  }

  async call(prompt: string, model: string): Promise<ProviderResponse> {
    try {
      const response = await fetch(`${this.apiKey}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model, prompt }),
      });

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
      // Fallback to cheap cloud model
      return this.fallbackToCheapModel(prompt, model);
    }
  }

  private async fallbackToCheapModel(prompt: string, model: string) {
    const groqAdapter = new GroqAdapter(process.env.GROQ_API_KEY);
    return groqAdapter.call(prompt, 'llama-3.1-70b');
  }
}
```

---

## 🎯 Success Metrics

- [ ] **90%+ of requests use free models** (Ollama)
- [ ] **Average cost < $5/month** per active user
- [ ] **Zero surprise bills** - all costs transparent
- [ ] **Sub-second response times** with free models
- [ ] **User satisfaction** maintained or improved
- [ ] **Cost dashboard shows real-time tracking**
- [ ] **Automatic fallback works seamlessly**

---

## 🚨 Important Notes

1. **Default to Free**: Always try Ollama first
2. **Transparent Costs**: Show users cost before expensive calls
3. **Auto-Fallback**: If free model unavailable, use cheap alternative
4. **Never Hide Costs**: Display real-time cost in UI
5. **User Control**: Let users bring their own API keys
6. **No Surprise Bills**: Hard limits on spending
7. **Performance Monitoring**: Track response times and quality

---

## 📚 Related Issues

- Cost governance and budget enforcement
- Roundtable multi-agent coordination
- Integration hub for external services
- Multi-panel workspace UI
- User-provided API key management

---

## 🔍 Testing Strategy

### Unit Tests
- [ ] Test model selection logic
- [ ] Test cost calculation accuracy
- [ ] Test fallback mechanisms
- [ ] Test budget enforcement

### Integration Tests
- [ ] Test Ollama connectivity
- [ ] Test Groq API integration
- [ ] Test Together AI integration
- [ ] Test HuggingFace API

### End-to-End Tests
- [ ] Test complete roundtable with free models
- [ ] Test cost tracking across session
- [ ] Test automatic fallback scenario
- [ ] Test user-provided key override

### Performance Tests
- [ ] Measure Ollama response times
- [ ] Compare quality vs OpenAI
- [ ] Test concurrent request handling
- [ ] Measure cost savings in production

---

## 🤝 Next Steps

1. **Review and approve this plan** - Get stakeholder buy-in
2. **Set up development environment** - Install Ollama locally
3. **Start with Phase 1** (Model Configuration)
4. **Implement incrementally** - Deploy phase by phase
5. **Monitor and adjust** - Track costs and performance
6. **Gather user feedback** - Ensure quality remains high

---

## 💬 Discussion Points

- Should we support additional free models (e.g., Falcon, StableLM)?
- What should be the default monthly budget limit?
- How to handle users who prefer OpenAI quality?
- Should we cache common queries to reduce costs further?
- What metrics should trigger an alert?

---

## 🎓 Additional Resources

- [Ollama Documentation](https://ollama.ai/docs)
- [Groq API Documentation](https://groq.com/docs)
- [Together AI Documentation](https://docs.together.ai)
- [HuggingFace Inference API](https://huggingface.co/docs/api-inference)
- [Cost Optimization Best Practices](https://docs.example.com/cost-optimization)

---

**Created**: 2025-12-15
**Status**: Open
**Assignee**: TBD
**Milestone**: Cost Optimization v1.0
