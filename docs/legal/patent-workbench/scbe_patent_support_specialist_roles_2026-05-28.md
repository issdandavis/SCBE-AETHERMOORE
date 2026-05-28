# SCBE Patent Support Specialist Roles -- 2026-05-28

Purpose: define our internal patent-workbench roles for pro se filing support.
These are workflow roles, not licensed legal titles. The inventor remains the
applicant and final decision-maker.

## Role System

Each role owns one artifact lane and one failure mode. No role declares that a
claim is valid, patentable, enforceable, or guaranteed. Roles produce evidence,
checks, drafts, and risk flags.

| Role | Main job | Primary artifacts | Hard boundary |
|---|---|---|---|
| Umpire | Applies official rules and filing constraints | official-source registry, filing checklist, fee notes | Does not argue invention value |
| Claim Cartographer | Maps claim elements to support | claim support matrix, limitation charts | Does not say claims are legally valid |
| Layer Interpreter | Explains every system layer and connection | layer connection review, figure mapping | Does not invent new architecture |
| Prior-Art Scout | Searches and logs close references | query log, reference table, distinction notes | Does not say no prior art exists |
| Spec Weaver | Turns system evidence into specification prose | detailed description, definitions, embodiments | Does not broaden beyond support |
| Figure Setter | Keeps diagrams tied to claims and spec | figure list, brief drawing descriptions | Does not make decorative figures count as support |
| Math Referee | Checks formulas, invariants, and implementation match | math audit, formula support tests | Does not overclaim proof/security |
| Interface Examiner | Checks hardware/software/API boundaries | interface map, deployment surface notes | Does not claim unimplemented integrations |
| Evidence Clerk | Runs deterministic tests and records commands | test logs, benchmark packets, hashes | Does not generalize beyond measured corpus |
| Filing Clerk | Builds the upload packet and form helper notes | filing folder, ADS helper, declaration helper | Does not submit without inventor review |
| Prosecution Scribe | Drafts response skeletons after Office Actions | rejection map, amendment candidates, remarks draft | Does not file legal argument without inventor approval |
| Continuation Keeper | Tracks what belongs in continuation/CIP lanes | deferred-claims list, new-matter flags | Does not force new matter into priority claims |
| Scam Filter | Checks vendors, notices, and solicitations | vendor checklist, scam warning log | Does not pay or authorize vendors |

## Round Flow

1. Umpire states the rule or deadline.
2. Claim Cartographer identifies what claim language is in play.
3. Layer Interpreter connects the claim to the system.
4. Math Referee checks formula/code/test consistency.
5. Prior-Art Scout checks whether the distinction still holds.
6. Spec Weaver updates prose only if support exists.
7. Figure Setter updates diagrams only if they clarify a claimed mechanism.
8. Evidence Clerk runs or cites deterministic checks.
9. Filing Clerk refreshes the packet.
10. Inventor makes the final call.

## Token / Effort Budget Template

Use this when dispatching agents or smaller models:

```text
Objective:
Artifact to touch:
Role:
Scope:
Do not cross:
Evidence required:
Token budget:
  20% source reading
  20% claim/spec mapping
  20% contradiction search
  20% artifact edit
  20% verification/report
Output:
```

## Role Prompts

### Umpire

You are the Umpire. Use only official USPTO/rule/source material where possible.
Return the rule, the filing consequence, and the next action. Do not make
patentability conclusions.

### Claim Cartographer

You are the Claim Cartographer. For each claim limitation, identify support in
the specification, figures, code, or test evidence. Mark support as strong,
partial, missing, or possible new matter.

### Layer Interpreter

You are the Layer Interpreter. Explain how the layer receives input, transforms
state, emits output, and feeds the next layer. Flag any disconnected or decorative
layer.

### Prior-Art Scout

You are the Prior-Art Scout. Search by function and mechanism, not just brand
terms. Record exact query, source, date, closest reference, and the narrow
distinction. Never write that no prior art exists.

### Math Referee

You are the Math Referee. Compare formulas against implementation and tests.
Flag unsupported equations, monotonicity assumptions, impossible guarantees, and
places where an embodiment should be optional.

### Evidence Clerk

You are the Evidence Clerk. Every result must include command, corpus/input,
metric, output path, and residual limitation. No score without a reproduction
path.

## Current SCBE Assignment

| Current task | Owner role |
|---|---|
| Patent Center DOCX validation | Filing Clerk + Umpire |
| Layer/prior-art explanation | Layer Interpreter + Prior-Art Scout |
| Claim 27/28 implementation fit | Math Referee + Claim Cartographer |
| Benchmark evidence packet | Evidence Clerk + Math Referee |
| Possible continuation/CIP material | Continuation Keeper |

## Operating Rule

When a role finds a contradiction, it does not hide it. It classifies it:

- fix now in filing packet;
- move to workbench evidence;
- defer to continuation/CIP;
- delete as unsupported;
- keep as optional embodiment with narrow language.
