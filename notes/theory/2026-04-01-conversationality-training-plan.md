# Conversationality Training Plan

Source: Codex session April 1, 2026
Status: Research complete, execution pending

## What We Already Have

- Base model: Qwen/Qwen2.5-0.5B-Instruct (already fine-tuned on SCBE data)
- SCBE SFT dataset: 41,703 cleaned pairs (24 categories) on HuggingFace
- Code multiview dataset: 8,000 pairs (L0/L1/L2/L3) on HuggingFace
- Kaggle baseline vs stack-lite: COMPLETE (14% win for multiview)
- Kaggle governance fine-tune: v4 submitted (CPU, 200 steps)
- Colab notebook: finetune_qwen_governance.ipynb ready

## What's New (from Codex research)

### Recommended Datasets for Conversationality

| Dataset | Purpose | Size |
|---------|---------|------|
| HuggingFaceH4/ultrachat_200k | Multi-turn SFT (Zephyr-style) | 200K conversations |
| HuggingFaceTB/smol-smoltalk | Lighter SFT for small models | Smaller |
| m-ric/Open_Assistant_Conversation_Chains | Human-generated multi-turn | Multilingual |
| argilla/ultrafeedback-binarized-preferences-cleaned | DPO preference alignment | Clean binary prefs |

### Training Pipeline (3 stages)

1. **SFT on ultrachat_200k** — teaches multi-turn conversation flow
2. **Mix in Open_Assistant_Conversation_Chains** — adds human-generated grounding (acknowledgment, clarification, follow-through)
3. **DPO on ultrafeedback-binarized-preferences-cleaned** — aligns preferences

### Key Insight (from paper)

"Grounding Gaps in Language Model Generations" (arxiv 2311.09144):
Models underproduce conversational grounding acts — acknowledgment, clarification, follow-through.
Fix: add custom dataset that rewards these behaviors.

### Compute Options

| Option | Status | Cost |
|--------|--------|------|
| Colab (local bridge) | Working | Free (T4 GPU) |
| HF ZeroGPU | For Spaces/demos only | Free but limited |
| HF Jobs | Requires Pro/Team | Pay-as-you-go |
| Kaggle | Working (CPU only, P100 incompatible) | Free |

### Recommended Execution Order

1. SFT on Qwen2.5-0.5B + ultrachat_200k (Colab, fastest improvement)
2. Mix SCBE-specific data (our 41K cleaned) with ultrachat for domain grounding
3. DPO on ultrafeedback preferences (second stage)
4. Add custom SCBE conversationality pairs (acknowledgment + governance context)
5. Scale to 7B with winning config

### Connection to Triangulation

The conversationality training should use multi-view (L0/L1/L2/L3) format:
- L0: raw byte-level conversation structure
- L1: tongue-tokenized conversation (domain separation)
- L2: governance assessment of conversation flow
- L3: the actual conversation

This extends the 14% triangulation improvement to conversation quality.
