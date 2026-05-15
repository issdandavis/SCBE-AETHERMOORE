# scbe-autogen

SCBE governance gate for Microsoft AutoGen. Wraps AutoGen agents with the SCBE
trap-dispatch pipeline so every outbound message is checked for adversarial
patterns before being sent.

## Install

```bash
pip install scbe-autogen
# With AutoGen v0.4:
pip install "scbe-autogen[autogen-v4]"
# With AutoGen v0.2:
pip install "scbe-autogen[autogen-v2]"
```

## AutoGen v0.4 — governed agent

```python
from autogen_agentchat.agents import AssistantAgent
from scbe_autogen import SCBEGovernedAgent

base = AssistantAgent(name="assistant", model_client=your_client)
governed = SCBEGovernedAgent(
    agent=base,
    api_key="scbe_live_...",   # or set SCBE_API_KEY env var
)

result = await governed.run(task="summarize this document")
```

## AutoGen v0.2 — hook registration

```python
import autogen
from scbe_autogen import register_scbe_hook

agent = autogen.AssistantAgent(name="assistant", llm_config={"model": "gpt-4o"})
register_scbe_hook(agent, api_key="scbe_live_...")

# All outbound messages now flow through the SCBE governance gate
```

Set `SCBE_API_URL` to point at a self-hosted SCBE API (default: `http://127.0.0.1:8000`).

## License

MIT OR Apache-2.0
