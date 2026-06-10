# ASTRA

**Autonomous Security, Tenancy & Resilience Assessor**

An AI agent that autonomously assesses AWS environments against security, resilience, and SaaS/tenancy best practices using read-only access.

## Modules

- **Security** — Security Hub, GuardDuty, IAM analysis, encryption, public access
- **Resilience** — Multi-AZ, backups, failover, single points of failure
- **SaaS/Tenancy** — Tenant isolation, control plane separation, cost allocation

## Tech Stack

- [Strands Agents SDK](https://github.com/strands-agents/sdk-python) (Python)
- Amazon Bedrock (Claude) for reasoning
- Bedrock Knowledge Bases for best-practice retrieval
- AWS CDK for deployment
- Read-only IAM role (SecurityAudit + ReadOnlyAccess)

## Status

🚧 Under development — Phase 1 (Security module prototype)
