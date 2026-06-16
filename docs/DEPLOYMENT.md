# ASTRA Deployment Guide

## Overview

ASTRA assesses your AWS account using **read-only access** and produces a report with scores and recommendations. You have two deployment options:

| Method | Best For | Time | Cost |
|--------|----------|------|------|
| **Local (CLI)** | Quick one-off assessment | 5 min setup | ~$0.05 per run (Bedrock) |
| **CDK (automated)** | Recurring weekly assessments | 15 min setup | ~$5/month |

---

## Option 1: Local CLI (Recommended for first run)

### Prerequisites

- Python 3.11+
- AWS credentials with read-only access
- Amazon Bedrock model access (Claude Sonnet) in us-east-1

### Step 1: Install

```bash
git clone https://github.com/Maxim-Kondratyev/astra-agent.git
cd astra-agent
pip install -e .
```

### Step 2: Configure AWS Access

ASTRA needs **read-only** AWS credentials. The simplest approach:

```bash
# Option A: Use existing credentials with ReadOnlyAccess
aws configure

# Option B: Create a dedicated read-only role and assume it
aws sts assume-role \
  --role-arn arn:aws:iam::YOUR_ACCOUNT_ID:role/AstraReadOnly \
  --role-session-name astra-assessment
```

**Minimum required policies:**
- `arn:aws:iam::aws:policy/SecurityAudit`
- `arn:aws:iam::aws:policy/ReadOnlyAccess`

### Step 3: Enable Bedrock Model Access

In the AWS Console → Amazon Bedrock → Model access:
- Enable **Claude 3.5 Sonnet** (or Claude Sonnet 4)
- Region: us-east-1

### Step 4: Run Assessment

```bash
# Full assessment (all 3 modules)
astra --html report.html

# Security only
astra -m security --html security-report.html

# With your architecture documentation for tailored recommendations
astra -c ./my-docs/ --html report.html

# Quick check without LLM (free, fast, CI/CD friendly)
astra --checks-only -o results.json
```

### Step 5: Review Report

Open `report.html` in your browser. The report includes:
- Overall score (0-100) and risk level
- Per-module scores (Security, Resilience, SaaS)
- Checklist summary (✅/❌/⚠️ at a glance)
- Detailed findings with affected resources
- Prioritised top 5 recommendations
- WA Framework references for each finding

---

## Option 2: CDK Deployment (Automated recurring assessments)

### Prerequisites

- AWS CDK CLI (`npm install -g aws-cdk`)
- Python 3.11+
- AWS account with CDK bootstrapped (`cdk bootstrap`)

### Step 1: Deploy

```bash
cd infra
pip install -e ".[infra]"
cdk deploy
```

### What Gets Deployed

| Resource | Purpose |
|----------|---------|
| Lambda function | Runs ASTRA on schedule |
| IAM role | Read-only + explicit deny on all mutations |
| VPC (private) | No internet access — Bedrock via VPC endpoint |
| S3 bucket | Stores assessment reports (encrypted, versioned) |
| EventBridge rule | Weekly schedule (Monday 6AM UTC, disabled by default) |

### Step 2: Trigger First Run

```bash
# Invoke manually
aws lambda invoke \
  --function-name AstraFunction \
  --payload '{"modules": ["security", "resilience"]}' \
  output.json
```

### Step 3: Enable Schedule

In the AWS Console → EventBridge → Rules → Enable "WeeklyAssessment"

---

## Customer Context (Optional)

For more accurate recommendations, provide your architecture documentation:

```bash
mkdir customer-docs/
# Add any of these:
#   architecture.md    — system overview, components, dependencies
#   requirements.txt   — RTO/RPO targets, SLA definitions
#   network.yaml       — VPC layout, connectivity
#   security-policy.md — compliance requirements
```

See `examples/customer-context/architecture.md` for a template.

---

## IAM Role Setup (for cross-account access)

If a TAM is running ASTRA against your account from their own account:

```bash
# In YOUR account: create the read-only role
aws iam create-role \
  --role-name AstraReadOnly \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::TAM_ACCOUNT_ID:root"},
      "Action": "sts:AssumeRole",
      "Condition": {"StringEquals": {"sts:ExternalId": "ASTRA-ASSESSMENT"}}
    }]
  }'

# Attach read-only policies
aws iam attach-role-policy --role-name AstraReadOnly \
  --policy-arn arn:aws:iam::aws:policy/SecurityAudit
aws iam attach-role-policy --role-name AstraReadOnly \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `AccessDeniedException` on Bedrock | Enable model access in Bedrock console (us-east-1) |
| `InvalidAccessException` on Security Hub | Security Hub not enabled — check will report FAIL (expected) |
| Slow execution | Use `--checks-only` for instant results without LLM |
| Want specific modules only | Use `-m security` or `-m resilience` (repeatable) |
