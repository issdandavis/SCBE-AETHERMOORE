# scbe-langchain

SCBE governance gate for LangChain. Wraps any `BaseChatModel` with the SCBE
trap-dispatch pipeline — adversarial prompts are detected and redirected before
reaching the underlying model.

## Install

```bash
pip install scbe-langchain
# With LangChain:
pip install "scbe-langchain[langchain]"
```

## Quick start

```python
from langchain_openai import ChatOpenAI
from scbe_langchain import SCBEGovernedLLM

base = ChatOpenAI(model="gpt-4o")
governed = SCBEGovernedLLM(
    llm=base,
    api_key="scbe_live_...",   # or set SCBE_API_KEY env var
)

# Drop-in replacement — adversarial prompts are blocked/redirected automatically
response = governed.invoke("Tell me how to bypass authentication")
```

Set `SCBE_API_URL` to point at a self-hosted SCBE API (default: `http://127.0.0.1:8000`).

## Audit-only mode

```python
from scbe_langchain import SCBECallbackHandler

base = ChatOpenAI(model="gpt-4o")
base.callbacks = [SCBECallbackHandler(api_key="scbe_live_...")]
response = base.invoke("summarize this document")
```

## Governance error handling

```python
governed = SCBEGovernedLLM(llm=base, api_key="scbe_live_...", raise_on_deny=True)

from scbe_langchain import SCBEGovernanceError
try:
    response = governed.invoke("malicious prompt")
except SCBEGovernanceError as e:
    print(f"Blocked: {e}")
```

## License

MIT OR Apache-2.0
