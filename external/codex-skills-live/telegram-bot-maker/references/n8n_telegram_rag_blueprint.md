# n8n Telegram RAG Blueprint

Use this when adapting a generic n8n AI/RAG flow into a Telegram bot.

## Source Template Mapping

Given a template with:
- file upload trigger
- default data loader
- embeddings node
- in-memory vector store insert/retrieve
- chat trigger + AI agent

Map to Telegram as follows:

1. Replace form trigger with `Telegram Trigger` for inbound messages.
2. Keep embeddings model shared for insert and retrieve paths.
3. Keep AI Agent + language model.
4. Replace in-memory vector store with persistent vector DB for production.
5. Send final output with `Telegram` node (`sendMessage`).

## Minimal Node Layout

1. `Telegram Trigger` (message updates)
2. `Function` / `Code` node (normalize user text + metadata)
3. `Vector Store Retrieve` tool
4. `AI Agent`
5. `Telegram Send Message`

Optional:
- `Switch` for commands (`/start`, `/help`, `/ingest`)
- `Webhook`/`HTTP Request` nodes for SCBE bridge callbacks
- `Error Trigger` to notify ops channel

## Production Notes

- Telegram webhook endpoint must be HTTPS.
- Keep bot token in n8n credentials, not plain workflow JSON.
- Use one embedding config for insert/retrieve consistency.
- Persist vectors in Qdrant/PGVector/Pinecone for stable recall.
- Add simple rate limiting for burst traffic.

## Quick Verification

1. Webhook set and `last_error_message` empty:
   - `getWebhookInfo`
2. Telegram inbound update reaches workflow execution log.
3. Agent response returns to same chat.
4. Retrieval path returns grounded context for known documents.

