# ASTRA Deployment Guide

## Deployment Options

| Method | Best For | Time | Prerequisites |
|--------|----------|------|---------------|
| **Local CLI** | Quick assessment, testing | 2 minutes | Python 3.11+, AWS credentials |
| **CDK Stack** | Customer production deployment | 10 minutes | AWS CDK, account access |

---

## Option 1: Local CLI (Quick Start)

### Prerequisites

- Python 3.11+
- AWS credentials with `SecurityAudit` managed policy
- Bedrock model access for Claude in `us-east-1`

### Steps

```bash
# 1. Clone and install
git clone https://github.com/Maxim-Kondratyev/astra-agent.git
cd astra-agent
pip install -e .

# 2. Configure AWS credentials
export AWS_DEFAULT_REGION=us-east-1
# Ensure your credentials have SecurityAudit + ReadOnlyAccess

# 3. Run assessment
python -m astra --html report.html

# 4. Open the report
open report.html  # macOS
# xdg-open report.html  # Linux
```

### CLI Options

```
python -m astra [OPTIONS]

Options:
  --model MODEL       Bedrock model ID (default: us.anthropic.claude-opus-4-8)
  --region REGION     AWS region for Bedrock (default: us-east-1)
  --module MODULE     Module to assess: security|resilience|saas|all (default: all)
  --html FILE         Save HTML report to file
  --output FILE       Save raw JSON output to file
  --account-id ID     Override account ID in report header (auto-detected)
```

### Examples

```bash
# Security only (fastest, ~2 min)
python -m astra --module security --html security-report.html

# Resilience only
python -m astra --module resilience --html resilience-report.html

# Full assessment (all 3 modules)
python -m astra --html full-assessment.html

# Use a cheaper model for cost-sensitive runs
python -m astra --model us.anthropic.claude-sonnet-4-6 --html report.html
```

---

## Option 2: CDK Stack (Production)

This deploys ASTRA as a self-contained, on-demand Lambda function in the customer's AWS account.

### What Gets Deployed

| Resource | Purpose |
|----------|---------|
| IAM Role | Read-only access (SecurityAudit + ReadOnlyAccess + explicit DENY on mutations) |
| Lambda Function | Runs the agent (15-min timeout, 512 MB) |
| S3 Bucket | Stores assessment reports (encrypted, no public access, SSL-enforced) |

### Prerequisites

- AWS CDK CLI installed: `npm install -g aws-cdk`
- Python 3.11+
- AWS credentials with admin access to deploy the stack
- Bedrock model access enabled for Claude in us-east-1

### Deployment Steps

```bash
# 1. Clone the repo
git clone https://github.com/Maxim-Kondratyev/astra-agent.git
cd astra-agent

# 2. Install dependencies
pip install -e ".[infra]"

# 3. Bootstrap CDK (first time only)
cd infra
cdk bootstrap

# 4. Deploy the stack
cdk deploy

# 5. Note the outputs:
#    - ReportsBucketName: where reports are saved
#    - AstraFunctionArn: the Lambda to invoke
#    - AstraRoleArn: the read-only IAM role
```

### Trigger an Assessment

```bash
# Invoke the Lambda function
aws lambda invoke \
  --function-name AstraStack-AstraFunction-XXXXX \
  --region us-east-1 \
  /tmp/response.json

# Check the response
cat /tmp/response.json
# → {"statusCode": 200, "body": "{\"report_key\": \"assessments/2026-06-10_2200/report.html\", ...}"}

# Download the report
aws s3 cp s3://astra-reports-ACCOUNT_ID/assessments/2026-06-10_2200/report.html ./report.html
open report.html
```

### Schedule Recurring Assessments

Add to `infra/stacks/astra_stack.py`:

```python
from aws_cdk import aws_events as events, aws_events_targets as targets

# Weekly assessment every Monday at 6 AM UTC
rule = events.Rule(self, "WeeklyAssessment",
    schedule=events.Schedule.cron(week_day="MON", hour="6", minute="0"),
)
rule.add_target(targets.LambdaFunction(astra_lambda))
```

---

## Customer Deployment Checklist

For TAMs deploying ASTRA to a customer account:

- [ ] Customer has Bedrock model access enabled (Claude Sonnet or Opus in us-east-1)
- [ ] Customer account has Security Hub enabled
- [ ] Customer account has GuardDuty enabled (recommended but not required)
- [ ] CDK bootstrap has been run in the target account/region
- [ ] Customer understands what gets deployed (IAM role, Lambda, S3 bucket)
- [ ] Customer confirms the read-only guarantees are acceptable
- [ ] Deploy the CDK stack
- [ ] Run the first assessment
- [ ] Review the report together with the customer
- [ ] Set up a recurring schedule (optional)
- [ ] Document in SIFT + SSP

---

## Cost Estimate

| Component | Per Assessment | Monthly (weekly schedule) |
|-----------|---------------|--------------------------|
| Bedrock (Opus 4.8) | ~$3-5 | ~$12-20 |
| Bedrock (Sonnet 4.6) | ~$0.50-1.00 | ~$2-4 |
| Lambda compute | ~$0.02 | ~$0.08 |
| S3 storage | negligible | < $0.01 |
| **Total (Opus)** | **~$3-5** | **~$12-20** |
| **Total (Sonnet)** | **~$0.50-1.00** | **~$2-4** |

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `AccessDeniedException` on Bedrock | Model not enabled | Enable model access in Bedrock console → Model access |
| `InvalidAccessException` on Security Hub | Security Hub not enabled | Enable Security Hub in the account |
| Lambda timeout | Too many resources | Run individual modules: `--module security` |
| Empty findings | Services not configured | Enable Security Hub + GuardDuty for meaningful results |

---

## Uninstalling

```bash
# Remove the CDK stack
cd infra
cdk destroy

# This removes:
# - Lambda function
# - IAM role
# Note: S3 bucket is RETAINED (contains your reports)
```
