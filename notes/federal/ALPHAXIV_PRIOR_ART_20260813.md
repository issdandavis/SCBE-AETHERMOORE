# alphaXiv prior-art sweep -- 2026-08-13

Run with the `axv2_` alphaXiv API key over MCP (`api.alphaxiv.org/mcp/v1`),
`discover_papers`, difficulty 7. Raw ranked output preserved below.

## What the ranking shows

The 11 hits fall into two clusters that **do not touch each other**:

| cluster | papers |
|---|---|
| CFI / control-flow attestation | WarpGuard (CUDA SASS, 2026-06), WarpGuard CPU-GPU CFA (2026-07), HPCCFA hardware perf counters (2026-03), DeepCheck non-intrusive CFI via deep learning (2019-05), GNN explanations for malware on CFGs (2025-04) |
| hyperbolic embeddings | Hyperbolic Graph Embeddings survey + anomaly-detection eval (2025-12), Euclidean+hyperbolic node anomaly detection (2025-10), Balanced hyperbolic embeddings as OOD detectors (2025-06), Hyperbolic Neural Networks (2018-05, ETH Zurich, 442 views) |

Every CFI paper is Euclidean or counter-based. Every hyperbolic paper targets
anomaly / OOD detection on graphs, not control-flow integrity. **Nothing in this
retrieval bridges the two**, which is the exact seam SCBE-2026-0001 claims.

**This is a signal, not a clearance.** One agentic retrieval over one corpus is
not a prior-art search: alphaXiv indexes arXiv only -- no patents, no USPTO, no
IEEE/ACM paywalled venues, and explicitly no biomedical. Patentability searching
is an attorney and examiner function. Treat this as "the obvious adjacent
literature does not already do this", nothing stronger.

## Worth actually reading before the SBIR narrative

- **Hyperbolic Graph Embeddings: a Survey and an Evaluation on Anomaly Detection**
  (2512.18826) -- closest thing to an independent check on whether hyperbolic beats
  Euclidean for this class of problem. Relevant because our own measurement found
  d_H did NOT beat cosine on trust AUC; this survey is the place to see whether
  that null is expected or anomalous.
- **DeepCheck** (1905.01858) -- non-intrusive CFI, the incumbent framing to
  differentiate against.
- **HPCCFA** (2603.29749) -- hardware performance counters for CFA. Directly
  competes on the "low overhead" claim, so its overhead numbers are the honest
  baseline to cite rather than the generic "10-20% for label-based CFI".

---

## Raw output

1. [ID=2605.28694] **E-Path: Equality Saturation for Control-Flow Graphs** (https://www.alphaxiv.org/abs/2605.28694). Published 2026-05-27 · 1 votes · 6 views: Modern equality saturation systems excel at expression-level rewrites by exploring large spaces of equivalent programs without suffering from the phase-ordering problem. How- ever, these systems strug...
2. [ID=2606.11871] **WarpGuard: Protected-Site Control-Flow Integrity for CUDA SASS Binaries** (https://www.alphaxiv.org/abs/2606.11871). Published 2026-06-10 · 2 votes · 4 views: Recent CUDA exploitation work shows that GPU memory bugs can escalate into device-side control-flow corruption, as kernels later consume corrupted return continuations, function pointers, dispatch-tab...
3. [ID=2607.13640] **WarpGuard: Towards Control-Flow Attestation for Heterogeneous CPU-GPU Execution** (https://www.alphaxiv.org/abs/2607.13640). Published 2026-07-15 · 0 votes · 3 views: Heterogeneous CPU-GPU workloads are increasingly used in safety-critical embedded systems, yet no existing approach provides joint attestation of their execution. Prior Control-Flow Attestation (CFA) ...
4. [ID=2603.29749] **HPCCFA: Leveraging Hardware Performance Counters for Control Flow Attestation** (https://www.alphaxiv.org/abs/2603.29749). Published 2026-03-31 · 1 votes · 2 views: Trusted Execution Environments (TEEs) allow the secure execution of code on remote systems without the need to trust their operators. They use static attestation as a central mechanism for establishin...
5. [ID=2512.18826] **Hyperbolic Graph Embeddings: a Survey and an Evaluation on Anomaly Detection** (https://www.alphaxiv.org/abs/2512.18826). Published 2025-12-21 · 2 votes · 15 views: This survey reviews hyperbolic graph embedding models, and evaluate them on anomaly detection, highlighting their advantages over Euclidean methods in capturing complex structures. Evaluating models l...
6. [ID=2510.11827] **Combining Euclidean and Hyperbolic Representations for Node-level Anomaly Detection** (https://www.alphaxiv.org/abs/2510.11827). Published 2025-10-13 · 1 votes · 7 views: Node-level anomaly detection (NAD) is challenging due to diverse structural patterns and feature distributions. As such, NAD is a critical task with several applications which range from fraud detecti...
7. [ID=2506.10146] **Balanced Hyperbolic Embeddings Are Natural Out-of-Distribution Detectors** (https://www.alphaxiv.org/abs/2506.10146). Published 2025-06-11 by University of Amsterdam · 3 votes · 52 views: Out-of-distribution recognition forms an important and well-studied problem in deep learning, with the goal to filter out samples that do not belong to the distribution on which a network has been tra...
8. [ID=1905.01858] **DeepCheck: A Non-intrusive Control-flow Integrity Checking based on Deep  Learning** (https://www.alphaxiv.org/abs/1905.01858). Published 2019-05-06 by Hunan University · 2 votes · 8 views: Code reuse attack (CRA) is a powerful attack that reuses existing codes to
hijack the program control flow. Control flow integrity (CFI) is one of the
most popular mechanisms to prevent against CRAs. ...
9. [ID=2504.16316] **On the Consistency of GNN Explanations for Malware Detection** (https://www.alphaxiv.org/abs/2504.16316). Published 2025-04-22 by University of New Brunswick, Canadian Institute for Cybersecurity · 2 votes · 44 views: Control Flow Graphs (CFGs) are critical for analyzing program execution and characterizing malware behavior. With the growing adoption of Graph Neural Networks (GNNs), CFG-based representations have p...
10. [ID=2603.22384] **Learning When to Act: Interval-Aware Reinforcement Learning with Predictive Temporal Structure** (https://www.alphaxiv.org/abs/2603.22384). Published 2026-03-23 · 2 votes · 10 views: Autonomous agents operating in continuous environments must decide not only what to do, but when to act. We introduce a lightweight adaptive temporal control system that learns the optimal interval be...
11. [ID=1805.09112] **Hyperbolic Neural Networks** (https://www.alphaxiv.org/abs/1805.09112). Published 2018-05-23 by ETH Zürich · 17 votes · 442 views: Hyperbolic spaces have recently gained momentum in the context of machine learning due to their high capacity and tree-likeliness properties. However, the representational power of hyperbolic geometry...