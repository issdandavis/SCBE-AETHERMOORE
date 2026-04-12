# Cloudflare Doc Registry Agent Notes

This is a future-state note, not a required implementation.

If document management is later automated with Cloudflare Agents SDK, the clean shape is:

- one stateful agent that stores document records
- one workflow that promotes a topic from exploratory → operational → canonical
- one audit log for authority changes

Good agent responsibilities:

- store document class and owner path
- track “last verified against runtime” timestamps
- reject promotions when canonical/runtime sources were not checked first

Do not build this before the manual operating model is stable.
