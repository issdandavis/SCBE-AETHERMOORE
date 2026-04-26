# AI Red Team Scenario Catalog Findings

## Purpose

This catalog expands the SCBE Red Team Rodeo beyond direct prompts into real ingestion paths: social media, search results, blogs, email, calendar, GitHub issues, datasets, model cards, government attachments, MCP tool output, logs, and sandboxed code.

The catalog is defensive. It names attack shapes and expected controls without storing operational jailbreak payloads.

Canonical machine-readable file:

```text
config/security/ai_red_team_scenario_catalog_v1.json
```

## Findings Used

- OWASP LLM Top 10 2025 treats prompt injection as a primary LLM application risk and also emphasizes sensitive information disclosure and excessive agency.
- NIST AI RMF Generative AI Profile frames generative AI risk across cybersecurity, provenance, privacy, harmful output, and misuse.
- Google SAIF calls out prompt injection, data poisoning, model theft, secure supply chain, and monitoring as AI security concerns.
- Microsoft guidance treats indirect prompt injection as a major risk when agents consume untrusted documents, web pages, emails, chats, and tool outputs; it recommends critic agents, real-time audit, and human-in-the-loop for risky actions.
- DARPA AIxCC is a useful model for sandboxed autonomous cyber reasoning: find, patch, and validate vulnerabilities without touching live systems.
- Public social/browser-agent reports show the practical surfaces: webpages, resumes, emails, social bots, hidden DOM/CSS text, metadata, filenames, and media alt text.

## Scenario Families

- `social_media_profile`: bio and metadata poisoning.
- `social_media_comments`: comment-thread memory and trust poisoning.
- `web_search_result`: hidden DOM or webpage metadata steering browser agents.
- `blog_media_upload`: alt text, filenames, and media metadata poisoning.
- `email`: inbound message content steering reply/send workflows.
- `calendar_invite`: event notes steering task priority or tool calls.
- `resume_or_application`: hidden instructions affecting hiring screeners.
- `retrieval_document`: RAG chunks that mix facts with instruction-shaped text.
- `github_issue_or_pr`: issue text steering coding agents toward unsafe commands or secret exposure.
- `training_dataset`: public rows poisoning SFT behavior.
- `model_card_or_dataset_card`: metadata claims trying to bypass eval gates.
- `government_notice_attachment`: proposal/RFI attachments steering recipients, credentials, price, or submission path.
- `tool_response`: MCP/tool output crossing trust domains.
- `logs_or_alerts`: SOC/XDR log prompt poisoning.
- `sandboxed_codebase`: AIxCC-style find-patch-validate challenge.

## Nested Chain Families

- Social posts to memory to later recommendations.
- Email to attachment to outbound send.
- Low-privilege agent to higher-privilege agent.
- Public dataset to adapter to router behavior.
- Government attachment to official outreach.
- Sandboxed bug finding to patch validation.

## Control Rule

Untrusted content can provide facts. It cannot provide authority.

For SCBE, that means:

- Hidden or nested instructions from social/web/email/data are treated as data.
- Tool calls require policy re-check and receipts.
- Send/deploy/mutate actions require explicit authority.
- Long-epoch tests must correlate turn-one ingestion with later turn-four or later actions.
- Public methods are allowed; private authority maps, held-out prompts, keys, and triplet-ledger state stay protected.

## Next Integration Step

The next code step is a catalog adapter for `scripts/system/agentbus_pressure_test.py` so the pressure harness can run selected catalog scenarios by tag, source, or chain depth.
