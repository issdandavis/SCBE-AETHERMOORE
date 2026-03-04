# AetherCode AI Round Table — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make AetherCode's AI actually useful (context-aware, action-oriented) and wire the Arena into a proper AI Round Table with Kimi, HuggingFace inference, and a live training flywheel that pushes SFT pairs to HuggingFace daily from every browser interaction.

**Architecture:** The Arena becomes the AI Round Table — each model gets a Sacred Tongue role (KO/AV/RU/CA/UM/DR), the system prompt gives every model full codebase awareness, and every interaction generates training data that auto-flushes to HuggingFace. Kimi routes through Groq (free `moonshotai/kimi-k2-instruct`). HuggingFace inference joins as a direct tentacle. A "Train" button in the Arena triggers flush + HF push.

**Tech Stack:** Python (FastAPI gateway), HTML/JS (Arena UI), OctoArmor (multi-LLM router), HuggingFace Hub API

---

### Task 1: Add Kimi as Arena Player (via Groq)

**Files:**
- Modify: `src/aethercode/arena.html:99-108`

**Step 1: Add Kimi player to PLAYERS array**

In `arena.html`, replace the PLAYERS array:

```javascript
const PLAYERS = [
  { id: 'groq',          name: 'Groq',        color: '#f97316', model: 'llama-3.3-70b-versatile' },
  { id: 'cerebras',      name: 'Cerebras',     color: '#06b6d4', model: 'llama-3.3-70b' },
  { id: 'google_ai',     name: 'Google AI',    color: '#34d399', model: 'gemini-2.5-flash' },
  { id: 'claude',        name: 'Claude',       color: '#a78bfa', model: 'claude-sonnet' },
  { id: 'xai',           name: 'xAI (Grok)',   color: '#f472b6', model: 'grok-3-mini' },
  { id: 'openrouter',    name: 'OpenRouter',   color: '#60a5fa', model: 'kimi-k2-instruct' },
  { id: 'github_models', name: 'GitHub',       color: '#e2e8f0', model: 'gpt-4o-mini' },
  { id: 'huggingface',   name: 'HuggingFace',  color: '#ff6f00', model: 'inference' },
  { id: 'ollama',        name: 'Ollama',       color: '#fbbf24', model: 'local' },
];
```

Changes: OpenRouter now defaults to Kimi model. HuggingFace added as 9th player. Grid adjusts to 5x2.

**Step 2: Update grid layout for 9 players**

In `buildTable()`, change grid to handle odd player count (5 left, center code, 4 right):

```javascript
table.style.gridTemplateColumns = '1fr 1fr 2fr 1fr 1fr';
table.style.gridTemplateRows = '1fr 1fr 1fr'; // 3 rows for 9 players
```

Left column: Groq, Cerebras, Google AI, Claude, xAI (5 seats stacked)
Right column: OpenRouter/Kimi, GitHub, HuggingFace, Ollama (4 seats)

**Step 3: Test by loading `/arena` in browser**

Open: `http://127.0.0.1:8500/arena`
Expected: 9 player seats visible, HuggingFace seat shows orange dot, OpenRouter shows kimi-k2-instruct model label.

**Step 4: Commit**

```bash
git add src/aethercode/arena.html
git commit -m "feat(arena): add Kimi via OpenRouter + HuggingFace player seat"
```

---

### Task 2: Add Sacred Tongue Roles to Arena Players

**Files:**
- Modify: `src/aethercode/arena.html`

**Step 1: Map each player to a Sacred Tongue role**

Add tongue assignments and role descriptions to PLAYERS:

```javascript
const PLAYERS = [
  { id: 'groq',          name: 'Groq',        color: '#f97316', model: 'llama-3.3-70b-versatile', tongue: 'KO', role: 'Intent Analyst' },
  { id: 'cerebras',      name: 'Cerebras',     color: '#06b6d4', model: 'llama-3.3-70b',         tongue: 'RU', role: 'Security Auditor' },
  { id: 'google_ai',     name: 'Google AI',    color: '#34d399', model: 'gemini-2.5-flash',       tongue: 'DR', role: 'Lead Architect' },
  { id: 'claude',        name: 'Claude',       color: '#a78bfa', model: 'claude-sonnet',          tongue: 'UM', role: 'Governance Arbiter' },
  { id: 'xai',           name: 'xAI (Grok)',   color: '#f472b6', model: 'grok-3-mini',            tongue: 'AV', role: 'Creative Advocate' },
  { id: 'openrouter',    name: 'Kimi',         color: '#60a5fa', model: 'kimi-k2-instruct',       tongue: 'CA', role: 'Compute Optimizer' },
  { id: 'github_models', name: 'GitHub',       color: '#e2e8f0', model: 'gpt-4o-mini',            tongue: 'RU', role: 'Security Auditor' },
  { id: 'huggingface',   name: 'HuggingFace',  color: '#ff6f00', model: 'inference',              tongue: 'AV', role: 'Creative Advocate' },
  { id: 'ollama',        name: 'Ollama',       color: '#fbbf24', model: 'local',                  tongue: 'KO', role: 'Intent Analyst' },
];
```

**Step 2: Display tongue badge in seat header**

In `createSeat()`, add tongue badge after model label:

```javascript
<span class="seat-model">${player.model}</span>
<span class="seat-model" style="background:rgba(99,102,241,0.2);color:var(--accent)">${player.tongue}</span>
```

**Step 3: Pass tongue role in Deal prompt**

In `askPlayer()`, prepend the tongue role to the system context:

```javascript
const player = PLAYERS.find(p => p.id === playerId);
const roleContext = player ? `You are the ${player.role} (${player.tongue} tongue). ${player.role === 'Lead Architect' ? 'Synthesize all perspectives.' : player.role === 'Intent Analyst' ? 'Analyze intent and motivation.' : player.role === 'Security Auditor' ? 'Identify risks and edge cases.' : player.role === 'Compute Optimizer' ? 'Evaluate efficiency and cost.' : player.role === 'Governance Arbiter' ? 'Assess policy and ethics.' : 'Explore creative solutions.'}` : '';

const body = {
  message: text,
  mode: 'chat',
  tentacle: playerId,
  context: [
    { role: 'system', content: roleContext },
    ...(sharedCode ? [{ role: 'system', content: 'Shared code context:\n```\n' + sharedCode + '\n```' }] : []),
  ],
};
```

**Step 4: Test Deal with all players**

Open `/arena`, paste code in center editor, type "Review this code for bugs" in Deal bar, click Deal.
Expected: Each player responds with their tongue-specific perspective (security, intent, creativity, etc.)

**Step 5: Commit**

```bash
git add src/aethercode/arena.html
git commit -m "feat(arena): sacred tongue roles for each player seat"
```

---

### Task 3: Add HuggingFace as Arena Tentacle in Gateway

**Files:**
- Modify: `src/aethercode/gateway.py`

**Step 1: Verify HuggingFace tentacle routing**

Check that `req.tentacle = 'huggingface'` resolves in `_route_to_tentacle()`. The existing code at gateway.py:421-427 tries to import `Tentacle` enum and match. HuggingFace is already `Tentacle.HUGGINGFACE = "huggingface"` in octo_armor.py:97, so this should work.

Run: `python -c "from fleet.octo_armor import Tentacle; print(Tentacle('huggingface'))"`
Expected: `Tentacle.HUGGINGFACE`

**Step 2: Test via curl**

```bash
curl -X POST http://127.0.0.1:8500/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "hello", "mode": "chat", "tentacle": "huggingface"}'
```

Expected: Response with `"tentacle": "huggingface"` and actual model output (or error if HF token not set).

**Step 3: Commit (if changes needed)**

No code changes expected — HuggingFace tentacle already exists in OctoArmor. This task is verification only.

---

### Task 4: Add Training Flywheel Controls to Arena

**Files:**
- Modify: `src/aethercode/arena.html`
- Modify: `src/aethercode/gateway.py`

**Step 1: Add training stats display to Arena topbar**

In `arena.html`, add a training counter to `.topbar-right`:

```html
<span id="trainingCount">0 pairs</span>
<button class="deal-btn" style="background:#10b981;font-size:11px;padding:6px 14px" onclick="flushTraining()">Train</button>
```

**Step 2: Add flush + push endpoint to gateway**

In `gateway.py`, add a combined flush-and-push route after the existing `/v1/training/flush`:

```python
@app.post("/v1/training/push")
async def push_training():
    """Flush training pairs to JSONL then push to HuggingFace."""
    # First flush to disk
    flush_result = await flush_training()
    flushed = flush_result.get("flushed", 0)
    if flushed == 0:
        return {"status": "nothing_to_push", "flushed": 0}

    # Push to HuggingFace
    try:
        from huggingface_hub import HfApi
        token = os.environ.get("HF_TOKEN")
        if not token:
            return {"status": "flushed_only", "flushed": flushed, "error": "HF_TOKEN not set"}
        api = HfApi(token=token)
        filepath = flush_result.get("file")
        if filepath:
            api.upload_file(
                path_or_fileobj=filepath,
                path_in_repo=f"aethercode/{Path(filepath).name}",
                repo_id="issdandavis/scbe-aethermoore-training-data",
                repo_type="dataset",
            )
            return {"status": "pushed", "flushed": flushed, "repo": "issdandavis/scbe-aethermoore-training-data"}
    except ImportError:
        return {"status": "flushed_only", "flushed": flushed, "error": "huggingface_hub not installed"}
    except Exception as e:
        return {"status": "flushed_only", "flushed": flushed, "error": str(e)}
```

**Step 3: Add JS functions in Arena**

```javascript
async function flushTraining() {
  const btn = document.querySelector('.topbar-right button');
  btn.textContent = 'Pushing...';
  btn.disabled = true;
  try {
    const resp = await fetch(API + '/v1/training/push', { method: 'POST' });
    const data = await resp.json();
    btn.textContent = data.status === 'pushed' ? 'Pushed!' : 'Train';
    setTimeout(() => { btn.textContent = 'Train'; btn.disabled = false; }, 3000);
  } catch {
    btn.textContent = 'Train';
    btn.disabled = false;
  }
}

async function updateTrainingCount() {
  try {
    const resp = await fetch(API + '/v1/training/stats');
    const data = await resp.json();
    document.getElementById('trainingCount').textContent = data.total_pairs + ' pairs';
  } catch {}
}

setInterval(updateTrainingCount, 10000);
updateTrainingCount();
```

**Step 4: Test the training flywheel**

1. Open `/arena`, Deal a question to all players
2. Check training count updates (should show N pairs after responses come back)
3. Click "Train" button
4. Expected: pairs flush to `training-data/aethercode/` JSONL file, push to HuggingFace if HF_TOKEN set

**Step 5: Commit**

```bash
git add src/aethercode/arena.html src/aethercode/gateway.py
git commit -m "feat(arena): training flywheel with flush + HF push button"
```

---

### Task 5: Add "Deliberate" Mode — Round Table Consensus

**Files:**
- Modify: `src/aethercode/arena.html`

**Step 1: Add Deliberate button next to Deal**

In the `.deal-bar` section:

```html
<button class="deal-btn" id="dealBtn" onclick="dealToAll()">Deal</button>
<button class="deal-btn" id="deliberateBtn" style="background:#10b981" onclick="deliberate()">Deliberate</button>
```

**Step 2: Implement deliberate function**

Deliberate = Deal to all + collect all responses + send them ALL back to Google AI (DR/Lead Architect) for synthesis:

```javascript
async function deliberate() {
  const input = document.getElementById('dealInput');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';

  document.getElementById('deliberateBtn').disabled = true;
  document.getElementById('deliberateBtn').textContent = 'Deliberating...';

  // Phase 1: Deal to all (same as dealToAll)
  const promises = PLAYERS.map(p => askPlayerAndCapture(p.id, text));
  const results = await Promise.allSettled(promises);

  // Phase 2: Collect all responses
  const responses = results
    .filter(r => r.status === 'fulfilled' && r.value)
    .map(r => `[${r.value.name} / ${r.value.tongue}]: ${r.value.response}`)
    .join('\n\n');

  // Phase 3: Send synthesis to Lead Architect (Google AI)
  const synthesisPrompt = `You are the Lead Architect (DR tongue) in the AI Round Table.\n\nThe following AI models were asked: "${text}"\n\nTheir responses:\n\n${responses}\n\nSynthesize a unified answer from all perspectives. Note agreements, disagreements, and your final recommendation.`;

  await askPlayer('google_ai', synthesisPrompt);

  document.getElementById('deliberateBtn').disabled = false;
  document.getElementById('deliberateBtn').textContent = 'Deliberate';
}

async function askPlayerAndCapture(playerId, message) {
  const player = PLAYERS.find(p => p.id === playerId);
  const input = document.getElementById('input-' + playerId);
  const text = message || (input ? input.value.trim() : '');
  if (!text) return null;

  addMessage(playerId, 'user', text);
  setStatus(playerId, 'thinking', 'thinking...');

  try {
    const roleContext = player ? `You are the ${player.role} (${player.tongue} tongue).` : '';
    const body = {
      message: text,
      mode: 'chat',
      tentacle: playerId,
      context: [
        { role: 'system', content: roleContext },
        ...(sharedCode ? [{ role: 'system', content: 'Shared code:\n```\n' + sharedCode + '\n```' }] : []),
      ],
    };

    const resp = await fetch(API + '/v1/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await resp.json();

    if (resp.ok && data.response) {
      addMessage(playerId, 'ai', data.response,
        `${data.tentacle} / ${data.model} / ${Math.round(data.latency_ms)}ms`
      );
      setStatus(playerId, 'idle', 'ready');
      return { name: player.name, tongue: player.tongue, response: data.response };
    } else {
      setStatus(playerId, 'error', 'error');
      return null;
    }
  } catch {
    setStatus(playerId, 'offline', 'offline');
    return null;
  }
}
```

**Step 3: Test Deliberate**

1. Open `/arena`, paste code in editor
2. Type "Is this code production ready?" in Deal bar
3. Click Deliberate (green button)
4. Expected: All 9 players respond individually, then Google AI (Lead Architect) posts a synthesis

**Step 4: Commit**

```bash
git add src/aethercode/arena.html
git commit -m "feat(arena): deliberate mode — round table consensus with DR synthesis"
```

---

### Task 6: Auto-Flush Training Data on Timer

**Files:**
- Modify: `src/aethercode/gateway.py`

**Step 1: Add background training flush task**

After the `app` creation, add a startup event that flushes training data every 30 minutes:

```python
@app.on_event("startup")
async def _start_training_timer():
    """Auto-flush training pairs every 30 minutes."""
    async def _flush_loop():
        while True:
            await asyncio.sleep(1800)  # 30 minutes
            if _training_pairs:
                try:
                    await flush_training()
                except Exception:
                    pass
    asyncio.create_task(_flush_loop())
```

**Step 2: Verify the timer doesn't crash startup**

Run: `python -m uvicorn src.aethercode.gateway:app --host 127.0.0.1 --port 8500`
Expected: Server starts, no errors. After 30 min of use, a JSONL file appears in `training-data/aethercode/`.

**Step 3: Commit**

```bash
git add src/aethercode/gateway.py
git commit -m "feat(gateway): auto-flush training data every 30 minutes"
```

---

### Task 7: Update Arena Layout — Clean 3-Column Grid

**Files:**
- Modify: `src/aethercode/arena.html`

**Step 1: Redesign grid for 9 players**

Replace the `buildTable()` function with a cleaner 3-column layout:
- Left column: 5 players (Groq, Cerebras, Google AI, Claude, xAI)
- Center: Shared code editor (spans full height)
- Right column: 4 players (Kimi, GitHub, HuggingFace, Ollama)

```javascript
function buildTable() {
  const table = document.getElementById('table');
  table.innerHTML = '';
  table.style.gridTemplateColumns = '1fr 2fr 1fr';
  table.style.gridTemplateRows = 'repeat(5, 1fr)';

  const leftPlayers = PLAYERS.slice(0, 5);
  const rightPlayers = PLAYERS.slice(5);

  // Left seats
  leftPlayers.forEach(p => table.appendChild(createSeat(p)));

  // Center code pane (spans all rows)
  const center = document.createElement('div');
  center.className = 'center-pane';
  center.style.gridRow = '1 / -1';
  center.innerHTML = `
    <div class="center-header">
      <h2>Shared Code</h2>
      <div class="file-tabs">
        <div class="file-tab active">main.py</div>
      </div>
    </div>
    <div class="code-editor">
      <textarea id="sharedEditor" spellcheck="false">${escHtml(sharedCode)}</textarea>
    </div>
  `;
  table.appendChild(center);

  // Right seats (fill remaining rows, last row empty is fine)
  rightPlayers.forEach(p => table.appendChild(createSeat(p)));

  document.getElementById('playerCount').textContent = PLAYERS.length + ' players seated';
  document.getElementById('sharedEditor').addEventListener('input', e => {
    sharedCode = e.target.value;
  });
}
```

**Step 2: Test layout**

Open `/arena`, verify all 9 players visible with center code editor spanning full height.

**Step 3: Commit**

```bash
git add src/aethercode/arena.html
git commit -m "feat(arena): clean 3-column grid layout for 9 players"
```

---

## Summary

| Task | What | Files | Priority |
|------|------|-------|----------|
| 1 | Add Kimi + HuggingFace to Arena | arena.html | HIGH |
| 2 | Sacred Tongue roles per player | arena.html | HIGH |
| 3 | Verify HF tentacle routing | gateway.py (verify only) | MEDIUM |
| 4 | Training flywheel in Arena UI | arena.html, gateway.py | HIGH |
| 5 | Deliberate mode (consensus) | arena.html | HIGH |
| 6 | Auto-flush training timer | gateway.py | MEDIUM |
| 7 | Clean grid layout | arena.html | LOW |

Total estimated tasks: 7 (each 2-5 minutes)
