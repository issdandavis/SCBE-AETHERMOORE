# Terminal Ops Quickstart

Date: 2026-02-20  
Scope: Run web research, article/content ops, and product/store ops from terminal through SCBE connectors.

## Purpose

Use one CLI (`scripts/scbe_terminal_ops.py`) as your terminal control surface for:

1. Connector setup (`shopify`, `zapier`, `n8n`, and others)
2. Goal submission (`web_research`, `content_ops`, `store_ops`)
3. Step execution with high-risk approval gate

## Start API

```bash
uvicorn src.api.main:app --reload --port 8000
```

## CLI Help

```bash
python scripts/scbe_terminal_ops.py --api-key demo_key_12345 --help
```

## List connector templates

```bash
python scripts/scbe_terminal_ops.py --api-key demo_key_12345 templates
```

## Register Shopify connector

```bash
python scripts/scbe_terminal_ops.py --api-key demo_key_12345 connector add --name shopify-admin-read --kind shopify --shop-domain your-store.myshopify.com --auth-type header --auth-header-name X-Shopify-Access-Token --auth-token <SHOPIFY_ADMIN_TOKEN>
```

## Register Zapier connector

```bash
python scripts/scbe_terminal_ops.py --api-key demo_key_12345 connector add --name zapier-store-ops --kind zapier --endpoint-url https://hooks.zapier.com/hooks/catch/<id>/<slug>/
```

## Submit goals

Web research goal:

```bash
python scripts/scbe_terminal_ops.py --api-key demo_key_12345 goal create --goal "Research top 20 product opportunities and sources" --channel web_research --priority high --execution-mode connector --connector-id <CONNECTOR_ID>
```

Article/content submission goal:

```bash
python scripts/scbe_terminal_ops.py --api-key demo_key_12345 goal create --goal "Draft and submit weekly article batch" --channel content_ops --priority high --execution-mode connector --connector-id <CONNECTOR_ID>
```

Product/store upload goal:

```bash
python scripts/scbe_terminal_ops.py --api-key demo_key_12345 goal create --goal "Upload product updates and sync fulfillment metadata" --channel store_ops --priority high --execution-mode connector --connector-id <CONNECTOR_ID>
```

## Run goal steps

```bash
python scripts/scbe_terminal_ops.py --api-key demo_key_12345 goal run --goal-id <GOAL_ID>
```

If blocked for high-risk review:

```bash
python scripts/scbe_terminal_ops.py --api-key demo_key_12345 goal approve --goal-id <GOAL_ID>
```

Then continue run:

```bash
python scripts/scbe_terminal_ops.py --api-key demo_key_12345 goal run --goal-id <GOAL_ID>
```

## Notes

1. Keep `require_human_for_high_risk=true` for production goals.
2. Store real connector secrets in secret manager in production.
3. For unattended test runs only, use:
   - `goal run --auto-approve-high-risk`

