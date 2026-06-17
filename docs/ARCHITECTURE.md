# ASTRA Architecture

## Design Philosophy

> **Deterministic first, AI second.**

ASTRA separates **data collection** (deterministic, auditable) from **analysis** (AI-powered, contextual). The AI never decides what to check — it only interprets results that have already been gathered.

| Principle | Implementation |
|-----------|---------------|
| Repeatable | Same 34 checks run identically every time |
| Auditable | Every API call is traceable in CloudTrail |
| Safe | Read-only IAM + explicit deny = provable no-write guarantee |
| Degradable | `--checks-only` works without Bedrock (zero AI dependency) |
| Fast | Concurrent execution across modules (~20s total) |

---

## End-to-End Flow

```
                            ┌─────────────────────────────────┐
                            │         USER INPUT               │
                            │                                   │
                            │  astra -m security -m resilience │
                            │        --context-dir ./docs      │
                            │        --chat --html report.html │
                            └─────────────┬───────────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│  PHASE 1: CHECKS (Deterministic — no AI, no cost)                            │
│  ═══════════════════════════════════════════════                              │
│                                                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐  │
│  │   🛡️ Security        │  │   🏗️ Resilience      │  │   🏢 SaaS           │  │
│  │   Thread 1           │  │   Thread 2           │  │   Thread 3          │  │
│  │                      │  │                      │  │                     │  │
│  │  SEC-01 SecHub       │  │  REL-01 RDS M-AZ    │  │  SAS-01 Tagging    │  │
│  │  SEC-02 GuardDuty    │  │  REL-02 EC2 AZ      │  │  SAS-02 CostAlloc  │  │
│  │  SEC-03 Root MFA     │  │  REL-03 ASG Health   │  │  SAS-03 Boundaries │  │
│  │  SEC-04 Password     │  │  REL-04 ASG AZ      │  │  SAS-04 Isolation  │  │
│  │  SEC-05 S3 Block     │  │  REL-05 ELB AZ      │  │  SAS-05 Monitoring │  │
│  │  SEC-06 CloudTrail   │  │  REL-06 Backup      │  │  SAS-06 Throttling │  │
│  │  SEC-07 Flow Logs    │  │  REL-07 RDS Backup   │  │  SAS-07 Ctrl Plane │  │
│  │  SEC-08 Sec Groups   │  │  REL-08 NAT GW      │  │  SAS-08 CrossAccess│  │
│  │  SEC-09 Access Anlzr  │  │  REL-09 EBS Snaps   │  │  SAS-09 Onboarding │  │
│  │  SEC-10 EBS Encrypt  │  │  REL-10 R53 Health   │  │  SAS-10 NoisyNghbr │  │
│  │  SEC-11 Secrets Rot  │  │  REL-11 Cache M-AZ   │  │                     │  │
│  │  SEC-12 KMS Rotation │  │  REL-12 CW Alarms   │  │                     │  │
│  └──────────┬───────────┘  └──────────┬───────────┘  └──────────┬──────────┘  │
│             │                          │                          │             │
│             └──────────────────────────┼──────────────────────────┘             │
│                                        │                                        │
│                                        ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │  RESULTS: 34 x CheckResult { check_id, status, evidence, resources }    │   │
│  └─────────────────────────────────────────────┬───────────────────────────┘   │
│                                                 │                               │
└─────────────────────────────────────────────────┼───────────────────────────────┘
                                                  │
                                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│  PHASE 2: CONTEXT ASSEMBLY                                                    │
│  ═════════════════════════                                                    │
│                                                                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐   │
│  │ Check Results    │  │ WA Knowledge Base │  │ Customer Docs (optional) │   │
│  │ (from Phase 1)   │  │ • Security Pillar │  │ • architecture.md        │   │
│  │                   │  │ • Reliability     │  │ • rto-requirements.txt   │   │
│  │ 34 structured    │  │ • SaaS Lens       │  │ • network-topology.yaml  │   │
│  │ PASS/FAIL/WARN   │  │                   │  │                          │   │
│  └────────┬─────────┘  └────────┬──────────┘  └────────────┬─────────────┘   │
│           │                      │                           │                 │
│           └──────────────────────┼───────────────────────────┘                 │
│                                  ▼                                             │
│           ┌──────────────────────────────────────────────┐                    │
│           │  ASSEMBLED PROMPT (structured text to LLM)    │                    │
│           └──────────────────────┬───────────────────────┘                    │
│                                  │                                             │
└──────────────────────────────────┼─────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                               │
│  PHASE 3: AI ANALYSIS (Claude (latest available) via Amazon Bedrock)                      │
│  ═══════════════════════════════════════════════════════                       │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐ │
│  │  LLM Task:                                                               │ │
│  │  • Score each module (0-100) based on pass/fail ratio + severity         │ │
│  │  • Write executive summary connecting findings across modules            │ │
│  │  • Prioritise recommendations by blast radius and remediation effort     │ │
│  │  • If customer context provided: compare stated goals vs reality         │ │
│  │                                                                           │ │
│  │  Output: Structured JSON report                                           │ │
│  └──────────────────────────────────────┬──────────────────────────────────┘ │
│                                          │                                    │
└──────────────────────────────────────────┼────────────────────────────────────┘
                                           │
                              ┌────────────┼────────────┐
                              ▼            ▼            ▼
                     ┌──────────────┐ ┌────────┐ ┌───────────────┐
                     │  HTML Report │ │  JSON  │ │  💬 Chat Mode  │
                     │  (styled,    │ │  (raw, │ │  (interactive  │
                     │   visual)    │ │  CI/CD)│ │   follow-up)   │
                     └──────────────┘ └────────┘ └───────────────┘
```

---

## Component Details

### 1. CLI (`src/astra/__main__.py`)

The entry point. Parses arguments, orchestrates the flow, handles output routing.

| Flag | Effect |
|------|--------|
| `-m security` | Selects which module(s) to run |
| `--checks-only` | Stops after Phase 1 (no AI, no cost) |
| `--context-dir` | Adds customer docs to Phase 2 |
| `--chat` | After Phase 3, enters interactive conversation |
| `--html` / `-o` | Controls output format |

### 2. Assessment Runner (`src/astra/assessment.py`)

Orchestrates the three phases:
- Creates a `ThreadPoolExecutor(max_workers=3)` for concurrent module execution
- Assembles the prompt with results + context
- Calls Bedrock via Strands SDK
- Returns structured result dictionary

### 3. Checklists (`src/astra/checklist/`)

Each check is a pure function: `() → CheckResult`

```python
@dataclass
class CheckResult:
    check_id: str              # e.g., "REL-01"
    title: str                 # e.g., "RDS Multi-AZ"
    status: Status             # PASS | FAIL | WARNING | ERROR
    evidence: dict             # Raw data from AWS API
    affected_resources: list   # Resource IDs that failed
    recommendation: str        # What to do about it
    wa_reference: str          # WA Framework question
```

Checks use only `boto3` read operations: `describe_*`, `list_*`, `get_*`.

### 4. Knowledge Base (`src/astra/knowledge/`)

Static markdown files containing WA best practice summaries. Injected into the LLM prompt to ground recommendations in official AWS guidance. No vector DB needed — content fits within context window.

### 5. Report Generator (`src/astra/report/generator.py`)

Transforms LLM JSON output → styled HTML:
- Score circles with color coding
- Per-module breakdown with category bars
- Checklist summary table (✅/❌/⚠️)
- Detailed findings with severity badges
- Top recommendations section

### 6. Interactive Chat (`src/astra/chat.py`)

After assessment, creates a new Strands agent with the full report as system context. Enables multi-turn conversation about findings, remediation steps, and priority planning.

### 7. Interactive Onboarding (`src/astra/interactive.py`)

Guided wizard when user runs `astra` with no flags. Walks through module selection, credential setup, context upload, preflight checks, and model resolution.

### 8. Model Resolution (`src/astra/models.py`)

Tries Bedrock models from most capable to least capable using the Converse API. Returns the best available model without blocking. Recommends upgrading if using a fallback.

### 9. Preflight Checks (`src/astra/preflight.py`)

Validates credentials and read permissions before running the assessment. Provides clear fix instructions if anything is missing.

### 10. Infrastructure Discovery (`src/astra/discovery.py`) + Diagram (`src/astra/diagram.py`)

Scans VPCs, subnets, AZs, EC2, RDS, ELBs, Lambda, S3, Route53 and generates a Mermaid architecture diagram with finding annotations (⚠️ on failed resources).

### 11. CDK Infrastructure (`infra/`)

One-command deployment for automated recurring assessments:
- **Lambda** (15min timeout, 1GB memory) — runs the assessment
- **IAM Role** — ReadOnlyAccess + SecurityAudit + explicit deny on mutations
- **VPC** (private isolated, no internet) — network isolation
- **VPC Endpoints** — Bedrock Runtime, S3, STS, SecurityHub, GuardDuty
- **S3 Bucket** — encrypted, versioned, 365-day lifecycle
- **EventBridge** — weekly cron (disabled by default)

---

## Data Flow & Security

```
┌── Customer AWS Account ────────────────────────────────────────────┐
│                                                                      │
│  ┌──────────────┐         ┌──────────────────────────────────────┐  │
│  │              │         │                                      │  │
│  │  AWS APIs    │◀────────│  ASTRA (read-only)                   │  │
│  │  (read-only) │ boto3   │                                      │  │
│  │              │ describe │  1. Calls AWS APIs                   │  │
│  └──────────────┘ list    │  2. Sends results to Bedrock         │  │
│                    get     │  3. Receives report                  │  │
│                            │  4. Saves to local fs / S3           │  │
│  ┌──────────────┐         │                                      │  │
│  │ Bedrock      │◀───────▶│  (VPC endpoint — no internet)        │  │
│  │ (in-region)  │         │                                      │  │
│  └──────────────┘         └──────────────────────────────────────┘  │
│                                                                      │
│  Data never leaves the account. No internet egress.                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Performance Characteristics

| Phase | Duration | Cost | Can Skip? |
|-------|----------|------|-----------|
| Phase 1: Checks | 10-20s | $0 (API calls only) | No |
| Phase 2: Context | <1s | $0 (file reads) | No |
| Phase 3: LLM | 15-30s | ~$0.03-0.05 | Yes (`--checks-only`) |
| Chat (per question) | 3-10s | ~$0.01-0.02 | Yes (optional) |
| **Total** | **<60s** | **<$0.10** | — |
