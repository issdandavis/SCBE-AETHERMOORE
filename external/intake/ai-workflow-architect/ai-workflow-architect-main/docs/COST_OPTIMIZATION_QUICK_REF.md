# Cost Optimization Quick Reference

> **TL;DR**: Use free Ollama models first, cheap cloud models as fallback, expensive models only with user's own API key.

---

## 💰 Cost at a Glance

| Tier | Provider | Cost/1M Tokens | Use Case |
|------|----------|----------------|----------|
| 🎉 **FREE** | Ollama (self-hosted) | $0.00 | Default for everything |
| 💚 **CHEAP** | Groq | $0.59-0.79 | Fallback when Ollama down |
| 💚 **CHEAP** | Together AI | $0.90 | Complex reasoning |
| 💚 **CHEAP** | Perplexity | $0.05 | Search/research |
| 💸 **EXPENSIVE** | OpenAI GPT-4 | $3.00-10.00 | User key only |
| 💸 **EXPENSIVE** | Claude Opus | $15.00 | User key only |

**Target**: <$5/month per user (90%+ using free tier)

---

## 🚀 Quick Setup (5 minutes)

```bash
# 1. Install Ollama
curl https://ollama.ai/install.sh | sh

# 2. Pull models
ollama pull llama3.1:8b codellama:13b mistral:7b

# 3. Start server
ollama serve &

# 4. Test
curl http://localhost:11434/api/tags
```

---

## 🎯 Model Selection Rules

### For Code Tasks
1. **Primary**: `ollama/codellama:13b` (FREE)
2. **Fallback**: `groq/llama-3.1-70b` ($0.59/1M)
3. **Complex**: `together/qwen-2.5-72b` ($0.90/1M)

### For Chat Tasks
1. **Primary**: `ollama/llama3.1:8b` (FREE)
2. **Fallback**: `groq/mixtral-8x7b` ($0.24/1M)

### For Search Tasks
1. **Primary**: `perplexity/pplx-7b` ($0.05/1M)
2. **Fallback**: `ollama/llama3.1:8b` (FREE)

### For Analysis Tasks
1. **Primary**: `ollama/mistral:7b` (FREE)
2. **Fallback**: `together/qwen-2.5-72b` ($0.90/1M)

---

## 📋 Implementation Priorities

### Week 1: Foundation
- [ ] Add `free-model-config.ts` with all models
- [ ] Create `model-selector.ts` for smart selection
- [ ] Update `costGovernor.ts` middleware

### Week 2: Integration
- [ ] Implement `OllamaAdapter`
- [ ] Add Groq/Together fallbacks
- [ ] Test end-to-end

### Week 3: UI & Monitoring
- [ ] Build Cost Dashboard
- [ ] Add real-time cost display
- [ ] Implement budget alerts

### Week 4: Polish
- [ ] User-provided key support
- [ ] Documentation
- [ ] Production deployment

---

## ⚠️ Critical Rules

1. ✅ **Always try Ollama first**
2. ✅ **Show cost BEFORE expensive calls**
3. ✅ **Auto-fallback if Ollama down**
4. ❌ **Never use OpenAI/Claude without user's key**
5. ❌ **Never hide costs from users**

---

## 🔗 Resources

- **Full Issue**: `docs/FREE_FIRST_AI_STRATEGY_ISSUE.md`
- **Implementation Guide**: `docs/FREE_AI_IMPLEMENTATION_GUIDE.md`
- **Ollama Docs**: https://ollama.ai/docs
- **Groq API**: https://console.groq.com
- **Together AI**: https://api.together.xyz

---

## 📊 Success Metrics

- [ ] 90%+ requests use free models
- [ ] Average cost < $5/month per user
- [ ] Zero surprise bills
- [ ] Response time < 2s
- [ ] User satisfaction maintained

---

## 🆘 Quick Troubleshooting

**Problem**: Ollama not responding
```bash
ollama serve  # Restart
```

**Problem**: Model not found
```bash
ollama pull llama3.1:8b
```

**Problem**: Slow responses
```bash
# Use smaller model for simple tasks
ollama pull phi-3
```

**Problem**: High costs
- Check which models are being used
- Verify Ollama is running
- Review cost dashboard

---

**Last Updated**: 2025-12-15
