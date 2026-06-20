---
name: pro-se-patent-workbench
description: Use when preparing a self-filed U.S. patent application, especially SCBE-AETHERMOORE non-provisional utility work. Builds official-source registries, prior-art logs, claim support matrices, filing readiness checklists, and attorney-free procedural packets while clearly avoiding legal-advice claims.
---

# Pro Se Patent Workbench

Use this skill when the user is preparing a patent filing themselves and wants
book-pipeline discipline: source gathering, draft stages, spelling cleanup,
claim support, prior-art logs, and filing readiness.

This skill does not provide legal advice and does not impersonate a lawyer. It
helps a pro se applicant organize evidence, drafts, official references, and
checklists.

## Core Rules

- Use official USPTO sources first for current filing requirements and fees.
- Keep claims, specification, drawings, ADS/oath/micro-entity forms, and prior
  art as separate workstreams.
- For every claim element, attach a support citation from the specification,
  figures, or implemented code.
- Flag priority-risk items: supported by provisional, likely continuation,
  likely CIP/new matter, or product-only.
- Avoid legal conclusions such as "patentable" or "valid"; use "support found,"
  "support missing," or "needs review."
- Preserve micro-entity cost discipline unless the user explicitly chooses extra
  claims or surcharges.

## Default SCBE Commands

From the repo root:

```powershell
npm run patent:workbench
npm run patent:status
npm run patent:support-scan
node bin/scbe-patent.cjs prior-art-plan
```

The workbench writes to:

```text
docs/legal/patent-workbench/
```

## Workflow

1. Evidence freeze:
   - export the filed provisional and receipt from Patent Center;
   - record filing date, application number, title, inventor;
   - record repo commit hashes for code support.

2. Official-source registry:
   - run `scbe-patent sources`;
   - verify USPTO utility guide, Patent Center, DOCX guidance, forms, fee
     schedule, Patent Public Search, and Inventors Assistance Center links.

3. Claim support:
   - run `scbe-patent support-scan`;
   - inspect the generated claim support scan;
   - add manual citations where the script only finds weak keyword evidence.

4. Prior-art research:
   - run `scbe-patent prior-art-plan`;
   - search USPTO Patent Public Search first;
   - then search Google Patents, Lens, Semantic Scholar, and arXiv;
   - save query, result title, publication/patent number, URL, relevance, and
     how SCBE differs.

5. Draft packet:
   - keep independent claims to 3 and total claims to 20 by default;
   - write specification in neutral technical language;
   - keep coined SCBE terms in definitions/examples, not as claim dependencies.

6. Readiness:
   - run `scbe-patent readiness`;
   - mark each item with evidence;
   - re-check USPTO fees and DOCX validation on the filing day.

## SCBE Claim Families

Start with these families unless the user changes strategy:

- hyperbolic governance gate;
- harmonic cost scaling;
- semantic/tongue weighting;
- runtime gate and audit receipt;
- quarantine containment;
- bijective tamper and identifier canonicality.

## Language Guardrails

Prefer:

- "computer-implemented method";
- "one or more processors";
- "non-transitory computer-readable medium";
- "semantic weighting axes";
- "nonlinear governance cost";
- "quarantine containment state";
- "audit receipt";
- "under configured thresholds."

Avoid or qualify:

- "unhackable";
- "impossible";
- "military-grade";
- "guarantees safety";
- "proves alignment";
- "passed the bar";
- "lawyer-equivalent."

## Output Contract

End each patent-workbench turn with:

- files created/updated;
- commands run;
- what is verified;
- what still needs manual research;
- whether anything is legal-procedural uncertainty rather than code uncertainty.
