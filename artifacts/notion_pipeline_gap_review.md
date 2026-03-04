# Notion Pipeline Gap Review
Generated: 2026-02-16T07:44:36.133847+00:00
Repo: C:\Users\issda\SCBE-AETHERMOORE-working
Total tasks: 3

## Priority Counts
- critical: 2
- high: 1

## Notion Coverage Tasks

- [CRITICAL] Increase 'technical_system_stream' training stream coverage (fine-tune-funnel, Fine-Tune Funnel)
  - Stream 'technical_system_stream' has 0/100 records from configured Notion/fine-tune sources.
  - action: Export missing notion categories using the requested sync query.
  - action: Tag records for the target stream so it reaches required minimum.

- [CRITICAL] Increase 'isekai_emotive_stream' training stream coverage (fine-tune-funnel, Fine-Tune Funnel)
  - Stream 'isekai_emotive_stream' has 0/80 records from configured Notion/fine-tune sources.
  - action: Export missing notion categories using the requested sync query.
  - action: Tag records for the target stream so it reaches required minimum.

- [HIGH] Rebuild training-data metadata file (code-assistant, Notion Export Pipeline)
  - No training-data/metadata.json was found from notion-to-dataset export.
  - action: Run notion_to_dataset.py and verify export step writes metadata.json.
