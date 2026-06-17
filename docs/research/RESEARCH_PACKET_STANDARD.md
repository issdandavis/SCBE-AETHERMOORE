# AetherMoore Research Packet Standard

Status: operating standard for public research packets
Updated: 2026-06-17

This standard defines what "convert a note into research" means for AetherMoore.
It does not mean changing a Markdown file into a PDF. It means moving an idea
through structured source gathering, adversarial review, validation, and claim
boundary setting before publication.

## Packet Grades

| Grade | Meaning | Public Use |
| --- | --- | --- |
| Idea Seed | Raw concept, metaphor, or hypothesis. | Can be listed as a future lane, but not sold as evidence. |
| Research Brief | Sources collected, claim boundary written, initial critique performed. | Can be published as a scoped research note. |
| Research Packet | Multi-pass review completed, source ledger present, validation plan written. | Can be published as an arXiv-style packet. |
| Validation Packet | Independent checks, experiments, simulations, or replications attached. | Can support stronger technical statements. |
| Peer-Review Candidate | External review requested or received, revisions logged. | Can be submitted or shared for formal critique. |

## Ten-Pass Research Loop

Each promoted topic should pass through these roles. They may be run by different
AI systems, different prompts, or humans, but the packet must record the role and
what changed.

1. Framer: turns the raw idea into one falsifiable question.
2. Source scout: finds primary, official, or peer-reviewed sources.
3. Domain skeptic: lists reasons the idea may be wrong.
4. Systems engineer: maps components, interfaces, constraints, and failure modes.
5. Safety reviewer: identifies harm, misuse, welfare, and operational risks.
6. Measurement designer: defines what data would prove or disprove the claim.
7. Literature reconciler: resolves conflicting sources and unknowns.
8. Product translator: states what the work is useful for without overclaiming.
9. Red-team reviewer: attacks wording, causality, novelty, and missing citations.
10. Editor: produces the final abstract, claim boundary, source ledger, and PDF.

## Required Sections

Every research-grade packet needs:

- title,
- abstract,
- raw idea,
- research question,
- background,
- source ledger,
- mechanism or system model,
- validation plan,
- risks and failure modes,
- claim boundary,
- review ledger,
- open questions,
- publication status.

## Citation Rule

Use primary sources where possible: papers, official agency pages, standards,
datasets, documentation, patents, or books. Blog posts and AI-generated summaries
can be useful leads, but they are not enough for a research-grade packet.

## Legal Boundary

These packets do not make legal claims, legal advice, patentability opinions,
compliance certifications, or guarantees. They are technical research artifacts
with explicit uncertainty, source provenance, and validation status.
