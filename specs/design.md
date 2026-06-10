# ASTRA — Design: From Idea to Deployable Agent

## The Process Overview

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│  SPEC   │───▶│  BUILD  │───▶│  TEST   │───▶│ PACKAGE │───▶│ DEPLOY  │
│         │    │         │    │         │    │         │    │         │
│Requirements│ │Agent +  │    │Your own │    │CDK stack│    │Customer │
│& Design │    │Tools +  │    │AWS acct │    │+ KB     │    │account  │
│         │    │KB       │    │         │    │         │    │         │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
  (we're here)
```

---

## Step 1: SPEC (Done ✓)

What we just did — define requirements, modules, architecture, and success criteria.

---

## Step 2: BUILD

### What you're building (5 components):

#### A. The Agent (Python + Strands SDK)

This is the brain. A Python application that:
- Receives a command ("assess security" / "assess resilience" / "assess all")
- Calls AWS APIs (read-only) via AgentCore Gateway tools
- Sends findings to the LLM along with best-practice knowledge
- Produces a structured assessment report
- Stores findings in AgentCore Memory for trend tracking

```python
# Simplified concept — what the agent looks like
from strands import Agent
from strands.models import BedrockModel
from astra.tools import security_tools, resilience_tools, saas_tools

agent = Agent(
    model=BedrockModel(model_id="anthropic.claude-sonnet..."),
    tools=[*security_tools, *resilience_tools, *saas_tools],
    system_prompt="You are ASTRA, an autonomous cloud assessor..."
)

result = agent("Assess the security posture of this AWS account")
```

#### B. The Tools (MCP-compatible via AgentCore Gateway)

Each tool is registered in AgentCore Gateway as an MCP endpoint. The agent discovers and calls them via semantic selection:

```python
# Example tool — registered in Gateway
@tool
def get_security_hub_findings(severity: str = "HIGH") -> dict:
    """Retrieve Security Hub findings filtered by severity."""
    client = boto3.client('securityhub')
    # ... query and return findings
```

Tools are grouped by module:
- `security_tools`: Security Hub, GuardDuty, IAM Analyzer, Config rules
- `resilience_tools`: Resilience Hub, EC2 (AZ spread), RDS, ELB, Route53
- `saas_tools`: Resource tagging, VPC isolation, IAM boundaries

Gateway provides:
- Semantic tool selection (agent picks the right tool based on context)
- Auth handling (cross-account credentials)
- Composition (multiple tools via single MCP endpoint)

#### C. The Knowledge Base (documents in S3)

Static documents the agent retrieves from to compare "what is" vs "what should be":
- WA Security Pillar (PDF/markdown)
- WA Reliability Pillar (PDF/markdown)
- SaaS Lens (PDF/markdown)
- SIP v2 checklist (you author this)
- Resilience Lifecycle Framework stages (you author this)
- Customer-uploaded architecture docs (optional)

Loaded into Bedrock Knowledge Bases with OpenSearch Serverless for vector search.

#### D. The Policy (Cedar — read-only enforcement)

Cedar policy enforced at AgentCore platform level:

```cedar
// ASTRA can only perform read operations
permit(
  principal == Agent::"astra",
  action in [Action::"Describe", Action::"List", Action::"Get"],
  resource
);

// Explicitly deny any write/modify/delete
forbid(
  principal == Agent::"astra",
  action in [Action::"Create", Action::"Delete", Action::"Modify", Action::"Put"],
  resource
);
```

This guarantees read-only even if IAM is misconfigured — provable to any CISO.

#### E. The Infrastructure (CDK)

A CDK stack that deploys everything:
- AgentCore Runtime workload (runs the agent)
- AgentCore Gateway (MCP tools endpoint)
- AgentCore Policy (Cedar read-only rules)
- AgentCore Observability (tracing)
- IAM role with read-only policies (SecurityAudit + ReadOnlyAccess)
- S3 bucket for knowledge base + reports
- Bedrock Knowledge Base resource
- VPC endpoints (Bedrock, S3) — no internet needed
- EventBridge rule (optional: scheduled runs)

---

## Step 3: TEST

1. Deploy to your own AWS account (or a sandbox)
2. Run each module independently
3. Validate findings against what you know is true
4. Check for false positives/negatives
5. Verify cost per run (should be < $5)
6. Verify execution time (should be < 15 min per module)

---

## Step 4: PACKAGE

Make it deployable by anyone:
- CDK stack with parameters (region, modules to enable, schedule)
- Knowledge base content bundled as assets
- README with deployment instructions
- One-command deployment: `cdk deploy --parameters Modules=security,resilience`

---

## Step 5: DEPLOY (to customer)

1. Customer creates a CloudFormation/CDK deployment (you provide the stack)
2. Stack creates read-only role + agent infrastructure
3. Customer triggers first assessment
4. You review results together
5. Prioritise remediation
6. Schedule recurring runs

---

## Development Sequence (What to build first)

```
Week 1:  Project setup + 1 tool working (Security Hub query)
         └── Agent can call Security Hub and summarise findings

Week 2:  Add 4 more security tools + knowledge base
         └── Agent produces a full security assessment report

Week 3:  CDK stack + test deployment
         └── Deployable to any account with one command

Week 4:  Module 1 (Resilience) tools
         └── Two modules working

Week 5:  Module 3 (SaaS) tools + final report format
         └── All three modules, HTML report

Week 6:  Polish + first customer deployment
         └── JetBrains or Dynatrace
```

---

## Project Structure

```
astra/
├── specs/
│   ├── requirements.md          ← you are here
│   └── design.md                ← this file
├── src/
│   ├── astra/
│   │   ├── __init__.py
│   │   ├── agent.py             ← main agent definition
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── security.py      ← Security Hub, GuardDuty, IAM tools
│   │   │   ├── resilience.py    ← Resilience Hub, Multi-AZ, backup tools
│   │   │   └── saas.py          ← Tenancy, isolation, tagging tools
│   │   ├── knowledge/
│   │   │   ├── security/        ← WA Security Pillar docs
│   │   │   ├── resilience/      ← WA Reliability Pillar docs
│   │   │   └── saas/            ← SaaS Lens docs
│   │   └── report/
│   │       ├── generator.py     ← builds HTML/JSON report
│   │       └── templates/       ← HTML report templates
│   └── tests/
│       ├── test_security_tools.py
│       ├── test_resilience_tools.py
│       └── test_agent.py
├── infra/
│   ├── app.py                   ← CDK app entry point
│   ├── stacks/
│   │   ├── astra_stack.py       ← main infrastructure stack
│   │   └── knowledge_base_stack.py
│   └── cdk.json
├── pyproject.toml
└── README.md
```

---

## Key Decisions to Make Before Coding

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Agent runtime | Lambda vs AgentCore Runtime | **AgentCore Runtime** (no timeout, session isolation, serverless) |
| Tool layer | Direct boto3 vs AgentCore Gateway | **Gateway** (MCP-compatible, semantic selection, auth handling) |
| Read-only enforcement | IAM only vs IAM + Cedar | **IAM + Cedar Policy** (provable, auditable, CISO-friendly) |
| Knowledge base | In-prompt context vs Bedrock KB | **Bedrock KB** (scalable, updatable, supports customer docs) |
| Report storage | S3 vs email vs dashboard | **S3** (simple, secure, customer controls access) |
| Trigger | Manual vs scheduled vs both | **Both** — manual for first run, EventBridge for recurring |
| Model | Claude Sonnet vs Haiku | **Sonnet** for assessment quality, Haiku for cost-sensitive reruns |
| Observability | CloudWatch only vs AgentCore Observability | **AgentCore Observability** (full reasoning trace, OTEL-compatible) |
| Memory | None vs AgentCore Memory | **Memory** in Phase 2 (enables trend tracking across runs) |

---

## What You Need to Start

1. **AWS account** with Bedrock model access enabled (Claude Sonnet) + AgentCore access
2. **Python 3.11+**
3. **Strands SDK**: `pip install strands-agents strands-agents-tools`
4. **AgentCore CLI**: [Getting started guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html)
5. **AWS CDK**: `npm install -g aws-cdk`
6. **boto3** (comes with Lambda, needed locally for dev)

---

## Next Step

Say the word and we start building — beginning with the project skeleton and the first security tool.
