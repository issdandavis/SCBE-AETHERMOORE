# AetherBot — Quick Start Guide

Your local AI assistant that knows the entire SCBE-AETHERMOORE system.
Runs on your machine, no API key needed, no cloud, no cost.

## Install (one time)

Ollama is already installed. If it's not, download from https://ollama.com/download

## Run AetherBot

Open any terminal and type:

```
ollama run issdandavis7795/AetherBot
```

That's it. You're chatting with an AI that knows:
- The 14-layer pipeline
- All 6 Sacred Tongues
- The harmonic wall formula
- Fibonacci trust consensus
- Null-space detection
- Your novel "The Six Tongues Protocol"
- The patent (USPTO #63/961,403)

## Example Questions

```
>>> What is the harmonic wall?
>>> How do Sacred Tongues classify semantic meaning?
>>> Explain null-space signatures in simple terms
>>> What happens when an agent's trust drops on the Fibonacci ladder?
>>> How does the 14-layer pipeline process an action?
>>> What is the connection between the novel and the code?
```

## Use From Code (Python)

```python
import requests

response = requests.post('http://localhost:11434/api/generate', json={
    'model': 'issdandavis7795/AetherBot',
    'prompt': 'What is the harmonic wall?',
    'stream': False
})
print(response.json()['response'])
```

## Use From Code (curl)

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "issdandavis7795/AetherBot",
  "prompt": "Explain the 6 Sacred Tongues",
  "stream": false
}'
```

## Use in AetherBrowser Mobile

The AetherBrowser Chat tab can route to AetherBot as the "Local" model option.
Start the API server first:

```
python scripts/aetherbrowser/api_server.py
```

Then open `kindle-app/www/aetherbrowser.html` — select "Local" in the model picker.

## Update AetherBot

If the Modelfile changes:

```
ollama create AetherBot -f config/ollama/AetherBot.Modelfile
ollama cp AetherBot issdandavis7795/AetherBot
ollama push issdandavis7795/AetherBot
```

## Share It

Anyone with Ollama can run your model:

```
ollama run issdandavis7795/AetherBot
```

No account needed to pull. Just install Ollama and run that command.

## What's Inside

- **Base model**: Llama 3.2 (3B parameters)
- **System prompt**: Full SCBE context — pipeline, tongues, math, novel, patent
- **Temperature**: 0.7 (creative but grounded)
- **Context window**: 8192 tokens
- **Size**: ~2GB on disk
- **Speed**: ~10-30 tokens/sec on CPU, faster with GPU

## Modelfile Location

```
config/ollama/AetherBot.Modelfile
```

Edit this to change the system prompt, temperature, or base model.
