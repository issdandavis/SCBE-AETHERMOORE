# SCBE Free Tier Demo User Guide

Generated: 2026-05-03T17:26:41.040178+00:00

This guide is generated from the same packet used to deploy the demo stack. It is the
buyer-facing version of the working prototype: a small customer-capacity gate built
from AWS Lambda, Amazon DynamoDB, Amazon SNS, and Amazon SES quota inspection.

## What The Demo Proves

- A customer record can live in `scbe-free-tier-demo-customers`.
- Usage events can be recorded in `scbe-free-tier-demo-usage-events`.
- A capacity gate can run as `scbe-free-tier-demo-capacity-gate`.
- Upgrade signals can publish through `scbe-free-tier-demo-upgrade-events`.
- Email delivery stays gated until Amazon SES identities are verified.

## Run The Local Check

```powershell
aws sts get-caller-identity --profile scbe-free-tier --region us-east-1
```

## Invoke The Capacity Gate

```powershell
$payloadPath = "artifacts/aws_free_tier_demo_payload.json"
'{"customer_id":"demo-customer","tier":"free","used_actions":199,"requested_actions":3}' | Set-Content -Path $payloadPath -Encoding utf8
aws lambda invoke --function-name scbe-free-tier-demo-capacity-gate --payload file://$payloadPath --cli-binary-format raw-in-base64-out --profile scbe-free-tier --region us-east-1 artifacts/aws_free_tier_demo_response.json
Get-Content artifacts/aws_free_tier_demo_response.json
```

## Customer Ladder

| Tier | Monthly actions | Agents | Research packets | Upgrade signal |
| --- | ---: | ---: | ---: | ---: |
| free | 250 | 2 | 25 | 80% |
| starter | 2500 | 6 | 250 | 85% |
| pro | 25000 | 18 | 2500 | 90% |
| business | 250000 | 64 | 25000 | 92% |

## Promotion Rule

Keep the stack in demo mode until the customer guide, the Lambda response, the
DynamoDB seed records, and the SES identity status are all present. After that,
the next paid tier adds an authenticated public endpoint and real email delivery.
