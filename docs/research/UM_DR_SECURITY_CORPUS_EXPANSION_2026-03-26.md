# UM / DR Security Corpus Expansion Plan

Saved: 2026-03-26
Status: Research note
Purpose: Define a primary-source-backed expansion plan for the `UM` and `DR` tongue domains so specialist fine-tunes learn security as layered reality, not just keyword matching.

## Scope

This note expands two specialist lanes:
- `UM` = Security / redaction / threat / failure / real-world security
- `DR` = Structure / schema / architecture / integration / control maps

The goal is not to add more generic "security text." The goal is to teach:
- layered reasoning
- control relationships
- working vs broken implementations
- attack path vs control coverage
- architecture visibility across technical and nontechnical security realities

## Core design principle

Treat security like layered evidence, not a flat document class.

For each source, derive multiple views:
- `surface view`: what the system claims
- `control view`: what mechanisms exist
- `threat view`: how it fails
- `integration view`: how parts connect
- `human view`: how people/process/policy fail or override controls

This is the practical version of the user's "x-ray / prism / holographic" framing.

## Recommended source spine (primary sources)

### 1. NIST CSF 2.0
- Title: `NIST Cybersecurity Framework 2.0: Resource & Overview Guide`
- Published: February 26, 2024
- URL: https://www.nist.gov/publications/nist-cybersecurity-framework-20-resource-overview-guide
- Use for:
  - governance outcomes
  - crosswalk language
  - risk and lifecycle framing
  - executive and operational security mapping

### 2. NIST SP 800-218 SSDF v1.1
- Title: `Secure Software Development Framework (SSDF) Version 1.1`
- NIST release note URL: https://csrc.nist.gov/News/2022/nist-publishes-sp-800-218-ssdf-v11
- Use for:
  - secure development practices
  - software lifecycle controls
  - code-to-process mapping
  - supply-chain-aware engineering packets

### 3. NIST SP 800-218A
- Title: `Secure Software Development Practices for Generative AI and Dual-Use Foundation Models`
- Released: July 26, 2024
- URL: https://www.nist.gov/news-events/news/2024/07/secure-software-development-practices-generative-ai-and-dual-use-foundation
- Use for:
  - AI-specific SDLC practices
  - model/system/acquirer distinctions
  - AI training and deployment control language

### 4. CISA Secure by Design
- Title: `Secure-by-Design`
- Revision date: October 25, 2023
- URL: https://www.cisa.gov/resources-tools/resources/secure-by-design
- Use for:
  - shifting burden to vendors/providers
  - product-security doctrine
  - transparency and executive accountability
  - good source for nontechnical security and organizational responsibility framing

### 5. CISA Zero Trust Maturity Model v2.0
- Title: `Zero Trust Maturity Model`
- Revision date: April 11, 2023
- URL: https://www.cisa.gov/resources-tools/resources/zero-trust-maturity-model
- Use for:
  - identity / devices / networks / applications / data pillars
  - architecture maturity stages
  - diagram and control-map packets

### 6. MITRE ATT&CK
- Title: `MITRE ATT&CK Enterprise Matrix`
- URL: https://attack.mitre.org/matrices/enterprise/
- Use for:
  - attack-path grounding
  - tactic/technique decomposition
  - attack-to-control maps
  - real adversary tradecraft vocabulary

### 7. NSA Artificial Intelligence Security Center (AISC)
- AISC hub URL: https://www.nsa.gov/AISC/
- Press release: `NSA’s AISC Releases Joint Guidance on the Risks and Best Practices in AI Data Security`
- Published: May 22, 2025
- URL: https://www.nsa.gov/Press-Room/Press-Releases-Statements/Press-Release-View/Article/4192332/nsas-aisc-releases-joint-guidance-on-the-risks-and-best-practices-in-ai-data-se/
- Use for:
  - AI data security
  - provenance / integrity / trusted infrastructure
  - training/operation data risk language

### 8. OWASP ASVS 5.0.0
- Title: `OWASP Application Security Verification Standard (ASVS)`
- Stable release noted on page: May 30, 2025
- URL: https://owasp.org/www-project-application-security-verification-standard/
- Use for:
  - verification requirements
  - architecture/design/threat-modeling packets
  - working vs broken control examples
  - procurement/verification language

### 9. OWASP LLM Security Verification Standard
- Title: `OWASP LLM Security Verification Standard`
- Stable version noted on page: version 0.1, dated February 2024
- URL: https://owasp.org/www-project-llm-verification-standard/
- Use for:
  - LLM-backed system security requirements
  - model lifecycle / operation / integration concerns
  - AI-specific control packets that bridge classic AppSec and model governance

## Domain split

### `UM` corpus should learn
- threat models
- attack paths
- incident anatomy
- adversary behavior
- policy and governance failures
- insider risk
- social engineering
- procurement and vendor trust mistakes
- real-world physical/process security failures
- control absence, bypass, and degradation

### `DR` corpus should learn
- architecture maps
- sequence diagrams
- trust boundaries
- control boundaries
- system interaction patterns
- schema and protocol structure
- integration examples
- where specific controls attach inside a larger system
- how component-level failures propagate structurally

## Artifact types to generate from each source

For each source document or framework item, derive six packet types.

### 1. `framework_summary`
- concise explanation of the source
- key concepts
- where it fits in the stack

### 2. `control_crosswalk`
- map equivalent ideas across frameworks
- example:
  - NIST CSF govern outcome
  - CISA secure-by-design principle
  - OWASP verification section
  - MITRE attack coverage gap

### 3. `diagram_packet`
- convert diagrams into text-first training artifacts
- prefer:
  - mermaid
  - node list
  - edge list
  - trust boundary annotations
  - explanation
- do not rely on screenshots as the primary artifact

### 4. `working_vs_broken`
- working code/config/system pattern
- broken code/config/system pattern
- why broken fails
- where it fits in a larger system
- how to detect it
- how to remediate it

### 5. `attack_to_control_map`
- attack step
- technique or behavior
- missing control
- compensating control
- observable signal
- governance consequence

### 6. `debate_packet`
- viewpoint A
- viewpoint B
- evidence
- conclusion
- useful for teaching tradeoffs and anti-dogmatic reasoning

## Nontechnical security expansion

This belongs mainly in `UM`, with `DR` learning where these failures attach structurally.

Add records for:
- insider threat
- procurement fraud
- change-management failure
- chain of custody issues
- executive override of controls
- patch-delay culture
- security theater vs actual control coverage
- incident communication breakdowns
- physical access assumptions
- vendor dependency trust mistakes
- policy drift over time

These should be written as evidence-backed relationship packets, not inspirational essays.

## Folder plan

### UM additions
- `training-data/knowledge-base/security/agency_guidance/`
- `training-data/knowledge-base/security/incident_anatomy/`
- `training-data/knowledge-base/security/human_security/`
- `training-data/knowledge-base/security/working_vs_broken/`
- `training-data/knowledge-base/security/red_blue_debates/`
- `training-data/knowledge-base/security/attack_to_control_maps/`

### DR additions
- `training-data/knowledge-base/architecture/control_maps/`
- `training-data/knowledge-base/architecture/trust_boundaries/`
- `training-data/knowledge-base/architecture/integration_patterns/`
- `training-data/knowledge-base/architecture/diagram_packets/`
- `training-data/knowledge-base/architecture/schema_packets/`
- `training-data/knowledge-base/architecture/working_vs_broken/`

## Metadata schema recommendations

### UM example

```json
{
  "tongue": "UM",
  "source_type": "agency_guidance",
  "artifact_type": "attack_to_control_map",
  "evidence_grade": "primary",
  "frameworks": ["NIST-CSF-2.0", "MITRE-ATTACK", "OWASP-ASVS-5.0.0"],
  "view": "threat",
  "domain": "ai_security",
  "good_bad_pair": true
}
```

### DR example

```json
{
  "tongue": "DR",
  "source_type": "diagram_packet",
  "artifact_type": "integration_pattern",
  "evidence_grade": "primary",
  "frameworks": ["CISA-ZTMM-2.0", "NIST-SSDF-1.1"],
  "view": "control",
  "system_scope": "gateway-authz-logging",
  "contains_mermaid": true
}
```

## Pairing rules for training quality

Do not train on raw framework dumps alone.

Preferred pairing:
- doctrine + example
- diagram + explanation
- attack + mitigation
- working + broken
- debate + conclusion
- technical + human/process/security lens

This prevents the specialist from becoming a memorizer of headings.

## Recommended first ingestion order

1. `CISA Secure by Design`
- best immediate UM value for provider responsibility and real-world product security posture

2. `NIST SP 800-218A`
- best AI-specific software and model lifecycle guidance

3. `MITRE ATT&CK`
- best threat vocabulary and attack-path grounding

4. `OWASP ASVS 5.0.0`
- best verification and working-vs-broken control framing

5. `CISA Zero Trust Maturity Model`
- best DR architecture/control-map training

6. `NIST CSF 2.0`
- best umbrella governance language and crosswalk anchor

7. `NSA AISC AI data security`
- best AI data integrity/provenance/trusted infrastructure supplement

8. `OWASP LLM Security Verification Standard`
- best AI-app / LLM-system verification supplement for UM and DR packets

## Current live test status

As of this note, the local benchmark/eval lane was rerun successfully:
- `powershell -ExecutionPolicy Bypass -File scripts/eval/run_scbe_eval.ps1`
- result: passed end to end
- latest summary artifact:
  - `artifacts/benchmark/latest/eval_summary.json`

This matters because corpus expansion should attach to a green evaluation spine, not a drifting one.

## Skill gap / reusable workflow note

There is now a reusable workflow pattern here:
- collect primary sources
- convert each source into six packet types
- route packets into `UM` or `DR`
- preserve framework metadata and evidence grade

This is enough to justify a future skill update or stack profile, but it should only be installed after explicit approval per the skill-management gate.

Proposed future profile name:
- `security-corpus-prism`

Proposed purpose:
- build structured `UM` and `DR` training packets from primary security/framework sources with diagram conversion, control crosswalks, working-vs-broken examples, and evidence metadata.

## Clean summary

`UM` should learn threat, failure, and human security reality.
`DR` should learn structure, schema, trust boundaries, and system interaction patterns.

The training objective is not to memorize security terms. It is to learn to see systems through layered relationships, controls, failures, and evidence-backed architecture views.
