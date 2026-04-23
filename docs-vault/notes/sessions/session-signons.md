# Session Sign-Ons

- Generated UTC: 2026-03-04T02:08:01Z
- Rule: every AI signs on once per session with callsign + UTC timestamp.
- Rule: when work is validated, mark that session as `verified`.
- Compaction: only latest verified/retired sessions are shown here; full ledger stays in `artifacts/agent_comm/session_signons.jsonl`.

| timestamp_utc | agent | callsign | session_id | status | summary |
|---|---|---|---|---|---|
| 2026-03-04T02:08:01Z | Codex | Helix Warden | 20260304020647-codex-helix-warden | active | Session sign-on protocol enabled for all agents. Use per-session timestamped sign-ons; verified work compacts older entries forward. |

