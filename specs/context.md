# ASTRA — Project Context & Decisions Log

## Origin Story

ASTRA was born from a practical problem: EMEA-ISV TAM goals (H1 2026) require multiple customer engagements across different domains (security, resilience, SaaS, agentic AI). Rather than treating each goal independently, ASTRA unifies them into a single artifact that covers G7, G1, G2, G6, G8, and G3 simultaneously.

## The Problem It Solves

Mature ISV customers (JetBrains, Dynatrace) don't want to spend time on manual reviews:
- Every engineer's time is accounted for
- Cloud budgets are tightly controlled
- New tools require procurement approval
- No sandbox freedom for experimentation

ASTRA's pitch: "Grant read-only access, receive a comprehensive assessment. No meetings, no workshops, no disruption."

## Key Design Decisions

### 1. Read-Only Only
- Agent CANNOT modify any customer resources
- Uses SecurityAudit + ReadOnlyAccess managed policies
- This is non-negotiable for customer trust

### 2. No Internet Access
- Knowledge base is local (S3 in customer account)
- Bedrock access via VPC endpoint
- No data leaves the customer account
- TAM provides knowledge base updates as new versions of the deployment package

### 3. Modular Architecture
- Module 1: Resilience (→ G1)
- Module 2: Security (→ G2)  
- Module 3: SaaS/Tenancy (→ G6)
- Customers can run one, two, or all three modules

### 4. Tech Stack (G7-qualifying)
- **Strands Agents SDK** — AWS open-source agent framework
- **Bedrock AgentCore** — managed agent runtime (if available in region, else Lambda)
- **Bedrock Knowledge Bases** — RAG for best-practice retrieval
- **CDK (Python)** — one-command deployment

### 5. Deployment Model
- Runs in CUSTOMER's account (not TAM's)
- Customer pays for Bedrock invocations (< $5 per assessment run)
- Alternative: if customer doesn't have Bedrock enabled, run in TAM account with cross-account read role (open question)

### 6. Agent Runtime
- Lambda for MVP (simpler, 15-min timeout sufficient)
- AgentCore if available in eu-west-1/eu-central-1
- ECS Fargate as fallback for longer runs

## Goal Coverage Map

| Goal | How ASTRA Covers It | Evidence |
|------|---------------------|----------|
| G7: Agentic AI | The agent IS the artifact — built with Strands/AgentCore/Bedrock Agents | Repo + deployment to customer |
| G1: Resilience | Module 1 performs autonomous resilience assessment | Assessment report documenting findings |
| G2: Security | Module 2 performs autonomous security posture assessment | Security score + remediation plan |
| G6: SaaS Architecture | Module 3 assesses tenant isolation and SaaS patterns | SaaS maturity score |
| G8: Scaled Impact | Reusable across EMEA-ISV customers, potential Pathfinder | Shared with team, multiple customer deployments |
| G3: Strategic Leadership | Each customer deployment = SSP initiative with ISCs | SSP entry per customer |

## Target Customers

1. **JetBrains** (Central Platform) — primary target, CISO engagement already planned
2. **Dynatrace** — secondary, familiar relationship

## Development Phases

### Phase 1: Security Module Prototype (Weeks 1-3)
- [ ] Project skeleton (Strands agent + CDK)
- [ ] 5 core security tools (Security Hub, GuardDuty, IAM Analyzer, public access, encryption)
- [ ] Knowledge base with WA Security Pillar
- [ ] Structured report output (JSON + HTML)
- [ ] Deployable via CDK to test account
- [ ] Tested and validated

### Phase 2: Add Resilience + SaaS (Weeks 4-5)
- [ ] Resilience tools (Multi-AZ, backups, failover, SPOF detection)
- [ ] SaaS tools (tenant isolation, tagging, control plane)
- [ ] Combined report with all three scores
- [ ] Knowledge base expanded with Reliability Pillar + SaaS Lens

### Phase 3: Customer Deployment (Week 6+)
- [ ] Deploy to JetBrains
- [ ] Document in SIFT + SSP
- [ ] Share with EMEA-ISV team
- [ ] Propose as Pathfinder project

## Open Questions (To Resolve Before/During Build)

1. **Where does the agent run?** Customer account (ideal for data sovereignty) vs TAM account (simpler if customer lacks Bedrock access)
2. **Bedrock model access** — do JetBrains/Dynatrace have Bedrock enabled? If not, cross-account pattern needed
3. **Knowledge base update cadence** — quarterly? On-demand when new WA content drops?
4. **Multi-account support** — should ASTRA assess all accounts in an AWS Organization, or one at a time?
5. **AgentCore availability** — check if AgentCore is GA in eu-west-1 / eu-central-1

## Related Context

### G7 Clarification Sent
A message was sent to rosslyal (G7 goal owner) on 2026-06-10 asking:
1. Does a delivered artifact count even without customer production deployment?
2. Does a workshop with hands-on output count?
3. Is there a ready-made workshop TAMs can run and have counted?
4. How should TAMs with mature ISV customers approach G7?

### Customer Engagement Plan
- JetBrains CISO engagement planned for SIP v2 (G2) and FIS Gameday (G1)
- ASTRA can be positioned as the "automated version" — runs continuously vs one-off review
- Pitch: "We'll deploy an agent that does the assessment for you. All you do is grant read-only access and read the report."

## How to Continue Building

When starting a new session:
1. Point to this repo: https://github.com/Maxim-Kondratyev/astra-agent
2. Read this file for full context
3. Check Phase 1 checklist above for next tasks
4. Start with: project skeleton → first tool → agent wiring → CDK stack

## Project Location

- **GitHub**: https://github.com/Maxim-Kondratyev/astra-agent (private)
- **Local**: ~/Projects/astra
