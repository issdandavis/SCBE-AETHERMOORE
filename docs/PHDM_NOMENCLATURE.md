# 📘 PHDM Nomenclature Reference - Canonical Definitions

> last-synced: 2026-02-16T07:29:14.387Z

# PHDM Nomenclature Reference

Version: 1.0.0

Date: February 10, 2026

Status: Authoritative

Purpose: Single source of truth for PHDM naming conventions across the entire SCBE-AETHERMOORE codebase and documentation.

---

## Canonical Definition

<!-- Unsupported block type: callout -->
PHDM = Polyhedral Hamiltonian Defense Manifold

This is the only acceptable expansion for the PHDM acronym across all documentation, code comments, presentations, and patent filings.

### What It Actually Does

The implementation in src/harmonic/phdm.ts performs:

1. Polyhedral: Traverses 16 canonical polyhedra (5 Platonic, 3 Archimedean, 2 Kepler-Poinsot, 6 others)

2. Hamiltonian: Follows Hamiltonian paths through the polyhedral graph

3. Defense: Generates HMAC key chains from topological invariants for intrusion detection

4. Manifold: Monitors state deviations against a 6D geodesic spline in hyperbolic space

Geometry Model: Poincaré ball model (NOT half-plane)

---

## Retired Names (DO NOT USE)

### ❌ Poincare Half-plane Drift Monitor

Where it appeared: CLAUDE.md:74, CLAUDE.md:217, STRUCTURE.md:72

Why retired: Wrong geometry model—the implementation uses the Poincaré ball model, not the half-plane model. The geometry is polyhedral, not half-plane.

Status: REMOVE from all documentation

### ❌ Piecewise Hamiltonian Distance Metric

Where it appeared: SCBE_PATENT_PORTFOLIO.md:121

Why retired: This describes a sub-operation (distance calculation), not the full module. Too narrow in scope.

Status: REMOVE from all documentation

### ❌ Polynomial Hamiltonian Detection Module

Where it appeared: SCBE-AETHERMOORE-v3.0.0/tests/harmonic/phdm.test.ts:2 (legacy)

Why retired: Wrong word entirely—should be "Polyhedral" not "Polynomial"

Status: REMOVE from all legacy references

### ❌ Polyhedral Hamiltonian Dynamic Mesh

Where it appeared: python/scbe/brain.py:4, multiple Notion pages

Why retired: "Dynamic Mesh" describes the cognitive architecture specialization (brain tissue), not the core security function. This caused confusion between the security layer and the cognitive layer.

Status: Deprecated—use context-specific alias below instead

### ❌ Polyhedra-Based Geometric Defense Manifold

Where it appeared: Patent documentation

Why retired: Redundant phrasing—"Polyhedral" already means "based on polyhedra"

Status: REMOVE from patent docs

### ❌ Polyhedral Coherence Verification

Where it appeared: Layer descriptions

Why retired: Too vague—doesn't capture the Hamiltonian path structure

Status: REMOVE from layer documentation

### ❌ Polyhedral Hamiltonian Density Matrix

Where it appeared: Technical Appendix C

Why retired: "Density Matrix" is quantum mechanics terminology that doesn't apply here. Causes confusion with actual quantum computing concepts.

Status: REMOVE from technical appendices

---

## Context-Specific Aliases (ALLOWED)

When PHDM is used in specialized contexts, you may clarify the role with an alias, but always include the full canonical name first.

### ✅ PHDM Cognitive Lattice

Context: When discussing the brain architecture implementation in python/scbe/brain.py

Usage: "The PHDM (Polyhedral Hamiltonian Defense Manifold) serves as a cognitive lattice in the AetherBrain architecture..."

Purpose: Clarifies that PHDM is being used as the substrate for AI reasoning, not just security

### ✅ PHDM Brain Substrate

Context: AI cognitive architecture discussions

Usage: "The PHDM brain substrate organizes reasoning into 16 polyhedral nodes..."

Purpose: Emphasizes the cognitive function without changing the acronym

### ✅ PHDM Security Container

Context: When contrasting cognitive vs. security roles

Usage: "PHDM functions as both a cognitive lattice (internal reasoning) and a security container (boundary enforcement)..."

Purpose: Clarifies the dual-role nature

---

## Migration Guide

### Code Files to Update

<!-- Unsupported block type: table -->
<!-- Unsupported block type: table_row -->

<!-- Unsupported block type: table_row -->

<!-- Unsupported block type: table_row -->

<!-- Unsupported block type: table_row -->

<!-- Unsupported block type: table_row -->

<!-- Unsupported block type: table_row -->

<!-- Unsupported block type: table_row -->

### Notion Pages to Update

1. 🧠 PHDM as AI Brain Architecture - The Geometric Skull — Update all references to "Dynamic Mesh"

2. SCBE-AETHERMOORE + PHDM: Complete Mathematical & Security Specification — Update Chapter 6 title

3. Technical Appendix C: PHDM Consciousness Encoding — Remove "Density Matrix" terminology

4. Patent documentation pages — Standardize all PHDM references

---

## Standard Code Comment Template

Use this header for all PHDM-related files:

```typescript
/**
 * PHDM: Polyhedral Hamiltonian Defense Manifold
 * 
 * Traverses 16 canonical polyhedra in Hamiltonian paths to generate
 * HMAC key chains from topological invariants (Euler characteristic, genus)
 * and monitors state deviations against a 6D geodesic spline for intrusion detection.
 * 
 * Geometry: Poincaré ball model (hyperbolic space)
 * Security: Quantum-resistant cryptographic containment
 * 
 * @see https://notion.so/phdm-spec for full specification
 */
```

---

## FAQ

Q: Why not keep "Dynamic Mesh" since it's more descriptive for the brain architecture?

A: "Dynamic Mesh" describes how PHDM is used in one context (cognitive architecture), not what PHDM is. The module's primary function is defense/security. Use "PHDM Cognitive Lattice" as a clarifying phrase when needed.

Q: Can I use "PHDM" alone without expanding it?

A: Yes, but the first occurrence in any document should expand it as "PHDM (Polyhedral Hamiltonian Defense Manifold)" for clarity.

Q: What about presentations and marketing materials?

A: Always use the canonical expansion. If you need a simplified explanation, say: "PHDM creates a geometric cage that makes dangerous AI behaviors mathematically impossible."

---

## Related Documentation

- 🧠 PHDM as AI Brain Architecture - The Geometric Skull

- SCBE-AETHERMOORE + PHDM: Complete Mathematical & Security Specification

- 📐 Hamiltonian Braid Specification - Formal Mathematical Definition

---

Status: This document is the authoritative source for PHDM naming. Any conflicts between this page and other documentation should be resolved in favor of this specification.

Last Updated: February 10, 2026

Maintained By: Issac Davis
