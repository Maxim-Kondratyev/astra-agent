# ASTRA — Autonomous Security, Tenancy & Resilience Assessor

## Vision

An AI agent that autonomously assesses a customer's AWS environment against security, resilience, and SaaS/tenancy best practices using read-only access. Produces a prioritised report with scores and actionable recommendations — no manual reviews required.

## Problem Statement

Mature ISV customers (e.g., JetBrains, Dynatrace) don't have time for lengthy manual reviews. They need:
- A clear benchmark of where they stand
- Prioritised actions to improve
- Minimal effort on their side (grant read-only access, receive report)

## Goals Alignment

| Team Goal | How ASTRA Contributes |
|-----------|----------------------|
| G7: Agentic AI | The agent itself IS the artifact |
| G1: Resilience | Module 1 performs resilience assessment |
| G2: Security | Module 2 performs security posture assessment |
| G6: SaaS Architecture | Module 3 assesses tenant isolation and SaaS patterns |
| G8: Scaled Impact | Reusable across EMEA-ISV customers (Pathfinder potential) |
| G3: Strategic Leadership | Each deployment = SSP initiative with ISCs |

## Technology Stack (G7-qualifying)

| Component | Technology | Why |
|-----------|-----------|-----|
| Agent Framework | **Strands Agents SDK** (Python) | AWS open-source agent framework, counts for G7 |
| Agent Runtime | **Amazon Bedrock AgentCore** | Managed hosting for the agent, counts for G7 |
| Foundation Model | **Claude (Bedrock)** | Reasoning engine for assessment logic |
| Knowledge Base | **Bedrock Knowledge Bases** (S3 + OpenSearch Serverless) | Stores WA pillars, SIP v2, Resilience Lifecycle docs |
| AWS Data Sources | Security Hub, Config, IAM Access Analyzer, Resilience Hub, Trusted Advisor | Read-only queries for actual environment state |
| Deployment | **CDK (Python)** | Infrastructure as Code for customer deployment |
| Output | Structured JSON + HTML report | Assessment results |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Customer AWS Account                   │
│                                                          │
│  ┌──────────────┐    ┌─────────────────────────────┐    │
│  │ Read-Only    │    │ ASTRA Agent (Lambda/ECS)     │    │
│  │ IAM Role     │◄───│                              │    │
│  │              │    │  ┌─────────┐ ┌───────────┐  │    │
│  │ - SecurityAudit   │  │ Module 1│ │ Module 2  │  │    │
│  │ - ReadOnlyAccess  │  │Resilience│ │ Security  │  │    │
│  │              │    │  └─────────┘ └───────────┘  │    │
│  └──────────────┘    │  ┌─────────┐               │    │
│                      │  │ Module 3│               │    │
│  ┌──────────────┐    │  │ SaaS    │               │    │
│  │ Knowledge    │    │  └─────────┘               │    │
│  │ Base (S3)    │◄───│                              │    │
│  │ - WA Pillars │    └─────────────────────────────┘    │
│  │ - SIP v2     │                   │                    │
│  │ - Resilience │                   ▼                    │
│  │   Lifecycle  │    ┌─────────────────────────────┐    │
│  └──────────────┘    │ Assessment Report (S3)       │    │
│                      │ - Scores per module           │    │
│                      │ - Prioritised findings        │    │
│                      │ - Recommended actions         │    │
│                      └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

## Modules

### Module 1: Resilience Assessment

**Knowledge Base Sources:**
- Well-Architected Reliability Pillar
- Resilience Lifecycle Framework (Stages 1-3)
- AWS Resilience Hub best practices

**Checks (read-only):**
- Multi-AZ deployment verification
- Auto-scaling configuration review
- Backup policies and retention
- Cross-region replication status
- RDS Multi-AZ / Aurora failover config
- ELB health check configuration
- Route 53 failover routing policies
- Single points of failure detection

**Output:** Resilience score + gap list mapped to Resilience Lifecycle stages

---

### Module 2: Security Assessment

**Knowledge Base Sources:**
- Well-Architected Security Pillar
- SIP v2 assessment criteria
- AWS Security Best Practices

**Checks (read-only):**
- Security Hub findings summary and score
- GuardDuty enablement and findings
- IAM Access Analyzer findings
- Public access (S3, security groups, ELB)
- Encryption at rest/in transit status
- Root account usage / MFA status
- CloudTrail and logging configuration
- Secrets Manager / hardcoded credentials detection

**Output:** Security posture score + prioritised remediation plan

---

### Module 3: SaaS / Tenancy Assessment

**Knowledge Base Sources:**
- SaaS Lens (Well-Architected)
- AWS SaaS Architecture Patterns
- Tenant Isolation best practices

**Checks (read-only):**
- Tenant isolation patterns (account-level, VPC-level, resource-level)
- Noisy neighbour indicators (shared resources without throttling)
- Control plane / data plane separation
- Per-tenant observability (tagging, CloudWatch dimensions)
- Cost allocation by tenant (tagging strategy)
- Cross-tenant data access boundaries

**Output:** SaaS maturity score + isolation gap analysis

---

## Deployment Model

### What the customer does:
1. Deploy a CDK stack (one command: `cdk deploy`)
2. Stack creates: read-only IAM role, Lambda/ECS for agent, S3 bucket for KB + reports
3. Agent runs on-demand or on schedule (e.g., weekly)
4. Read the report

### What the TAM does:
1. Provide the CDK stack
2. Provide updated knowledge base content (versioned, no internet required)
3. Review results with the customer
4. Help prioritise and plan remediation

### Security Constraints:
- **Read-only access only** — agent CANNOT modify any resources
- **No internet egress** — knowledge base is local (S3), Bedrock is via VPC endpoint
- **No data leaves the account** — reports stay in customer's S3
- **Customer controls execution** — they trigger it, they own the output

## Customer Context Upload

### Purpose
Allow customers to upload their own architecture documentation so ASTRA can assess not only what's deployed, but also compare reality against documented intent.

### What customers can upload:
- Architecture diagrams (PDF, PNG, drawio exports)
- Design documents (markdown, PDF, Word)
- Runbooks and operational procedures
- SLA definitions (RTO/RPO targets)
- Security policies and compliance requirements
- Network topology diagrams
- Threat models

### How it works:
- Dedicated S3 prefix: `s3://<astra-bucket>/customer-docs/`
- Customer uploads files directly (S3 console, CLI, or a simple upload script)
- Bedrock Knowledge Base auto-syncs and indexes new documents
- Agent uses this context during assessment to:
  - Compare documented architecture vs actual deployed state
  - Validate stated RTO/RPO against infrastructure capabilities
  - Flag discrepancies between policy and reality
  - Provide more relevant, context-aware recommendations

### Assessment modes:
- **Without customer docs**: ASTRA assesses against AWS best practices only
- **With customer docs**: ASTRA also assesses against the customer's OWN stated goals and architecture

### Security:
- Documents stay in customer's S3 bucket (never leave the account)
- No internet access — indexing happens within the account
- Customer controls what they upload (no mandatory documents)
- Documents are encrypted at rest (S3 SSE-KMS)

---

## Non-Functional Requirements

- Agent execution completes within 15 minutes per module
- Report is human-readable (HTML) and machine-parseable (JSON)
- Works in eu-west-1, eu-central-1 (primary customer regions)
- Cost per assessment run: < $5 (Bedrock invocations + compute)
- No persistent infrastructure when not running (serverless)

## Success Criteria (MVP)

### Phase 1 — Prototype (2-3 weeks)
- [ ] Module 2 (Security) working on a test account
- [ ] 5 core security checks implemented
- [ ] Knowledge base loaded with WA Security Pillar
- [ ] Produces structured report
- [ ] Deployable via CDK

### Phase 2 — Expand (2-3 weeks)
- [ ] Module 1 (Resilience) added
- [ ] Module 3 (SaaS/Tenancy) added
- [ ] Full report with all three scores
- [ ] Tested on 2+ accounts

### Phase 3 — Customer Deployment
- [ ] Deploy to JetBrains (first customer)
- [ ] Document in SIFT + SSP
- [ ] Share with EMEA-ISV team (G8 scaled impact)

## Open Questions

1. Should the agent run in customer's account or in TAM's account with cross-account read role?
2. Bedrock model access — do all customer accounts have Bedrock enabled? If not, run in TAM account.
3. Knowledge base update cadence — quarterly? On-demand?
4. Should we support multi-account assessment (AWS Organizations)?
