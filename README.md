# ASTRA — Autonomous Security, Tenancy & Resilience Assessor

An AI-powered agent that autonomously assesses AWS environments against the **Well-Architected Framework** using read-only access. Runs 34 prebuilt checks across Security, Resilience, and SaaS/Tenancy — then produces an executive-grade report with prioritised recommendations.

```
python -m astra -m security -m resilience --html report.html
```

## How It Works

```
┌────────────────┐     ┌──────────────────┐     ┌────────────────┐
│  34 Prebuilt   │────▶│  LLM Analysis    │────▶│  HTML Report   │
│  AWS Checks    │     │  (Claude/Bedrock) │     │  with Scores   │
│  (read-only)   │     │  + Customer Ctx   │     │  & Remediation │
└────────────────┘     └──────────────────┘     └────────────────┘
```

1. **Deterministic checks** — runs all checks against AWS APIs (read-only, no modifications)
2. **LLM analysis** — passes results + WA best practices to Claude for scoring and narrative
3. **Report generation** — produces styled HTML with per-module scores and prioritised fixes

## Modules

| Module | Checks | WA Mapping |
|--------|--------|-----------|
| 🛡️ Security | 12 | Security Pillar (SEC 2–7) |
| 🏗️ Resilience | 12 | Reliability Pillar (REL 6–13) |
| 🏢 SaaS | 10 | SaaS Lens |

### Security Checks (SEC-01 to SEC-12)
Security Hub, GuardDuty, root MFA, password policy, S3 public access block, CloudTrail, VPC flow logs, security groups, IAM Access Analyzer, EBS encryption default, Secrets Manager rotation, KMS key rotation.

### Resilience Checks (REL-01 to REL-12)
RDS Multi-AZ, EC2 AZ spread, ASG health checks, ASG multi-AZ, ELB multi-AZ, AWS Backup plans, RDS backup retention, NAT Gateway redundancy, EBS snapshots, Route 53 health checks, ElastiCache Multi-AZ, CloudWatch alarms.

### SaaS Checks (SAS-01 to SAS-10)
Tenant tagging, cost allocation tags, permission boundaries, resource isolation, per-tenant monitoring, API throttling, control plane separation, cross-tenant access, tenant onboarding automation, noisy neighbour detection.

## Quick Start

### Prerequisites
- Python 3.11+
- AWS credentials with **read-only** access (SecurityAudit + ReadOnlyAccess managed policies)
- Amazon Bedrock model access (Claude Sonnet)

### Install

```bash
git clone https://github.com/Maxim-Kondratyev/astra-agent.git
cd astra-agent
pip install -e .
```

### Run

```bash
# All modules
python -m astra --html report.html

# Single module
python -m astra -m security --html security-report.html

# Multiple modules
python -m astra -m security -m resilience --html report.html

# With customer context (architecture docs)
python -m astra --context-dir ./customer-docs/ --html report.html
```

### Output Options

| Flag | Description |
|------|-------------|
| `--html FILE` | Styled HTML report |
| `--output FILE` | Raw JSON report |
| `-m MODULE` | Module to assess (repeatable: `-m security -m resilience`) |
| `-c DIR` | Customer context directory for tailored recommendations |
| `--model ID` | Bedrock model ID (default: Claude Sonnet 4) |
| `--region` | AWS region for Bedrock API calls |

## Customer Context Upload

Drop your architecture documentation in a folder and pass it with `--context-dir`:

```bash
mkdir customer-docs/
# Add your files:
#   customer-docs/architecture.md
#   customer-docs/rto-rpo-requirements.txt
#   customer-docs/network-topology.yaml

python -m astra -c ./customer-docs/ --html report.html
```

Supported formats: `.md`, `.txt`, `.yaml`, `.yml`, `.json`

The agent uses this context to:
- Compare **documented architecture** against **actual deployed state**
- Validate stated RTO/RPO against backup/failover configuration
- Flag discrepancies between policy and reality
- Provide more relevant, context-aware recommendations

## Deployment (CDK)

For automated recurring assessments in a customer's AWS account:

```bash
cd infra
pip install -e ".[infra]"
cdk deploy
```

This deploys:
- Lambda function running ASTRA on schedule (weekly)
- Read-only IAM role with **explicit deny** on all mutations
- VPC with no internet access (Bedrock via VPC endpoint)
- S3 bucket for reports (encrypted, versioned)

## Architecture

```
┌─── Customer AWS Account ────────────────────────────────────────┐
│                                                                   │
│  ┌─────────────┐    ┌──────────────────────────────────────┐    │
│  │ IAM Role    │    │ ASTRA Agent                          │    │
│  │ (read-only  │───▶│                                      │    │
│  │  + deny)    │    │  ┌────────────┐  ┌───────────────┐   │    │
│  └─────────────┘    │  │ Checklists │  │ LLM Analysis  │   │    │
│                      │  │ 34 checks  │  │ (Bedrock)     │   │    │
│  ┌─────────────┐    │  └────────────┘  └───────────────┘   │    │
│  │ Customer    │───▶│  ┌────────────────────────────────┐   │    │
│  │ Context     │    │  │ Report Generator (HTML/JSON)    │   │    │
│  │ (optional)  │    │  └────────────────────────────────┘   │    │
│  └─────────────┘    └──────────────────────────────────────┘    │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ AWS APIs (read-only): Security Hub, GuardDuty, IAM, EC2,  │  │
│  │ RDS, ELB, Backup, Route53, CloudTrail, S3, KMS, Lambda... │  │
│  └────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Security Guarantees

- **Read-only access only** — agent CANNOT modify resources
- **Explicit IAM deny** on all create/update/delete/terminate actions
- **No internet egress** — Bedrock accessed via VPC endpoint
- **No data leaves the account** — reports stay in customer's S3
- **Customer controls execution** — they trigger it, they own the output

## Project Structure

```
astra-agent/
├── src/astra/
│   ├── __main__.py          # CLI entry point
│   ├── assessment.py        # Unified assessment runner
│   ├── agent.py             # Strands agent (legacy mode)
│   ├── checklist/
│   │   ├── resilience.py    # 12 WA Reliability Pillar checks
│   │   ├── security.py      # 12 WA Security Pillar checks
│   │   └── saas.py          # 10 WA SaaS Lens checks
│   ├── report/
│   │   └── generator.py     # HTML report generator
│   ├── knowledge/           # WA best practice reference docs
│   └── tools/               # Raw AWS API tools (legacy)
├── infra/                   # CDK deployment stack
├── specs/                   # Requirements & design docs
├── docs/                    # Architecture & security docs
└── pyproject.toml
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Agent Framework | [Strands Agents SDK](https://github.com/strands-agents/sdk-python) |
| Foundation Model | Claude Sonnet (Amazon Bedrock) |
| Infrastructure | AWS CDK (Python) |
| Checks | boto3 (read-only AWS API calls) |
| Report | HTML with inline CSS |

## License

Private — EMEA-ISV TAM team internal project.
