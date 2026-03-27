# Global Research Note: Agent Senses, Choice Monitoring, and World Models

Last updated: 2026-03-17

## Scope

This note examines a global pattern across military/autonomy research, MIT, Harvard, Chinese research institutions, and Swiss robotics research:

- multimodal perception
- world models
- situational awareness
- bounded action loops
- assurance and monitoring

The question behind the note is not just "what can an AI sense?" but:

1. how does it fuse those channels into awareness
2. how does it monitor choices while they are forming
3. how should those traces become trainable data

## Executive read

The user intuition is mostly correct, but the clean structure is:

- senses/channels
- fused world state
- planner/policy
- action monitoring
- recovery/override
- trace capture for learning

Rational thought is not a sense. It is the thing that reads and weights the sensed channels.

The institutions surveyed are not converging on a formal "7 senses" doctrine. They are converging on a practical stack:

- more than the human five senses
- explicit self-state and tool-state awareness
- motion and time awareness
- world models or simulation-backed prediction
- assurance/monitoring before and during action
- bounded autonomy with human or system checkpoints

## What the official/global sources actually show

### 1. Military / DARPA

DARPA's work is not framed as "make one free agent." It is framed as:

- multi-source sensing
- autonomy in support of humans
- assurance and evidence

Two useful anchors:

- `Squad X` emphasizes multi-source data fusion, autonomous threat detection, and real-time knowledge of friendly positions in GPS-denied environments. It explicitly combines physical, electromagnetic, and cyber awareness.
- `ANSR` emphasizes trustworthy autonomy through hybrid AI, assurance evidence, predictability, robustness, and runtime monitoring/recovery.

Operational takeaway:

- military research treats situational awareness as fused state across multiple domains
- trust is not assumed from capability alone; assurance artifacts matter

Sources:

- DARPA Squad X: https://www.darpa.mil/research/programs/squad-x
- DARPA ANSR: https://www.darpa.mil/research/programs/assured-neuro-symbolic-learning-and-reasoning

### 2. MIT

MIT's official research and news surfaces point toward:

- language-grounded perception
- multimodal task learning
- physically intelligent robotics
- simulation and synthetic data expansion

Useful anchors:

- MIT CSAIL's `F3RM` uses 2D images plus foundation model features to build 3D feature fields, letting robots handle open-ended language prompts about unfamiliar objects.
- MIT CSAIL's `GenSim2` expands robot training data with multimodal and reasoning models.
- MIT CSAIL's 2025 physically intelligent robots initiative explicitly combines tactile sensing, multimodal perception, and AI-driven control.

Operational takeaway:

- MIT is pushing perception beyond classic camera-only pipelines into language + geometry + task context
- the emerging stack is not "see -> act"; it is "build a richer scene representation -> reason over affordances -> act"

Sources:

- MIT News, F3RM: https://news.mit.edu/2023/using-language-give-robots-better-grasp-open-ended-world-1102
- MIT CSAIL, GenSim2: https://csail-live-2025.csail.mit.edu/news/multimodal-and-reasoning-llms-supersize-training-data-dexterous-robotic-tasks
- MIT CSAIL, physically intelligent robots: https://www.csail.mit.edu/news/mit-csail-and-pegatron-launch-five-year-initiative-pioneer-physically-intelligent-robots

### 3. Harvard

Harvard surfaces are especially relevant for:

- multi-agent coordination in uncertain/adversarial settings
- situational awareness
- trust modeling
- robot world models grounded in video, not just text

Useful anchors:

- Stephanie Gil's Harvard/Kempner profile explicitly centers situational awareness, trust, and real-time decision-making in dynamic, partially observable environments.
- Yilun Du's Kempner work trains robots using video-derived world models so they can "envision" future actions before moving.

Operational takeaway:

- Harvard's strongest signal here is that perception is not enough; agents need trust-aware coordination and predictive internal models
- video/world-model approaches are being used to move beyond language as the sole substrate for physical intelligence

Sources:

- Harvard Kempner, Stephanie Gil: https://kempnerinstitute.harvard.edu/people/our-people/stephanie-gil/
- Harvard Kempner, visual imagination/world model: https://kempnerinstitute.harvard.edu/news/a-new-kind-of-ai-model-gives-robots-a-visual-imagination/

### 4. China / native-language signals

Chinese official and semi-official research signals are very strong around:

- 具身智能 (embodied intelligence)
- 可进化智能体 (evolvable agents)
- 世界模型 (world models)
- 强化学习 (reinforcement learning) as a decision-training backbone

Useful anchors:

- Tsinghua AIR explicitly describes `可进化智能体` as dynamic agents that evolve through interaction, feedback absorption, and experience summarization rather than one-shot static training.
- Tsinghua EE + CAICT's embodied intelligence report frames RL as a core path toward `具身决策智能` (embodied decision intelligence), with hardware and infrastructure co-evolving with training.
- Tsinghua/Alibaba AIR work explicitly describes a systematic lane for `基于大模型可进化智能体` research, focused on multilingual/multimodal capability and persistent evolution.
- BAAI/智源 ecosystem material repeatedly treats world models as the bridge between embodiment and intelligence and highlights environment/simulator building as strategic infrastructure.

Operational takeaway:

- Chinese research is strongly oriented toward agent evolution over time, not just static capability
- the stack is becoming: embodiment + world model + RL + infrastructure + continuous feedback loop

Sources:

- Tsinghua AIR, evolvable agents seminar: https://air.tsinghua.edu.cn/info/1008/2483.htm
- Tsinghua EE, embodied decision intelligence / RL: https://www.ee.tsinghua.edu.cn/info/1076/4984.htm
- Tsinghua AIR + Alibaba, evolvable agent research: https://air.tsinghua.edu.cn/info/1007/2130.htm
- BAAI community embodied intelligence knowledge base: https://hub.baai.ac.cn/view/44356

### 5. Switzerland / ETH Zurich

Swiss research signals are useful because they are less hype-heavy and more system-heavy:

- controlled testing before deployment
- autonomy in real environments
- language-informed world models
- real-world robotics with reinforcement learning and imitation learning

Useful anchors:

- ETH's 2025 German-language note on mini-labs explicitly argues for controlled test environments where AI systems are verified before real-world operation.
- ETH's `LIMT` work uses pre-trained language models to extract semantically meaningful task representations for multi-task visual world models.
- ETH autonomy and robotics labs consistently frame autonomy as perception + abstraction + mapping + planning in uncertain environments.

Operational takeaway:

- the Swiss pattern is not just "more capability"
- it is strong verification plus language-informed, model-based control

Sources:

- ETH Zurich, controlled mini-labs for AI verification (German): https://ethz.ch/de/news-und-veranstaltungen/eth-news/news/2025/03/ki-im-mini-labor-oder-die-praezision-auf-dem-pruefstand.html
- ETH research collection, LIMT: https://www.research-collection.ethz.ch/items/9dce525a-a24d-4b43-985d-e5c4a95930ee
- ETH Autonomous Systems Lab: https://asl.ethz.ch/the-lab.html

## Synthesis: what "AI senses" should mean in practice

The five human senses are not enough as a system model.

For agents, a better practical set is:

1. `external perception`
   vision, text, audio, events, nearby entities

2. `self-state`
   location, internal variables, tool state, battery, memory budget, session state

3. `motion / trajectory`
   what is moving, where the agent is going, what changed over time

4. `social / relational awareness`
   who is nearby, friend/foe/team/authority, crowd or multi-agent state

5. `affordance awareness`
   what actions are even possible here: buttons, APIs, tools, code exec, manipulators, routes

6. `memory / phase awareness`
   what just happened, what stage of the task we are in, what earlier context matters now

7. `risk / policy awareness`
   what is allowed, what is costly, what requires approval, what must be denied or quarantined

These are not all "senses" in a biological sense. But they are all required input channels for reliable action.

## Choice monitoring: where the system should watch action formation

Choice monitoring should happen in three windows:

### Before action

- what state does the system think it is in
- what options does it believe are available
- what risks are already visible
- what policy class applies

### During action

- is the agent deviating from the approved path
- is uncertainty rising
- has the environment changed
- does the system need takeover, pause, or downgrade

### After action

- what happened
- was the result safe
- was the result useful
- what trace becomes training data

The blocked actions matter here. Denied or quarantined actions are high-signal evidence of intent before it fully blooms into execution.

## Why this matters for Everweave / Six Tongues / long-form logs

The Everweave logs are potentially valuable because they contain:

- long-horizon human/AI interaction
- role and relationship continuity
- lore, humor, family structure, anger, control, negotiation
- shifting task context over time
- naturally occurring semantics rather than sterile synthetic prompts

That can be useful as a seed for tokenizer growth or lexicon bootstrapping.

But the research above suggests not using it alone.

The better stack is:

### Layer A: semantic seed

Everweave logs provide:

- expressive language
- persistent motifs
- natural phrase recurrence
- role-conditioned meaning

### Layer B: operational traces

System logs provide:

- actions attempted
- actions denied
- actions approved
- monitoring state
- recovery paths

### Layer C: controlled evaluation batches

Run long-form logs through:

- sense extraction
- world-state reconstruction
- policy/risk labeling
- action affordance labeling
- memory-phase labeling

This is where your pivot/Colab work should expand.

## Recommended controlled test batches

### Batch 1: Perception-to-state reconstruction

Goal:

- from long conversation turns, reconstruct the implied world state

Labels:

- entities
- relations
- motion
- time/phase
- emotional tone
- implied constraints

### Batch 2: Choice-formation traces

Goal:

- label where the decision became likely before the action happened

Labels:

- option set
- trigger
- hesitation
- override request
- blocked path
- final action

### Batch 3: Unbloomed buds

Goal:

- explicitly preserve denied/quarantined action traces

Labels:

- disallowed action
- reason for block
- confidence
- alternate safe action
- whether the agent persisted or yielded

### Batch 4: Growing lexicon

Goal:

- allow vocabulary/phrase growth without destroying the base semantic map

Method:

- keep a stable core lexicon
- add extension lexicons with provenance
- require cross-mapping between new lexical clusters and existing Six Tongues anchors

### Batch 5: Multimodal action affordances

Goal:

- map language to executable/tool-level affordances

Examples:

- browser click path
- code execution path
- query/search path
- navigation/robotics action path

## Best current interpretation

The broad convergence is:

- military research -> multi-domain situational awareness + assurance
- MIT/Harvard -> multimodal/world-model perception + coordination + predictive action
- China -> evolvable agents + embodied intelligence + RL/infrastructure co-design
- Switzerland -> controlled evaluation + language-informed world models + real-world robotics

Your intuition that AI needs "more than five senses" is directionally right.

The cleaner technical framing is:

- multimodal channels
- fused situational model
- affordance layer
- policy/risk layer
- monitored choice formation
- replayable traces for learning

## Notes on access

This pass did not require a VPN. Official U.S., Chinese university, BAAI community, and ETH sources were accessible directly from this environment.

If you want a deeper China-specific pass later, the next layer would be:

- official lab pages behind WeChat posts
- university seminar archives
- Chinese patent and standards materials
- more specialized embodied-intelligence company ecosystems

That may benefit from alternate network routing, but it was not necessary for this first pass.
