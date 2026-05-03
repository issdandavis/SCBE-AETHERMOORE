# AWS Free Tier Portal

Date: 2026-05-03

Purpose: switch from a root AWS key to a limited SCBE automation profile without using the AWS console.

## Bootstrap Command

Dry-run:

```powershell
python scripts/system/aws_free_tier_portal.py --json
```

Execute:

```powershell
python scripts/system/aws_free_tier_portal.py --execute --json
```

## Created Identity

- AWS CLI profile: `scbe-free-tier`
- IAM user: `scbe-free-tier-operator`
- Lambda execution role: `scbe-lambda-basic-exec`
- Inline policy: `SCBEFreeTierOperatorPolicy`
- Region: `us-east-1`

## Allowed Lanes

The operator profile is limited to:

- AWS Lambda function CRUD/invoke,
- Amazon DynamoDB table/item operations,
- Amazon SNS topic/publish operations,
- Amazon SES send/quota/statistics/identity checks,
- CloudWatch Logs writes/reads needed by Lambda,
- `iam:PassRole` only for `scbe-lambda-basic-exec`,
- own IAM access-key maintenance.

It does not attach `AdministratorAccess` and does not allow `iam:*`.

## Verify

```powershell
aws sts get-caller-identity --profile scbe-free-tier --output json
aws lambda list-functions --profile scbe-free-tier --region us-east-1 --max-items 5
aws dynamodb list-tables --profile scbe-free-tier --region us-east-1 --limit 5
aws sns list-topics --profile scbe-free-tier --region us-east-1
aws ses get-send-quota --profile scbe-free-tier --region us-east-1
```

## Security Note

The root key was used only as a local bootstrap source. It should be deactivated or deleted after the limited profile is confirmed and any needed billing/MFA setup is done from the AWS account root console.
