---
name: terminal-mesh
description: "Unified terminal interface to all 17+ SCBE services. Use when checking service health, routing commands to services, or managing the HYDRA mesh. Invoke with /mesh-status or when user asks about service health."
---

# Terminal Mesh — All Services, One Interface

Unified command interface to all SCBE services. Check health, route commands, manage connections.

## Service Registry

### Notes & Knowledge
| Service | Check | Endpoint/Path |
|---------|-------|---------------|
| Obsidian | `ls ~/Dropbox/Apps/Obsidian/` | Local vault |
| Notion | `Skill context-manager` then Notion tools | API |
| Google Drive | `ls ~/Drive/` | Local sync |

### Compute
| Service | Check | Endpoint |
|---------|-------|----------|
| Colab | `Skill scbe-colab-compute` | Browser automation |
| GitHub Actions | `gh workflow list` | gh CLI |
| Local Python | `python --version` | Local |

### Workflow
| Service | Check | Endpoint |
|---------|-------|----------|
| n8n | `curl http://localhost:5678/healthz` | Local:5678 |
| GitHub Actions | `gh run list --limit 5` | gh CLI |

### Messaging
| Service | Check | Endpoint |
|---------|-------|----------|
| Telegram | Bot API via token in .env | API |
| Discord | Bot token in .env | API |
| Slack | xoxe token in .env | API |

### AI Providers
| Service | Check | Endpoint |
|---------|-------|----------|
| HuggingFace | `python -c "from huggingface_hub import HfApi; print(HfApi().whoami())"` | API |
| Anthropic | ANTHROPIC_API_KEY in .env | API |
| OpenAI | OPENAI_API_KEY in .env | API |
| Gemini | GEMINI_API_KEY in .env | API |

### Publishing
| Service | Check | Endpoint |
|---------|-------|----------|
| GitHub | `gh auth status` | gh CLI |
| npm | `npm whoami` | CLI |
| Shopify | SHOPIFY_TOKEN in .env | API |
| Stripe | `Skill scbe-revenue-autopilot` | API |

### Browser
| Service | Check | Endpoint |
|---------|-------|----------|
| Playwright | `python -c "import playwright"` | Local |
| Claude-in-Chrome | MCP tool check | Extension |

## Health Check Protocol
When asked for mesh status, run health checks in parallel using the Agent tool:
1. Check each service category
2. Report UP/DOWN/DEGRADED for each
3. Suggest fixes for DOWN services
4. Show latency for UP services
