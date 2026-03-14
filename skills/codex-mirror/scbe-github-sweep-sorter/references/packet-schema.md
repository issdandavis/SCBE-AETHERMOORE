# Sweep Packet Schema

Use one packet per sweep mission. Keep it small and grep-friendly.

```json
{
  "packet_id": "sweep-20260314-001",
  "created_at": "2026-03-14T22:00:00Z",
  "sender": "codex",
  "recipient": "claude",
  "repo": "SCBE-AETHERMOORE",
  "branch": "main",
  "task_id": "repo-hygiene-batch-a",
  "formation": "hexagonal-ring",
  "quorum_required": "4/6",
  "ordered_attestation": false,
  "summary": "Sort repo hygiene roots and assign cleanup lanes",
  "risk": "medium",
  "buckets": [
    "keep-in-repo",
    "archive-or-cloud",
    "ignore-or-cache"
  ],
  "work_packets": [
    {
      "tongue": "KO",
      "role": "architecture-curator",
      "goal": "Confirm the keep/archive boundaries",
      "allowed_paths": ["docs/", "schemas/"],
      "blocked_paths": ["src/", "tests/"],
      "done_criteria": [
        "Boundary doc updated",
        "No source paths reassigned incorrectly"
      ]
    }
  ],
  "next_action": "Route to AI-to-AI packet lane",
  "proof": [
    "artifacts/repo-hygiene/latest_report.json"
  ]
}
```

## Required Fields

- `packet_id`
- `created_at`
- `repo`
- `task_id`
- `formation`
- `quorum_required`
- `summary`
- `work_packets`

## Notes

- `work_packets` should define ownership, not just intent.
- Include file paths when possible.
- Keep secrets and raw tokens out of packets.
