# Environment Variable Map

Fill only what the imported workflow actually needs.

| Variable | Purpose | Required for first safe run |
| --- | --- | --- |
| `OPENAI_API_KEY` | model calls where present | maybe |
| `HF_TOKEN` | Hugging Face access where present | maybe |
| `GH_TOKEN` | GitHub operations where present | maybe |
| `NOTION_TOKEN` | Notion integration where present | maybe |
| `WEBHOOK_BASE_URL` | callback routing | maybe |

Practical rule:
- map one workflow at a time
- do not fill every secret just because a bundle exists
