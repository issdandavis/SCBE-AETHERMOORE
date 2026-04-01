# Small Business Helper AI

Status: product concept
Date: 2026-03-31
Scope: self-governing AI assistant for small businesses using lightweight SCBE kernel

## Problem

The AI agent market is $7.6B (2025) growing to $50B by 2030. Enterprise has
governance platforms (Copilot Studio, Vertex, etc). Small businesses (5-50 employees)
have nothing -- they can't afford compliance overhead, don't have AI expertise,
and can't hire someone to audit their AI's behavior.

## Value Proposition

"AI that audits itself so you don't have to hire someone to audit it."

A small business helper AI that carries its own lightweight governance kernel:
- The harmonic wall running locally (not cloud-dependent)
- The 9-state phase diagram making trust decisions automatically
- Polly personality for approachable interaction
- Sacred Tongue domain separation preventing cross-task confusion

## Target Use Cases

1. **Bookkeeping automation**: categorize expenses, flag anomalies, prep tax docs
   - Governance: DENY any action that modifies bank connections
   - Tongue profile: CA (Compute) + RU (Binding) dominant

2. **Customer communications**: draft replies, schedule followups, manage reviews
   - Governance: QUARANTINE anything that sounds adversarial or legal
   - Tongue profile: AV (Transport) + KO (Intent) dominant

3. **Inventory management**: track stock, predict reorders, flag discrepancies
   - Governance: ALLOW reads freely, QUARANTINE writes, DENY deletes
   - Tongue profile: CA (Compute) + DR (Structure) dominant

4. **Compliance checking**: review contracts, flag risky clauses, track deadlines
   - Governance: read-only mode, ESCALATE anything involving signatures
   - Tongue profile: RU (Binding) + AV (Social) dominant

## Architecture

```
Small Business Helper
├── Polly Chat Interface (friendly, sardonic, helpful)
├── Pump Kernel (lightweight -- packet.py + guards.py only)
│   ├── Tongue profiler (6D domain awareness)
│   ├── Null pattern (absence detection)
│   ├── Governance gate (ALLOW/QUARANTINE/ESCALATE/DENY)
│   └── CycleBudget (15-second compute cap)
├── Task Router (maps user request to business domain)
├── UndercoverFilter (strips internal state from output)
└── Audit Log (local JSONL, exportable for accountant/lawyer)
```

## Minimum Viable Product

Phase 1: Polly chatbot with pump orientation, no tool execution
Phase 2: Add read-only integrations (QuickBooks API, Google Workspace)
Phase 3: Add write integrations with QUARANTINE gate
Phase 4: Mobile app (PWA for Android, Expo wrapper for iOS)

## Revenue Model

- Free: Polly chat with pump orientation (no integrations)
- $29/mo: read-only integrations + audit log
- $79/mo: full integrations + compliance checking
- $199/mo: multi-user + custom tongue profiles per business domain

## Why SCBE Wins Here

Nobody else offers self-governing AI for small business because:
1. Enterprise governance platforms are too expensive ($500+/mo)
2. Open-source agents have no governance at all
3. The pump kernel is lightweight enough to run on a $5/mo VPS
4. The tongue profiler catches domain confusion without ML infrastructure
5. The audit log satisfies accountants without requiring security expertise
