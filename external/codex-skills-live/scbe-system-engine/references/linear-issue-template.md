# Linear Issue Template — SCBE KO Review Deny/Quarantine

title: "SCBE KO Compliance Review"
project: ISDanDavis2/scbe-aethermoore
labels:
  - scbe-compliance
  - ko-tongue
  - ai-review
assignee: ""

body:
- summary: "Automated KO-tongue reviewer blocked this change."
- details:
  - action: "{{decision_record.action}}"
  - signature: "{{decision_record.signature}}"
  - reason: "{{decision_record.reason}}"
  - timestamp: "{{decision_record.timestamp}}"
  - pr_diff_excerpt: "{{review_input.preview}}"
- next_steps:
  - "Fix dual-output contract if missing (`StateVector` + `DecisionRecord`)."
  - "Replace hard-coded constants with config/derivations."
  - "Re-run KO review and re-trigger PR webhook."

