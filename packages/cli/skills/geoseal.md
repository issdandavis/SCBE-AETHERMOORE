# GeoSeal Skill Card

summary: Compile, gate, execute, and explain commands through GeoSeal receipts.
triggers: geoseal, geo seal, governance, receipt, seal, gate, quarantine, deny, allow, pipeline

## Worksheet

- Separate intent text from executable command text before calling GeoSeal.
- Use compile/plan first when the command is ambiguous.
- Execute only after an ALLOW decision from the existing GeoSeal gate.
- Return the decision, receipt path, stdout/stderr summary, and rollback note.
