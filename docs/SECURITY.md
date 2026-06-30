# ASTRA Security Model

## Core Principle: Read-Only Only

ASTRA **cannot** modify, create, or delete any resource in your AWS account. This is enforced at multiple layers:

### Layer 1: IAM Policies (Allow)

ASTRA uses two AWS-managed policies that grant read-only access:
- `SecurityAudit` — read access to security services
- `ReadOnlyAccess` — read access to all AWS services

### Layer 2: Explicit Deny (Enforce)

Even if ReadOnlyAccess inadvertently allows an action, ASTRA's IAM role includes an **explicit deny** statement that blocks all mutations AND sensitive data access:

```json
{
  "Effect": "Deny",
  "Action": [
    "ec2:Terminate*", "ec2:Delete*", "ec2:Modify*", "ec2:Create*", "ec2:Run*", "ec2:Stop*", "ec2:Start*",
    "s3:Delete*", "s3:PutBucketPolicy", "s3:PutBucketAcl",
    "s3:GetObject", "s3:GetObjectVersion", "s3:GetObjectTorrent",
    "secretsmanager:GetSecretValue",
    "iam:Create*", "iam:Delete*", "iam:Update*", "iam:Attach*", "iam:Detach*", "iam:Put*",
    "rds:Delete*", "rds:Modify*", "rds:Create*", "rds:Stop*", "rds:Start*",
    "lambda:Delete*", "lambda:Update*", "lambda:Create*",
    "elasticloadbalancing:Delete*", "elasticloadbalancing:Create*", "elasticloadbalancing:Modify*",
    "autoscaling:Delete*", "autoscaling:Create*", "autoscaling:Update*",
    "route53:Change*", "route53:Create*", "route53:Delete*",
    "cloudwatch:Delete*", "cloudwatch:Put*"
  ],
  "Resource": "*"
}
```

In IAM, **Deny always overrides Allow**. Even though `ReadOnlyAccess` grants `s3:Get*` and `secretsmanager:GetSecretValue`, the explicit deny blocks these — ASTRA cannot read your file contents or secrets.

### Layer 3: No Internet (CDK deployment)

When deployed via CDK, ASTRA runs in a VPC with:
- No NAT gateway (no internet route)
- No internet gateway
- Only VPC endpoints for Bedrock and S3

This means no data can leave your account.

### Layer 4: Code is Open Source

All 34 checks are plaintext Python — you can audit exactly what API calls are made:
- `src/astra/checklist/security.py` — 12 security checks
- `src/astra/checklist/resilience.py` — 12 resilience checks
- `src/astra/checklist/saas.py` — 10 SaaS checks

Every check uses `boto3.client("<service>")` with read-only API calls (`describe_*`, `list_*`, `get_*`).

## Data Handling

| Data | Where it goes |
|------|--------------|
| AWS API responses | In-memory only (not persisted) |
| Assessment report | Your local filesystem or your S3 bucket |
| Customer context docs | Read into memory, sent to Bedrock (stays in-region) |
| Bedrock model calls | AWS region you specify (default: us-east-1) |

## What ASTRA Does NOT Do

- ❌ Create, modify, or delete any AWS resource
- ❌ Store your data outside your account
- ❌ Make outbound internet connections
- ❌ Access S3 object contents (only bucket metadata)
- ❌ Read Secrets Manager secret values
- ❌ Access any customer application data

## What ASTRA Does (the one non-read action)

- ✅ Calls **Amazon Bedrock** (`bedrock:InvokeModel`) to generate the assessment report and power interactive chat
- This sends check results (resource IDs, configuration status) to Claude for analysis
- Data stays within your AWS region (Bedrock is a regional service)
- You can skip this entirely with `--checks-only` (zero Bedrock calls)

## Verifying Security

Before deploying, you can:

1. **Audit the code** — all checks are in `src/astra/checklist/`
2. **Run `--checks-only`** — no Bedrock call, pure boto3 reads
3. **Use CloudTrail** — every API call ASTRA makes is logged
4. **Review the CDK stack** — `infra/stacks/astra_stack.py` shows all IAM statements
