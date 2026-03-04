Now I have sufficient research data to compile the comprehensive report.

---

# Comprehensive Open Source Tools Research Report

## For AI Training Pipeline Integration

**Date:** 2026-02-21
**Scope:** Research only -- no installations performed

---

## 1. n8n -- Open Source Workflow Automation

### What It Is

n8n is a fair-code workflow automation platform with 176k GitHub stars. It combines visual workflow building with custom code execution, offering 400+ integrations, native AI capabilities built on LangChain, and full self-hosting support. It is positioned as an open-source alternative to Zapier, Make, and Tray.io, but with substantially more power for technical teams.

### GitHub Repository

- **URL:** [https://github.com/n8n-io/n8n](https://github.com/n8n-io/n8n)
- **Stars:** 176k
- **License:** Sustainable Use License + n8n Enterprise License (fair-code, source-available)
- **Tech Stack:** TypeScript (91.3%), Vue.js frontend
- **Commits:** 18,000+

### Installation on Windows 11

**Option A: Docker (Recommended for production)**
```bash
# Requires Docker Desktop for Windows 11
# (Home edition needs WSL2 enabled)
docker run -it --rm --name n8n -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n
```

For persistent production use, a `docker-compose.yml` with PostgreSQL backend is recommended. The n8n docs provide a complete Docker Compose configuration at [docs.n8n.io/hosting/installation/docker-compose](https://docs.n8n.io/hosting/installation/server-setups/docker-compose/).

**Option B: npm (Lighter, good for development)**
```bash
# Requires Node.js (LTS recommended)
npx n8n
# Or install globally:
npm install n8n -g
n8n start
```

Access the UI at `http://localhost:5678` after launch.

**Docker vs npm tradeoffs:**
| Aspect | Docker | npm |
|--------|--------|-----|
| Isolation | Full container isolation | Runs in host Node.js |
| Updates | Pull new image | npm update |
| Production readiness | Higher (PostgreSQL, volumes) | Development-grade |
| Windows ease | Requires Docker Desktop + WSL2 | Requires Node.js only |
| Resource overhead | Higher (container layer) | Lower |

### REST API Capabilities for AI Pipelines

n8n's webhook and API architecture makes it highly suitable for orchestrating AI training pipelines:

- **Webhook Node:** Creates HTTP endpoints that trigger workflows on POST/GET requests. Training scripts can call these endpoints to start/stop/report status.
- **HTTP Request Node:** Can call external APIs (HuggingFace, training servers, model registries).
- **Execute Command Node:** Can run shell commands, Python scripts, or SSH into remote GPU boxes.
- **Function Nodes:** Inline JavaScript/Python code for data transformation and logic.
- **Respond to Webhook Node:** Returns data at the end of a workflow, making n8n act as a REST API endpoint itself.
- **Cron/Schedule Triggers:** Schedule recurring training jobs.
- **Error Handling Workflows:** Catch failures and route them to alerts (Slack, email, etc.).

A practical MLOps pattern documented at [techbuddies.io](https://www.techbuddies.io/2026/01/22/orchestrating-pytorch-training-with-n8n-practical-mlops-automation/) shows n8n submitting Kubernetes Jobs or SSH commands to GPU workers, monitoring training progress via webhook callbacks, archiving checkpoints, and updating experiment trackers -- all while keeping the PyTorch logic in Python and n8n handling orchestration, retries, and conditional routing.

---

## 2. Lightweight Open Source Browsers for AI Web Navigation Training

### Selection Criteria
For AI web navigation training, the ideal browser needs: (a) lightweight resource footprint, (b) scriptable/automatable interfaces, (c) headless or programmatic operation, and (d) open source licensing.

### Top 3 Recommendations

#### 2A. Lightpanda (Best for headless AI automation)

- **GitHub:** [https://github.com/lightpanda-io/browser](https://github.com/lightpanda-io/browser)
- **Stars:** 11.9k
- **License:** AGPL-3.0
- **Language:** Zig + V8 JavaScript engine
- **Status:** Beta (actively developed)

**Performance vs Chrome:**
- 9x less memory usage
- 11x faster execution
- Instant startup (no GUI rendering overhead)

**Automation APIs supported:**
- Chrome DevTools Protocol (CDP) -- full WebSocket server
- Puppeteer compatible
- Playwright compatible
- chromedp (Go) compatible

**Windows installation:** Runs inside WSL (Windows Subsystem for Linux). Native Windows binaries are in development. Install client libraries (Puppeteer, etc.) on the Windows host; run the browser binary in WSL.

**AI pipeline fit:** Purpose-built for AI agents and automation. Its tiny footprint means you can run many parallel instances for web navigation training at scale. The CDP compatibility means existing Puppeteer/Playwright training harnesses work with minimal changes.

**Limitations:** Still in beta; not all Web APIs are implemented. May fail on complex JavaScript-heavy sites.

#### 2B. qutebrowser (Best for keyboard-driven interaction modeling)

- **GitHub:** [https://github.com/qutebrowser/qutebrowser](https://github.com/qutebrowser/qutebrowser)
- **Stars:** 11.3k
- **License:** GPL-3.0
- **Language:** Python + Qt/QtWebEngine (Chromium-based)

**Key features:**
- Vim-like keyboard-driven interface (every action is a named command)
- Userscript system: External scripts can interact with page content, receive environment variables about current URL/page, and return commands
- Command-based architecture (`:open`, `:click-element`, `:scroll`, etc.) -- every browser action has a discrete, named command
- IPC socket for external control
- Configurable via Python (`config.py`)

**Windows installation:** Prebuilt Windows releases available from the [releases page](https://github.com/qutebrowser/qutebrowser/releases). Also installable via pip: `pip install qutebrowser`.

**AI pipeline fit:** The discrete command vocabulary (open URL, click element, scroll, type text, navigate back) maps naturally to an action space for reinforcement learning agents. Userscripts provide a bridge for telemetry injection. The Python-native architecture makes integration with ML training loops straightforward.

**Limitations:** No official headless mode. Would need a virtual display (Xvfb) or similar for fully headless operation.

#### 2C. Min Browser (Best for lightweight Electron-based customization)

- **GitHub:** [https://github.com/minbrowser/min](https://github.com/minbrowser/min)
- **Stars:** 8.9k
- **License:** Apache-2.0
- **Language:** JavaScript (91.9%), built on Electron

**Key features:**
- Extremely minimal UI -- stripped-down browsing experience
- Userscript system for extensibility
- Built-in ad blocker and tracker blocker
- Tab grouping and task management
- Full Chromium renderer (via Electron)

**Windows installation:** Download prebuilt Windows installer from the [releases page](https://github.com/minbrowser/min/releases). For development: clone repo, `npm install`, `npm run build`, `npm start`.

**AI pipeline fit:** Being Electron-based means you can programmatically control it via Electron's built-in APIs (`BrowserWindow`, `webContents`). You could fork Min and add headless automation hooks directly. The Apache-2.0 license permits commercial use and modification. Its simplicity means less interference from UI complexity during automated browsing.

**Limitations:** No built-in headless mode or CDP support. Electron overhead is heavier than Lightpanda. Better suited as a starting point for a custom training browser than as a drop-in automation target.

### Honorable Mentions

- **Nyxt Browser** ([https://nyxt.atlas.engineer](https://nyxt.atlas.engineer)) -- Common Lisp-based, fully programmable via built-in REPL. Excellent scriptability but requires Lisp knowledge. Linux/macOS focused.
- **Falkon** -- KDE's Qt-based browser. Lightweight but limited automation APIs.

---

## 3. Open Source Educational Programs/Platforms

### 3A. Interactive Learning / Courseware

| Platform | Description | GitHub / URL | License |
|----------|-------------|--------------|---------|
| **GCompris** | Educational suite for ages 2-10, 180+ activities (math, science, reading, typing). Qt6-based, latest release 25.0. | [github.com/gcompris/GCompris-gtk](https://github.com/gcompris/GCompris-gtk) | GPL-3.0 |
| **Moodle** | World's most-used LMS (35M+ users, 48K+ sites). Course management, quizzes, grading, plugins. | [github.com/moodle/moodle](https://github.com/moodle/moodle) | GPL-3.0 |
| **Open edX** | MOOC platform (powers edX.org). Courseware, assessments, certificates, analytics. | [github.com/openedx](https://github.com/openedx) | AGPL-3.0 |
| **Kolibri** | Offline-first educational platform for low-resource environments. Curriculum alignment tools. | [github.com/learningequality/kolibri](https://github.com/learningequality/kolibri) | MIT |

### 3B. Choice-Based Interactive Fiction Engines

| Engine | Description | GitHub / URL | License | Headless? |
|--------|-------------|--------------|---------|-----------|
| **ChoiceScript** | Text-based multiple-choice game engine (JavaScript). See Section 4 for deep dive. | [github.com/dfabulich/choicescript](https://github.com/dfabulich/choicescript) | CSL v1.0 (non-commercial) | Yes (Node.js) |
| **Twine** | Visual story editor for branching narratives. Exports to HTML. Multiple story formats (Harlowe, SugarCube, Chapbook). | [github.com/klembot/twinern](https://twinery.org/) | GPL-3.0 | Partial (HTML output parseable) |
| **Ink (inkle)** | Professional narrative scripting language. C# compiler, JSON runtime. Used in 80 Degrees, Heaven's Vault. | [github.com/inkle/ink](https://github.com/inkle/ink) | MIT | **Yes** (inkjs for Node.js) |
| **Ren'Py** | Visual novel engine with Python scripting. Images, sound, branching dialogue. 4K+ published games. | [github.com/renpy/renpy](https://github.com/renpy/renpy) | MIT (+ some LGPL components) | Limited (Python API) |

**Best for AI headless automation:** Ink (via inkjs) and ChoiceScript (via headless.js) are the strongest candidates because both can run entirely in Node.js without any GUI.

### 3C. Life Simulation / Educational Games as AI Training Environments

| Project | Description | AI Training Potential |
|---------|-------------|----------------------|
| **OpenAI Gym / Gymnasium** | Standard RL environment interface. Many educational-style environments (CartPole, Taxi, FrozenLake). | Direct RL integration |
| **NetLogo** | Multi-agent modeling. Biology, economics, social science simulations. | Agent-based learning |
| **SimSE** | Software engineering process simulation game. | Process decision training |
| **Minetest** | Open-source Minecraft-like. Lua-scriptable, moddable. | Spatial reasoning, resource management |
| **OpenTTD** | Transport Tycoon Deluxe. Economy, logistics, city-building simulation. | Planning, optimization |

---

## 4. ChoiceScript -- Deep Dive

### GitHub Repository and License

- **Repository:** [https://github.com/dfabulich/choicescript](https://github.com/dfabulich/choicescript)
- **License:** ChoiceScript License (CSL) v1.0 -- **non-commercial only**. You may not use the interpreter or games written for it for commercial purposes (no sales, no ad revenue). Commercial licensing available via support@choiceofgames.com.
- **Language:** JavaScript (90.2%), HTML (7.5%), CSS (1.9%)
- **Key files:** `headless.js`, `compile.js`, `quicktest.js`, `randomtest.js`, `generator.js`, `generatorNode.js`

### Game Structure

A ChoiceScript game consists of plain text files organized as follows:

```
mygame/
  scenes/
    startup.txt          # Entry point -- defines global variables, scene list
    chapter1.txt          # Story scenes (one per file)
    chapter2.txt
    ending.txt
    choicescript_stats.txt # Stats screen definition
```

**startup.txt** must contain:
```
*title My Game Title
*author Author Name
*scene_list
  startup
  chapter1
  chapter2
  ending

*create strength 50
*create charm 30
*create has_sword false
```

**Scene files** use indentation-based scripting:
```
You enter the dark cave.

*choice
  #Draw your sword
    *if has_sword
      You brandish your blade!
      *set strength +10
      *goto fight
    *else
      You reach for a sword you don't have.
      *goto flee
  #Run away
    *goto flee
  #Negotiate
    *set charm +5
    *goto talk

*label fight
The creature attacks...
```

**Key commands:**
- `*create` / `*temp` -- declare persistent/temporary variables
- `*set` -- modify variables (supports `+`, `-`, `%+`, `%/`, etc.)
- `*choice` / `*fake_choice` -- present options to the player
- `*if` / `*elseif` / `*else` -- conditional branching
- `*goto` / `*goto_scene` / `*gosub` -- flow control
- `*finish` -- advance to next scene
- `*ending` -- end the game
- `*rand` -- random number generation
- `*stat_chart` -- define the stats display

### Headless Operation (No GUI)

**Yes, ChoiceScript can run headlessly.** The repo includes:

1. **`headless.js`** -- A Node.js-compatible entry point that runs the ChoiceScript interpreter without a browser DOM.

2. **npm package `choicescript`** (v1.2.0) -- Install with `npm install choicescript`. Provides CLI commands:
   ```bash
   choicescript quicktest    # Validate all paths
   choicescript randomtest   # Random automated playthroughs
   ```

3. **`randomtest.js`** -- Plays through the game thousands of times, making random selections at each `*choice`. Generates hit-count reports showing which lines were reached and how often. This is essentially an automated AI playthrough tool already built in.

4. **`quicktest.js`** -- Validates every path by "cheating" through both sides of every `*if` and every `#option` in every `*choice`.

### Programmatic Parsing of Choice Trees

To extract decision graphs from ChoiceScript games, you would:

1. **Parse the scene files** -- ChoiceScript's syntax is indentation-based plain text. A parser needs to:
   - Tokenize `*choice`, `#option`, `*if`, `*goto`, `*goto_scene`, `*label`, `*finish`, `*ending`
   - Track indentation depth for nesting
   - Resolve `*goto` targets to `*label` definitions within and across scenes

2. **Build a directed graph** where:
   - Nodes = labels, scene entry points, and choice points
   - Edges = player selections at `*choice` blocks + `*goto` transitions
   - Edge weights = variable changes (`*set` commands)

3. **Use the built-in testing infrastructure** -- `randomtest` already traverses the full game tree. Its output (hit counts per line) is effectively a coverage report of the decision graph. You could modify `randomtest.js` to emit structured JSON of every path taken.

4. **Leverage `generatorNode.js`** -- The repo includes `generator.js` and `generatorNode.js` which appear to be related to programmatic game generation/traversal.

No existing standalone "choice tree extractor" library was found, but the ChoiceScript codebase itself provides the parsing primitives needed to build one.

### Open Source Games for Training

- **DashingDon** ([dashingdon.com](https://dashingdon.com/)) -- Hosts hundreds of work-in-progress ChoiceScript games, most freely accessible for play. These are community-contributed and cover genres from fantasy to sci-fi to social simulation.
- **CoGDemos** ([cogdemos.ink](https://cogdemos.ink/)) -- Collaborative platform for testing and sharing ChoiceScript WIPs.
- **Choice of Games demo content** -- The official ChoiceScript repo includes a sample game (`web/mygame/`) as a starting point.
- **Hosted Games** ([hostedgames.org](https://hostedgames.org/)) -- Published ChoiceScript games (many free/demo versions available, though full versions are commercial).

**Important licensing note:** While ChoiceScript itself is non-commercial, games written in ChoiceScript by third parties may have their own licenses. The DashingDon WIP games are generally community-shared but may not have explicit open-source licenses.

---

## 5. Federated Learning Frameworks

### Comparison Table

| Framework | GitHub Stars | License | Install | HuggingFace Support | Consumer HW | Custom Training Loops |
|-----------|-------------|---------|---------|--------------------|--------------|-----------------------|
| **Flower** | 6.6k | Apache-2.0 | `pip install flwr` | **Native** (official examples) | **Yes** (RPi, Jetson, laptops) | **Yes** (full strategy customization) |
| **PySyft** | 9.7k | Apache-2.0 | `pip install syft` | Partial (DistilBert AST support) | Yes (edge devices) | Manual (you implement FL strategy) |
| **FATE** | 6k | Apache-2.0 | Docker Compose / KubeFATE | No native support | Heavy (enterprise-grade) | Limited (pre-built algorithms) |
| **FedML** | ~4k | Apache-2.0 | `pip install fedml` | Partial | Yes (RPi, Jetson) | Yes (FedAvg, FedProx, FedOpt, custom) |

### Framework Deep Dives

#### 5A. Flower (flwr.ai) -- RECOMMENDED

- **GitHub:** [https://github.com/adap/flower](https://github.com/adap/flower)
- **Website:** [https://flower.ai](https://flower.ai)
- **License:** Apache-2.0
- **Install:** `pip install -U flwr`

**Why Flower leads:**
- **Framework agnostic:** Works with PyTorch, TensorFlow, HuggingFace Transformers, JAX, scikit-learn, XGBoost, fastai, MLX, and more.
- **HuggingFace integration:** Official tutorial on [huggingface.co/blog/fl-with-flower](https://huggingface.co/blog/fl-with-flower). Demonstrated fine-tuning DistilBERT, Llama-3.2-1B, and LeRobot models in federated settings.
- **Consumer hardware:** Explicitly supports Raspberry Pi, NVIDIA Jetson, Android, iOS. Can run simulations on a single laptop.
- **Custom strategies:** Full API for building strategies from scratch. Override `configure_fit()`, `aggregate_fit()`, `configure_evaluate()`, etc. Built-in FedAvg, FedProx, FedAdam, FedAdagrad, and more.
- **GPU fractional allocation:** Configure `client-resources` to share a single GPU across multiple simulated clients.
- **Windows:** Fully supports Linux/macOS. Windows support via PowerShell (Ray backend is experimental on Windows; WSL2 recommended for simulations).

**Minimal example:**
```python
import flwr as fl

# Define client with custom training loop
class MyClient(fl.client.NumPyClient):
    def fit(self, parameters, config):
        # Your PyTorch/HF training loop here
        set_parameters(model, parameters)
        train(model, trainloader, epochs=1)
        return get_parameters(model), len(trainloader.dataset), {}

    def evaluate(self, parameters, config):
        set_parameters(model, parameters)
        loss, accuracy = test(model, testloader)
        return float(loss), len(testloader.dataset), {"accuracy": accuracy}

# Start federated learning
fl.simulation.start_simulation(
    client_fn=client_fn,
    num_clients=10,
    config=fl.server.ServerConfig(num_rounds=3),
)
```

#### 5B. PySyft (OpenMined)

- **GitHub:** [https://github.com/OpenMined/PySyft](https://github.com/OpenMined/PySyft)
- **License:** Apache-2.0
- **Install:** `pip install -U syft` (requires Python 3.10+)
- **Community:** 17,000+ members in OpenMined network

**Differentiator:** PySyft's focus is **remote data science** -- sending code to where data lives, receiving only results. This is broader than pure federated learning; it encompasses differential privacy, secure multi-party computation, and encrypted computation.

**Strengths:** Most popular FL framework by stars (9.7k). Strong privacy primitives. Good for scenarios where you need formal privacy guarantees beyond basic FL.

**Weaknesses:** No built-in FL algorithms (you implement FedAvg yourself). Steeper learning curve. GPU support on consumer hardware is still evolving. HuggingFace integration is limited to basic AST support for DistilBert.

#### 5C. FATE (FederatedAI)

- **GitHub:** [https://github.com/FederatedAI/FATE](https://github.com/FederatedAI/FATE)
- **License:** Apache-2.0
- **Install:** Docker Compose via KubeFATE, or PyPI
- **Origin:** WeBank (Tencent subsidiary), Linux Foundation project

**Strengths:** Industrial-grade. Large library of built-in algorithms (gradient-boosted trees, logistic regression, neural networks). FATEBoard for visualization. FATEServing for model deployment. FATE-LLM extension for federated LLM training.

**Weaknesses:** Enterprise-focused -- heavy infrastructure requirements (Kubernetes preferred). No native HuggingFace support. Not designed for consumer hardware. Documentation primarily in Chinese with English translations. Docker Compose deployment is the minimum viable path but still resource-intensive.

#### 5D. FedML

- **GitHub:** [https://github.com/FedML-AI/FedML](https://github.com/FedML-AI/FedML)
- **License:** Apache-2.0
- **Install:** `pip install fedml`
- **Note:** Now operating as TensorOpera.ai (commercial platform built on the open-source library)

**Strengths:** Supports simulation on a single laptop, cross-silo distributed training, and cross-device edge training. Built-in FedAvg, FedProx, FedOpt, FedAdam. Supports IoT devices (RPi 4, Jetson Nano). Cross-cloud job scheduling via FedML Launch.

**Weaknesses:** The open-source library has been partially subsumed by the commercial TensorOpera platform. Community engagement may be shifting toward the commercial offering.

### Recommendation for This Pipeline

**Flower is the clear winner** for an AI training pipeline that needs to:
- Work with HuggingFace models (native, documented integration)
- Run on consumer hardware (laptop with optional GPU)
- Support custom training loops (full strategy API)
- Integrate with other tools via standard Python (easy to orchestrate from n8n)

---

## 6. How These Connect: The Orchestrated AI Training Pipeline

### Architecture: n8n as the Central Orchestrator

```
                          +------------------+
                          |      n8n         |
                          | (Orchestrator)   |
                          +--------+---------+
                                   |
              +--------------------+--------------------+
              |                    |                    |
    +---------v-------+  +--------v--------+  +--------v--------+
    | Federated       |  | ChoiceScript /  |  | Telemetry &     |
    | Learning (Flower)|  | Ink Game Engine |  | Model Registry  |
    +---------+-------+  +--------+--------+  +--------+--------+
              |                    |                    |
              +--------------------+--------------------+
                                   |
                          +--------v--------+
                          | Fine-Tuning &   |
                          | Kernel Deploy   |
                          +-----------------+
```

### Step-by-Step Pipeline Flow

**Stage 1: n8n Triggers Federated Learning Initialization**
- A scheduled n8n workflow (cron trigger or webhook from a CI/CD system) initiates a new training round.
- n8n's Execute Command node SSH-es into a training server (or local machine) and launches the Flower server:
  ```
  n8n Webhook POST /start-training
    -> Execute Command: "python flower_server.py --num-rounds 5 --strategy FedAdagrad"
    -> HTTP Request: Register training run in MLflow/W&B experiment tracker
  ```
- n8n monitors the Flower server's status endpoint, routing failures to alert channels.

**Stage 2: AI Agents Play ChoiceScript/Ink Games**
- Each Flower client runs an AI agent that plays interactive fiction games as its "training data collection" phase.
- The agent uses the **ChoiceScript `headless.js`** or **inkjs** runtime in Node.js:
  ```javascript
  // Agent plays Ink story headlessly
  const {Story} = require('inkjs');
  const storyJSON = fs.readFileSync('scenario.ink.json', 'utf-8');
  const story = new Story(storyJSON);
  
  while (story.canContinue || story.currentChoices.length > 0) {
    let text = story.ContinueMaximally();
    let choices = story.currentChoices;
    // AI model selects a choice based on its current policy
    let selected = model.selectAction(text, choices);
    story.ChooseChoiceIndex(selected.index);
    // Log decision telemetry
    telemetry.log({text, choices, selected, variables: story.variablesState});
  }
  ```
- Games serve as structured decision environments where the AI must: evaluate context, weigh consequences (tracked via game variables like strength/charm/reputation), and optimize for outcomes (reaching good endings, maximizing stats).

**Stage 3: Telemetry Logged**
- Each game playthrough produces a structured trace:
  ```json
  {
    "run_id": "abc123",
    "game": "ethical_dilemmas_v2",
    "decisions": [
      {"scene": "startup", "choice_text": "Help the stranger", "variables_after": {"karma": 60}},
      {"scene": "chapter2", "choice_text": "Share resources", "variables_after": {"karma": 80}}
    ],
    "outcome": "good_ending",
    "total_reward": 0.85
  }
  ```
- n8n receives this telemetry via a webhook endpoint and routes it to:
  - A PostgreSQL/SQLite database for persistent storage
  - A file system (JSON lines) for batch training consumption
  - Optionally, a dashboard (Grafana, Metabase) for human monitoring

**Stage 4: Models Fine-Tuned on Decision Paths**
- n8n triggers a fine-tuning job once sufficient telemetry has accumulated (threshold-based or scheduled):
  ```
  n8n Webhook: /telemetry-batch-ready
    -> IF decision_count > 10000:
        -> Execute Command: "python finetune.py --data telemetry.jsonl --base-model distilbert-base"
        -> Flower aggregates fine-tuned weights across all clients
        -> HTTP Request: Push model to HuggingFace Hub or local registry
  ```
- The Flower framework handles aggregation: each client fine-tunes on its local game traces, then Flower aggregates the updated weights using FedAvg/FedAdagrad without any client needing to share its raw decision data.
- This creates a privacy-preserving loop where the central model improves from distributed decision-making experience.

**Stage 5: Graduated Kernels Deployed**
- n8n evaluates the newly aggregated model against a benchmark suite (a set of standardized ChoiceScript scenarios with known optimal paths):
  ```
  n8n Workflow:
    -> Execute Command: "python evaluate.py --model latest --benchmark ethics_suite_v3"
    -> IF accuracy > threshold AND safety_score > minimum:
        -> Tag model as "graduated"
        -> Deploy to inference endpoint
        -> Notify team via Slack/email
    -> ELSE:
        -> Log failure metrics
        -> Trigger remediation workflow (more training rounds, different game scenarios)
  ```
- "Graduated kernels" are model checkpoints that have demonstrated competence across the decision-making benchmark. n8n manages the promotion pipeline: staging, evaluation, approval gates (optional human-in-the-loop), and production deployment.

### Why This Architecture Works

1. **n8n provides the glue** -- It connects heterogeneous systems (Python FL servers, Node.js game engines, databases, deployment targets) without requiring them to know about each other. Each component exposes a simple API; n8n wires them together.

2. **ChoiceScript/Ink games provide structured training environments** -- Unlike raw text or web browsing, interactive fiction presents clear decision points with measurable consequences. The state space is well-defined (game variables), the action space is discrete (choices), and outcomes are evaluable (endings, stat values). This is ideal for training decision-making models.

3. **Flower handles the federated aggregation** -- Multiple agents can independently play different games or the same games with different strategies, and Flower aggregates their learned policies without centralizing raw training data. This scales horizontally and preserves privacy.

4. **The headless browser layer** (Lightpanda or qutebrowser) extends this to web-based training when needed -- an agent that has been pre-trained on structured ChoiceScript decisions can graduate to navigating real web interfaces, with the same n8n orchestration pipeline managing the transition.

---

## Sources

- [n8n GitHub Repository](https://github.com/n8n-io/n8n)
- [n8n npm Installation Docs](https://docs.n8n.io/hosting/installation/npm/)
- [n8n Docker Compose Docs](https://docs.n8n.io/hosting/installation/server-setups/docker-compose/)
- [n8n Webhook Node Docs](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/)
- [Orchestrating PyTorch Training With n8n (techbuddies.io)](https://www.techbuddies.io/2026/01/22/orchestrating-pytorch-training-with-n8n-practical-mlops-automation/)
- [Lightpanda GitHub Repository](https://github.com/lightpanda-io/browser)
- [qutebrowser GitHub Repository](https://github.com/qutebrowser/qutebrowser)
- [Min Browser GitHub Repository](https://github.com/minbrowser/min)
- [ChoiceScript GitHub Repository](https://github.com/dfabulich/choicescript)
- [ChoiceScript Introduction](https://www.choiceofgames.com/make-your-own-games/choicescript-intro/)
- [ChoiceScript Game Structure Wiki](https://choicescriptdev.fandom.com/wiki/Structure_of_a_ChoiceScript_game)
- [ChoiceScript Automatic Testing](https://choicescriptdev.fandom.com/wiki/Automatically_testing_your_game_(with_CMD_prompt))
- [DashingDon ChoiceScript Game Hosting](https://dashingdon.com/)
- [CoGDemos](https://cogdemos.ink/)
- [Ink (inkle) GitHub Repository](https://github.com/inkle/ink)
- [inkjs npm Package / GitHub](https://github.com/y-lohse/inkjs)
- [inkjs Story API Tutorial](https://videlais.com/2019/05/27/javascript-ink-part-2-story-api/)
- [Twine](https://twinery.org/)
- [Ren'Py GitHub Repository](https://github.com/renpy/renpy)
- [GCompris GitHub Repository](https://github.com/gcompris/GCompris-gtk)
- [Flower (flwr.ai) GitHub Repository](https://github.com/adap/flower)
- [Flower Website](https://flower.ai/)
- [Federated Learning using HuggingFace and Flower](https://huggingface.co/blog/fl-with-flower)
- [Flower Custom Strategy Tutorial](https://flower.ai/docs/framework/tutorial-series-build-a-strategy-from-scratch-pytorch.html)
- [Flower Simulation Docs](https://flower.ai/docs/framework/how-to-run-simulations.html)
- [PySyft GitHub Repository](https://github.com/OpenMined/PySyft)
- [OpenMined](https://openmined.org/)
- [FATE GitHub Repository](https://github.com/FederatedAI/FATE)
- [FedML GitHub Repository](https://github.com/FedML-AI/FedML)
- [Federated Learning Frameworks Comparison (Medium)](https://medium.com/elca-it/flower-pysyft-co-federated-learning-frameworks-in-python-b1a8eda68b0d)
- [Top 7 FL Frameworks (Apheris)](https://www.apheris.com/resources/blog/top-7-open-source-frameworks-for-federated-learning)
- [Best Headless Browsers 2026 (ZenRows)](https://www.zenrows.com/blog/best-headless-browser)
- [HeadlessBrowsers List (GitHub)](https://github.com/dhamaniasad/HeadlessBrowsers)