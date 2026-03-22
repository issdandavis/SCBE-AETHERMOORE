# Evidence Schema

Use this row shape when building claim-to-code artifacts.

## Required Fields

- `claim_or_page`: human-readable page or claim label
- `notion_id`: canonical Notion page ID
- `source_url`: Notion page URL when available
- `priority_tier`: `tier1|tier2|tier3|tier4`
- `verification_state`: `implemented|tested|partial|unmapped`
- `repo_code_paths`: runtime code surfaces
- `repo_test_paths`: tests that back the claim
- `demo_or_api_paths`: demos, docs, or API entrypoints that expose the behavior
- `notes`: short explanation of what is proven vs missing

## State Rules

- `implemented`: a concrete repo surface exists
- `tested`: implementation exists and at least one relevant test path exists
- `partial`: page is relevant but repo proof is incomplete or indirect
- `unmapped`: no convincing repo path found yet

## Minimal Human Output

For each page, answer:

1. What does the page claim?
2. What repo surface best matches it?
3. What test or demo proves it?
4. What is still missing?
