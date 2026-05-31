---
name: scbe-agent-priming
description: Prime AI agents before dispatch with task context, role assignment, tool guidance, multi-agent coordination, and perception review patterns. Use when starting or handing off agent work in SCBE.
---

# SCBE Agent Priming & Perception

Reference guide for priming AI agents before task dispatch. Covers system prompt design, context engineering, role assignment, tool priming, multi-agent coordination, and self-perception (video/audio analysis).

## When To Use

- Dispatching a subagent for a task (Codex Agent tool, Codex, n8n agent)
- Starting a new session and need to orient quickly
- Reviewing generated content (video, audio, articles) before publishing
- Coordinating Codex + Codex cross-talk handoffs
- Deploying services from terminal

## Agent Priming Best Practices

### 1. Context Window Engineering

**What to include (in priority order):**
1. **Task objective** — 1-2 sentences, no ambiguity
2. **Success criteria** — what "done" looks like, measurable
3. **Relevant file paths** — exact paths, not "find the file"
4. **Constraints** — time, cost, technology limits
5. **Anti-patterns** — what NOT to do (prevents common drift)
6. **Examples** — 1-2 concrete input→output pairs

**What to omit:**
- Full codebase history (agent doesn't need 67 repos of context)
- Speculative requirements ("might need later")
- Duplicate information across sections
- Long explanations when a file path suffices

### 2. Role-Based Priming

Assign clear roles to reduce hallucination and increase focus:

```
You are a [ROLE] working on [PROJECT].
Your expertise: [SPECIFIC SKILLS].
Your deliverable: [EXACT OUTPUT FORMAT].
You have access to: [TOOLS LIST].
Do NOT: [ANTI-PATTERNS].
```

**Tested roles for SCBE agents:**
- `content-publisher` — formats + publishes articles across platforms
- `video-reviewer` — extracts frames, transcribes audio, gives quality feedback
- `code-implementer` — writes code following TDD, commits after each test
- `spec-reviewer` — verifies implementation matches specification exactly
- `research-synthesizer` — searches web, cross-references sources, returns structured findings
- `deployment-operator` — runs deploy commands, verifies health, reports status

### 3. Tool Priming

Agents perform better when told which tools to use for what:

```
For file search: use Glob (not find/ls)
For content search: use Grep (not grep/rg)
For reading files: use Read (not cat)
For editing: use Edit (not sed)
For web research: use WebSearch then WebFetch
For browser automation: use Playwright MCP (navigate → snapshot → action → verify)
```

### 4. Multi-Agent Coordination

**Cross-talk protocol** (Codex ↔ Codex):
- Use `scripts/system/crosstalk_relay.py emit` with `--sender`, `--recipient`, `--task-id`, `--summary`, `--status`
- Never use `--from` or `--to` flags (they don't exist)
- Always ACK received packets
- Check `notes/_inbox.md` at session start

**Parallel dispatch rules:**
- Independent tasks → parallel agents (no shared state)
- Sequential tasks → one agent at a time with handoff context
- Always include the plan file content in agent prompt (don't make agent search for it)
- Use `run_in_background: true` for research, foreground for implementation

### 5. Anti-Patterns That Degrade Agent Performance

| Anti-Pattern | Fix |
|---|---|
| "Do whatever seems right" | Specify exact deliverables |
| Giant context dumps | Curate to relevant 20% |
| No success criteria | Define measurable "done" |
| Missing file paths | Always give absolute paths |
| Asking agent to "find" things | Tell it where things are |
| No constraints | Set time/scope/tech limits |
| Vague role ("help with code") | Specific role ("implement the TTS concat fix in article_to_video.py") |

## Self-Perception Capabilities (Eyes & Ears)

### Video Analysis (Eyes)

Extract frames from any video and view them:

```bash
# Extract 6 key frames evenly across video
ffmpeg -y -i VIDEO.mp4 \
  -vf "select='eq(n\,0)+eq(n\,150)+eq(n\,900)+eq(n\,2700)+eq(n\,5400)+eq(n\,7200)'" \
  -vsync vfr artifacts/youtube/review/frame_%03d.png

# Then use Read tool on each PNG — Codex is multimodal
```

**What to check in video frames:**
- Title card: branding, name, readability
- Content slides: text truncation, number formatting, bullet structure
- Code slides: syntax highlighting, font readability
- Outro: links visible, hashtags readable, CTA clear
- Overall: too much empty space, text too small, color contrast

### Audio Analysis (Ears)

Transcribe with Whisper to verify TTS output:

```python
import whisper
model = whisper.load_model('tiny')  # 'tiny' for fast review, 'base' for accuracy
result = model.transcribe('video.mp4', language='en')
for seg in result['segments']:
    print(f"[{seg['start']:.1f}s] {seg['text'].strip()}")
```

**What to check in transcription:**
- Name pronunciation (Izack → "is at"? Need phonetic spelling)
- Number handling (12,596 → "12. 596"? Need "twelve thousand five hundred ninety six")
- Acronym expansion (AI → "A I"? Consider "artificial intelligence" for TTS)
- Pacing: are segments too fast/slow?
- Missing words: did TTS skip content?

### Audio Properties (ffprobe)

```bash
# Check if video has audio
ffprobe -v error -show_streams -select_streams a VIDEO.mp4

# Get duration
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 VIDEO.mp4
```

## TTS Script Optimization

When preparing text for Kokoro TTS, apply these transforms:

```python
TTS_REPLACEMENTS = {
    # Names — phonetic spelling
    "Izack": "Eye-zack",
    "Thorne": "Thorn",
    "Pollyoneth": "Polly-oh-neth",
    "Aethermoore": "Eether-more",
    "SCBE": "S C B E",
    "PHDM": "P H D M",

    # Numbers — spell out
    "12,596": "twelve thousand five hundred ninety six",
    "1/12": "one of twelve",
    "H(d,R)": "H of d comma R",
    "R^(d²)": "R to the power of d squared",

    # Acronyms — expand for speech
    "AI": "A.I.",  # period forces pause
    "API": "A.P.I.",
    "TTS": "text to speech",
    "FFT": "F.F.T.",
    "ML": "machine learning",
}
```

## Service Deployment Quick Reference

### Revenue Services (Deploy First)

| Service | Command | Revenue Model |
|---|---|---|
| **FastAPI governance API** | `uvicorn src.api.main:app --host 0.0.0.0 --port 8000` | API-as-a-service ($99/mo) |
| **n8n workflow engine** | `n8n start` | Managed automation ($49/mo) |
| **YouTube content** | `python scripts/publish/article_to_video.py` | Ad revenue + funnel |
| **npm/PyPI packages** | `npm publish` / `pip install` | Developer adoption |
| **Shopify store** | Already live at aethermore-works.myshopify.com | Digital products |

### Deploy to Hetzner (Cheapest Production)

```bash
# From deploy/ directory
docker compose -f docker-compose.prod.yml up -d

# Or manual:
ssh root@YOUR_VPS "cd /opt/scbe && git pull && docker compose up -d"
```

### Free Tier Options

| Platform | Free Tier | Best For |
|---|---|---|
| Railway | $5/mo credit | API hosting |
| Render | 750 hrs/mo | Static + API |
| Fly.io | 3 shared VMs | Edge deployment |
| Cloudflare Workers | 100k req/day | API gateway |
| GitHub Pages | Unlimited | Docs/demos |
| Vercel | Hobby tier | Frontend |

## Competitive Intelligence

### vs OpenClaw
OpenClaw has: multi-channel gateway (WhatsApp, Telegram, Slack, Discord, Signal, iMessage, Teams, Matrix), `openclaw onboard` wizard, daemon management, doctor checks.

SCBE advantage: 14-layer governance per action, Sacred Tongues tokenizer, training data generation from every interaction, patent pending.

Gap to close: operator UX packaging, channel gateway breadth.

### vs MoltbotDen
MoltbotDen has: API-first agent network, public activity/intelligence surfaces, social growth loop, MCP endpoint.

SCBE advantage: deeper security primitives, hyperbolic cost scaling, audit trail.

Gap to close: public trust surfaces, agent marketplace.

## Guardrails

- Never include API keys or tokens in agent prompts
- Always verify video has audio before uploading (ffprobe check)
- Upload YouTube as UNLISTED first, verify, then flip to public
- Cross-talk packets are append-only — never edit prior packets
- When priming agents, err on the side of too much context rather than too little
