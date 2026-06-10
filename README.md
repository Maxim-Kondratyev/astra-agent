# ASTRA

**Autonomous Security, Tenancy & Resilience Assessor**

An AI agent that autonomously assesses AWS environments against security best practices using read-only access. Produces a scored, prioritised report with actionable recommendations.

## What It Does

ASTRA calls 5 security assessment tools, sends the findings to Claude (via Amazon Bedrock), and produces a comprehensive security report:

| Tool | What It Checks |
|------|----------------|
| Security Hub Findings | Active compliance failures across all AWS services |
| GuardDuty Findings | Active threat detections |
| IAM Password Policy | Root MFA, password complexity, user MFA enrollment |
| S3 Public Access | Account-level and per-bucket public access exposure |
| Encryption at Rest | S3, EBS, and RDS encryption coverage |

**Output:** A scored assessment (0-100) with severity-ranked findings, affected resources, and specific remediation steps.

## Quick Start

```bash
# Install
pip install -e .

# Run (requires AWS credentials + Bedrock model access in us-east-1)
python -m astra

# Save HTML report
python -m astra --html report.html --account-id 123456789012

# Use a specific model
python -m astra --model us.anthropic.claude-opus-4-8
```

## Prerequisites

- Python 3.11+
- AWS credentials with read-only access (`SecurityAudit` managed policy)
- Bedrock model access enabled for Claude Sonnet 4.6 in us-east-1
- Security Hub enabled in the target account

## Deploy to a Customer Account (CDK)

```bash
cd infra
pip install -e ".[infra]"
cdk deploy
```

This deploys:
- **IAM Role** — `SecurityAudit` + `ReadOnlyAccess` + explicit DENY on all mutations
- **S3 Bucket** — Encrypted, no public access, SSL-enforced — stores reports
- **Lambda Function** — 15-min timeout, invokes the agent on trigger

After deployment, invoke the Lambda to run an assessment:
```bash
aws lambda invoke --function-name AstraStack-AstraFunction-xxx /tmp/result.json
```

## Security Guarantees

1. **Read-only IAM** — `SecurityAudit` + `ReadOnlyAccess` managed policies only
2. **Explicit DENY** — IAM policy explicitly denies Create/Delete/Modify/Update/Terminate on all resources
3. **No internet** — Can deploy with VPC endpoints only (Bedrock, S3)
4. **Data stays in-account** — Reports stored in customer's own S3 bucket
5. **No persistent state** — Lambda runs on-demand, no always-on infrastructure

## Project Structure

```
astra-agent/
├── src/astra/
│   ├── agent.py                # Agent definition (model + tools + prompt)
│   ├── __main__.py             # CLI: python -m astra
│   ├── tools/security.py       # 5 read-only security assessment tools
│   └── report/generator.py     # JSON → styled HTML report
├── infra/
│   ├── stacks/astra_stack.py   # CDK stack (IAM, S3, Lambda)
│   └── lambda/handler.py       # Lambda handler
├── specs/                      # Requirements, design, context
└── pyproject.toml
```

## Modules Roadmap

- [x] **Security** (Phase 1) — Security Hub, GuardDuty, IAM, S3, Encryption
- [ ] **Resilience** (Phase 2) — Multi-AZ, backups, failover, SPOF detection
- [ ] **SaaS/Tenancy** (Phase 3) — Tenant isolation, control plane, cost allocation

## Cost

< $5 per assessment run (Bedrock model invocations + Lambda compute).
