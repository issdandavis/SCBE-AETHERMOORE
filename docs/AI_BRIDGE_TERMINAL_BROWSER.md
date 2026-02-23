# AI Bridge (Terminal + Browser)

Use one local bridge to talk to external AI providers from terminal or browser.

## Terminal (one-shot)
```powershell
python scripts/system/ai_bridge.py --provider hf --model Qwen/Qwen2.5-7B-Instruct --prompt "summarize current task" --vault-path "C:/Users/issda/OneDrive/Documents/DOCCUMENTS/A follder"
```

## Terminal (interactive)
```powershell
python scripts/system/ai_bridge.py --provider vertex --model gemini-2.5-flash --interactive --vault-path "C:/Users/issda/OneDrive/Documents/DOCCUMENTS/A follder"
```

## Browser
```powershell
streamlit run scripts/system/ai_bridge_streamlit.py
```

## Notes
- HF calls use `huggingface_hub` and optional `HF_TOKEN`.
- Vertex calls use `google-genai` with your active cloud auth.
- Every request/response can be logged into Obsidian automatically.
