# Notes on Large Language Models and Emerging Architectures

Status: research note
Source: `C:\Users\issda\Downloads\SCBE Ecosystem Growth.pdf`
Purpose: preserve the useful architecture discussion in repo-native Markdown without treating speculative ideas as proven implementation.

## 1. Autoregressive Language Models

### 1.1 Training by next-token prediction

Most widely used LLMs, including GPT-style models, are trained through next-token prediction. Text is tokenized into a sequence. At each position, the model receives the preceding context and predicts the next token. Causal left-to-right attention prevents the model from using future tokens during training.

Training usually uses cross-entropy loss: the model is penalized when it assigns low probability to the true next token. Over massive corpora, this produces representations that capture syntax, semantics, style, and longer-range statistical patterns.

### 1.2 Generation process and strengths

At inference time, autoregressive models generate one token, append it to the context, then repeat. This is simple, powerful, and responsible for much of the current performance of LLMs in summarization, question answering, dialogue, code generation, and general writing.

### 1.3 Limits of sequential generation

Autoregressive decoding is inherently sequential. That creates both engineering and conceptual limits:

- Inference cannot be fully parallelized across output tokens.
- The model commits to one token at a time.
- Earlier output is difficult to revise once emitted.
- Multiple possible continuations are collapsed into a single visible path.
- Later generation may spend compute on token-level continuation even when the high-level semantic direction is already mostly determined.

For SCBE, this matters because agentic workflows should not rely on free-form next-token continuation as the only control surface. The harness, board, verifier, and completion gates should carry state outside the model.

## 2. Diffusion Language Models

Diffusion language models approach generation through a noise-to-text process rather than strict next-token prediction. A forward process corrupts clean text over multiple steps. A reverse process learns to reconstruct the original text from the corrupted representation.

### 2.1 Advantages

Diffusion-style text systems can support more parallel generation and bidirectional conditioning. Instead of emitting one irreversible next token at a time, they can refine a whole sequence through iterative denoising.

Potential advantages:

- Parallel token refinement.
- Bidirectional context use.
- More global revision during generation.
- Better fit for workflows where an output needs to be shaped as a whole artifact.

Hybrid systems can combine an autoregressive backbone for global structure with diffusion-like refinement for local detail.

### 2.2 Challenges

Diffusion language models are still younger than autoregressive transformer systems. They can be computationally expensive, require careful noise-process design, and are not yet a universal replacement for mainstream autoregressive LLMs.

For SCBE, the practical takeaway is not "replace the model." It is: keep the harness model-agnostic so future non-autoregressive or hybrid generators can plug into the same governance, verification, and workflow board.

## 3. Energy-Based Models

Energy-based models assign a scalar energy to a configuration. Low-energy states represent desirable or likely configurations; high-energy states represent undesirable or unlikely configurations. In generative modeling, probabilities can be derived from the energy landscape, often using a Gibbs-style distribution.

### 3.1 Training and applications

EBMs can model global consistency and high-order interactions. They are attractive for tasks where the whole configuration matters more than a left-to-right sequence.

Challenges:

- The partition function is often intractable.
- Training can be unstable.
- Approximate methods such as contrastive divergence are commonly needed.
- Local minima can be a practical problem.

For SCBE, the useful analogy is the "cost landscape." A governed agent should not only ask "what token comes next?" It should ask "which proposed state has acceptable cost under the policy, evidence, and workflow constraints?"

## 4. Graph Neural Networks and LLMs

Graph neural networks operate on nodes and edges. They are built for relational structure: entities, dependencies, links, flows, ownership, provenance, and graph-local updates.

LLMs operate primarily on token sequences. Attention lets them model dependencies inside that sequence, but the input still reaches the model as ordered tokens rather than as a native graph of executable relations.

### 4.1 Complementary strengths

GNNs are strong where the core problem is relational:

- Dependency graphs.
- Knowledge graphs.
- Social or communication networks.
- Code reference graphs.
- Workflow state graphs.

LLMs are strong where the core problem is language:

- Natural language understanding.
- Text transformation.
- Explanation.
- Summarization.
- Flexible instruction following.

### 4.2 Hybrid approaches

Modern systems increasingly combine them:

- Graph-enhanced LLMs inject structured graph context into model prompts or model internals.
- LLM-powered graph construction extracts entities and relationships from text.
- Code agents use source graphs, symbol indexes, ASTs, and dependency maps to retrieve the right context before editing.

For SCBE, this supports the agent-bus direction: the model proposes moves, but external graph and board structures decide legal transitions, completion gates, and evidence trails.

## 5. Toward Non-Sequential Semantic Representations

This section is speculative architecture framing, not a claim that SCBE already implements a replacement for transformers.

Current LLMs expose language as sequences of discrete tokens. Human cognition likely includes richer dynamics: relational memory, embodied feedback, social context, parallel possibilities, and later revision of earlier interpretations.

Possible directions:

- Semantic field convergence: multiple candidate meanings move toward stable interpretation.
- Graph-based pathfinding: concepts, tools, files, and actions become nodes with legal transitions.
- Bounded drift across manifolds: identity and task state can move, but only inside governed limits.
- Multi-board workflow play: tasks are represented as pieces or moves across layered boards rather than as raw prose.
- External state memory: continuity is held by logs, receipts, artifacts, tests, and source graphs rather than only by model context.

For SCBE, the near-term implementation target is not a new foundation model. The practical target is a governed execution architecture around any model:

1. The model proposes candidate moves.
2. The semantic bus normalizes intent.
3. The board or workflow graph checks legal transitions.
4. GeoSeal/governance gates decide whether the move can execute.
5. The verifier decides whether the task is actually complete.
6. The receipt/log preserves what happened.

That is the actionable version of "non-sequential semantics": externalize state, legal moves, and completion checks so a small or weak model can operate inside a stronger scaffold.

## 6. SCBE Design Implications

The strongest product lesson from this note is that model intelligence and system intelligence are not the same thing.

SCBE should keep improving the system-level parts that models do not reliably provide by themselves:

- Retrieval: find the relevant files, docs, tools, and prior decisions.
- Source graphs: map code symbols, dependency edges, workflow nodes, and tests.
- Legal move matrix: constrain what an agent can do next.
- Verification loop: done is accepted only when external checks pass.
- Artifact freshness: old results cannot prove current readiness.
- Audit trail: record original input, corrected input, routing, execution, and completion proof.
- Model-agnostic control: Ollama, free APIs, BYOK, or paid frontier models should all use the same harness.

The architecture direction is therefore:

> Do not make every model smarter by assumption. Make the environment more structured, more visible, and harder to misuse.

## References

- Sebastian Raschka, "How does next-token prediction train a large language model?" https://sebastianraschka.com/faq/docs/next-token-prediction.html
- Apple Machine Learning Research, "Your LLM Knows the Future: Uncovering Its Multi-Token Prediction Potential." https://machinelearning.apple.com/research/prediction-potential
- Hugging Face blog, "Diffusion Language Models: The New Paradigm." https://huggingface.co/blog/ProCreations/diffusion-language-model
- DeepAI, "Energy-based Models Definition." https://deepai.org/machine-learning-glossary-and-terms/energy-based-models
- Symmetry Systems, "Large Language Models vs Graph Neural Networks: It Depends." https://www.symmetry-systems.com/blog/large-language-models-vs-graph-neural-networks-it-depends/
