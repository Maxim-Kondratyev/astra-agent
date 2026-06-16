# ASTRA Architecture

## Design Philosophy

**Deterministic first, AI second.**

Unlike typical AI agents that decide what to do at runtime, ASTRA uses a **fixed checklist** of 34 pre-defined checks. The AI (Claude via Bedrock) is only used for the final step: synthesising results into a narrative report with context-aware recommendations.

This means:
- Assessments are **repeatable** — same checks every time
- Results are **auditable** — you can trace exactly which API calls were made
- The AI enhances, never controls — if Bedrock is unavailable, `--checks-only` still works

## System Flow

```
┌─────────────────────────────────────────────────────────────┐
│                                                               │
│  1. CHECKS (deterministic, concurrent)                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │  Security    │ │  Resilience  │ │    SaaS      │         │
│  │  12 checks   │ │  12 checks   │ │  10 checks   │         │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘         │
│         │                 │                 │                  │
│         └────────────┬────┘─────────────────┘                 │
│                      ▼                                        │
│  2. CONTEXT (optional)                                        │
│  ┌──────────────────────────────────────────┐                │
│  │  WA Knowledge Base + Customer Docs       │                │
│  └──────────────────┬───────────────────────┘                │
│                      ▼                                        │
│  3. REPORT (LLM)                                             │
│  ┌──────────────────────────────────────────┐                │
│  │  Claude (Bedrock) → JSON → HTML          │                │
│  └──────────────────────────────────────────┘                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

| Component | File | Role |
|-----------|------|------|
| CLI | `src/astra/__main__.py` | User interface, argument parsing |
| Runner | `src/astra/assessment.py` | Orchestrates checks → context → LLM |
| Security checks | `src/astra/checklist/security.py` | 12 AWS Security Pillar checks |
| Resilience checks | `src/astra/checklist/resilience.py` | 12 AWS Reliability Pillar checks |
| SaaS checks | `src/astra/checklist/saas.py` | 10 AWS SaaS Lens checks |
| Report generator | `src/astra/report/generator.py` | JSON → styled HTML |
| Knowledge base | `src/astra/knowledge/` | WA best practices (sent to LLM as context) |
| Infrastructure | `infra/` | CDK stack for automated deployment |

## Concurrency Model

Checks run in parallel using `ThreadPoolExecutor(max_workers=3)`:
- Thread 1: All 12 security checks (sequential within module)
- Thread 2: All 12 resilience checks (sequential within module)
- Thread 3: All 10 SaaS checks (sequential within module)

Within each module, checks run sequentially because they share boto3 clients and some depend on the same API calls (e.g., multiple checks query `describe_instances`).

## Report Generation

The LLM receives:
1. **Structured check results** — PASS/FAIL/WARNING for each of 34 checks with evidence
2. **WA knowledge base** — official best practice text for referenced questions
3. **Customer context** (optional) — architecture docs, RTO/RPO requirements

The LLM produces:
- Overall score (0-100)
- Per-module scores
- Executive summary
- Prioritised recommendations tailored to the customer's context

## CDK Deployment Architecture

```
┌─── Customer AWS Account ─────────────────────────┐
│                                                    │
│  ┌──────────┐       ┌─────────────────────────┐  │
│  │ VPC      │       │ Lambda (ASTRA)          │  │
│  │ (private,│──────▶│ - 15 min timeout        │  │
│  │  no NAT) │       │ - 1024 MB memory        │  │
│  └──────────┘       │ - read-only IAM role    │  │
│       │              └────────────┬────────────┘  │
│  ┌────┴─────┐                    │                │
│  │ VPC      │                    ▼                │
│  │ Endpoints│       ┌─────────────────────────┐  │
│  │ - Bedrock│       │ S3 Bucket (reports)     │  │
│  │ - S3     │       │ - Encrypted (SSE-S3)    │  │
│  │ - STS    │       │ - Versioned             │  │
│  └──────────┘       │ - 365-day lifecycle     │  │
│                      └─────────────────────────┘  │
│                                                    │
│  ┌─────────────────────────────────────────────┐  │
│  │ EventBridge (weekly trigger, off by default)│  │
│  └─────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────┘
```
