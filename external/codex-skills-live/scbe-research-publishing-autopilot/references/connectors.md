# Connectors and Approval Schemas

## connectors.json
```json
{
  "defaults": {
    "timeout_seconds": 20
  },
  "connectors": {
    "x": {
      "mode": "webhook",
      "endpoint_env": "SCBE_X_WEBHOOK_URL",
      "token_env": "SCBE_X_WEBHOOK_TOKEN",
      "method": "POST",
      "headers": {
        "X-SCBE-Channel": "x"
      }
    },
    "article": {
      "mode": "webhook",
      "endpoint_env": "SCBE_ARTICLE_WEBHOOK_URL",
      "token_env": "SCBE_ARTICLE_WEBHOOK_TOKEN",
      "method": "POST"
    },
    "default": {
      "mode": "stdout"
    }
  }
}
```

## approvals.json
```json
{
  "approvals": [
    {
      "post_id": "post-1",
      "channel": "x",
      "approved": true,
      "approved_by": "issac",
      "expires_at": "2026-03-01T00:00:00Z"
    }
  ]
}
```

## retrigger_rules.json
```json
{
  "rules": [
    {
      "name": "low_ctr_x",
      "channel": "x",
      "metric": "ctr",
      "operator": "lt",
      "threshold": 0.015,
      "cooldown_minutes": 60,
      "action": "rewrite_hook"
    }
  ]
}
```

## Security Notes
- Keep endpoint URLs and tokens in environment variables only.
- Keep `--allow-unapproved` off in production.
- Keep claim gate report passing before dispatch.
