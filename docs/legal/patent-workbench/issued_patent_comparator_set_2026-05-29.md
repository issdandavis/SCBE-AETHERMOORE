# Issued Patent Comparator Set for SCBE Prosecution

Status: internal research memo, not legal advice.

Purpose: identify issued patents that survived examination in nearby software/AI/security lanes and extract lessons for SCBE-2026-0001. These do not prove SCBE is allowable, but they show claim styles and practical-application framing that have passed in related areas.

## Comparator 1 - US12340000B2

Title: Prompt injection detection for large language models  
Assignee: Intuit Inc.  
Issued: 2025-06-24  
Link: https://patents.google.com/patent/US12340000B2/en

### Why it matters

This is a direct LLM prompt-injection comparator. Its issued claim 1 is not framed as "safe AI" in the abstract. It recites a server receiving a user query, creating an LLM query, inserting a prohibited request, testing an LLM response, setting a prompt-injection signal, and then generating the user response.

### Lesson for SCBE

The allowed posture is concrete request processing plus a machine decision signal. For SCBE, the matching frame is:

- receive proposed computational action;
- encode/score it;
- compare against persisted state;
- set governance signals;
- route execution.

Avoid broad "alignment" language. Use "signal," "routing," "deny," "block," "review," and "execution decision."

## Comparator 2 - US12229265B1

Title: Generative AI model protection using sidecars  
Assignee: HiddenLayer Inc.  
Issued: 2025-02-18  
Link: https://patents.google.com/patent/US12229265B1/en

### Why it matters

This issued patent protects a GenAI sidecar/proxy architecture. Claim 1 recites receiving a prompt, redirecting it before ingestion by a first GenAI model, inputting it into a second GenAI model, checking guardrail output, initiating remediation if guardrails trigger, and otherwise passing the prompt to the first model.

### Lesson for SCBE

This supports the idea that AI guardrail systems can survive examination when claimed as an execution architecture. SCBE should distinguish itself from this by emphasizing that its guard is not merely a second model sidecar. SCBE's differentiator is geometric runtime governance with persisted centroid/drift state and deterministic tamper/audit mechanisms.

## Comparator 3 - US12118471B2

Title: Mitigation for prompt injection in A.I. models capable of accepting text input  
Issued: 2024-10-15  
Link: https://patents.google.com/patent/US12118471/en

### Why it matters

This issued patent claims trusted/untrusted token tagging for AI prompt-injection mitigation. Claim 1 recites an AI model accepting token sequences, a processor tagging trusted and untrusted instructions, token-vector tags, incompatible token sets, and modifying instructions so untrusted instructions are disregarded or removed.

### Lesson for SCBE

This is the closest tokenizer/security comparator. It shows that token-origin or trust tagging can pass if tied to a processor modifying model input behavior. SCBE should distinguish claim 26/28 by focusing on disjoint serialized semantic-axis vocabularies and bijective token mapping, not merely trusted/untrusted tagging.

## Comparator 4 - US11297078B2

Title: Cybersecurity detection and mitigation system using machine learning and advanced data correlation  
Assignee: PayPal Inc.  
Issued: 2022-04-05  
Link: https://patents.google.com/patent/US11297078B2/en

### Why it matters

This is a strong cybersecurity mitigation comparator. It recites access attempts, user behavior models, system access models, anomaly identification, and mitigation actions. It was classified around network security, anomaly detection, user behavior, machine learning, and access control.

### Lesson for SCBE

SCBE's Claim 1/9 story should be compared to this style: not just detecting anomalies, but applying a model to a specific access/action attempt and implementing mitigation. SCBE's novelty argument should be that its model is not only user/system access profiling; it uses bounded hyperbolic request state, session centroid drift, nonlinear cost, and execution routing.

## Comparator 5 - US11399037B2

Title: Anomaly behavior detection in interactive networks  
Issued: 2022-07-19  
Link: https://patents.google.com/patent/US11399037B2/en

### Why it matters

This issued patent uses graph/embedding-style anomaly detection in interactive networks. It shows that embedding-based anomaly detection can pass when claimed as a concrete model and system pipeline.

### Lesson for SCBE

This is useful against the "embeddings are abstract" fear, but it is also likely prior-art-adjacent. SCBE should distinguish itself by execution control: the hyperbolic distance does not merely detect anomalous graph behavior; it gates proposed computational actions through allow/review/quarantine/reroute/deny.

## Comparator 6 - US11093816B2

Title: Convolutional neural network (CNN)-based anomaly detection  
Issued: 2021-08-17  
Link: https://patents.google.com/patent/US11093816

### Why it matters

This issued patent claims anomaly detection using multiple similarity calculators and CNN processing. It shows that multi-feature anomaly input generation and machine-learning detection can be allowed when the processing structure is concrete.

### Lesson for SCBE

This supports the multi-axis signal story, but SCBE should not sound like generic multi-feature ML anomaly detection. SCBE's stronger distinction is that six semantic axes and token vocabularies feed a runtime governance gate, not just a classifier.

## Comparator 7 - US12413977B2

Title: Access controlling network architectures utilizing cellular signaled access control and machine-learning techniques to identify when automated programmable entities mimic humans  
Issued: 2025-09-09  
Link: https://patents.google.com/patent/US12413977B2/en

### Why it matters

This is an issued access-control / ML / bot-detection family. It shows that access-control architecture claims using ML signals around automated entities can pass.

### Lesson for SCBE

This is useful for the agentic/fleet side, but SCBE should avoid overclaiming "bot detection." The stronger SCBE lane is governance of proposed computational actions by geometric drift and persistent runtime state.

## What These Comparators Teach

Issued patents in this area tend to survive when they claim:

1. a concrete computer architecture;
2. a specific request/action/prompt path;
3. a computed signal from a model or rule process;
4. a machine behavior change based on that signal;
5. enough implementation detail that the claim is not just a result.

That aligns with SCBE's strongest framing:

> proposed computational action -> encoded vector/state -> bounded hyperbolic domain -> persisted centroid/reference comparison -> nonlinear governance signal -> allow/review/quarantine/reroute/deny -> audit/tamper/receipt output.

## What These Comparators Do Not Prove

They do not prove SCBE will be allowed. They may also become prior-art references an examiner could cite for parts of the claim. Their value is comparison:

- AI prompt-injection patents have issued.
- AI sidecar/guardrail patents have issued.
- ML cybersecurity mitigation patents have issued.
- Embedding/anomaly patents have issued.
- Token trust/tagging patents have issued.

SCBE should be positioned as a different ordered combination, not as a generic member of those categories.

## Practical Use In A Future Office Action Response

If rejected under 101:

- use these as examples of examiner-accepted practical AI/security architectures, while arguing from MPEP 2106 practical application.

If rejected under 103:

- use them to build a distinction chart:
  - prior art teaches guardrail sidecars;
  - prior art teaches prompt-injection signals;
  - prior art teaches ML access anomaly mitigation;
  - prior art teaches embedding anomaly detection;
  - but none teaches the SCBE ordered combination of bounded hyperbolic drift, session centroid, nonlinear cost, and execution routing.

If rejected under 112:

- use these as claim-style examples: replace coined terms with processor actions, signal generation, model inputs, state updates, and remediation actions.
