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

### What you're building (4 components):

#### A. The Agent (Python + Strands SDK)

This is the brain. A Python application that:
- Receives a command ("assess security" / "assess resilience" / "assess all")
- Calls AWS APIs (read-only) to gather environment state
- Sends findings to the LLM along with best-practice knowledge
- Produces a structured assessment report

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

#### B. The Tools (Python functions the agent can call)

Each tool is a function that queries an AWS service and returns structured data:

```python
# Example tool
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

#### C. The Knowledge Base (documents in S3)

Static documents the agent retrieves from to compare "what is" vs "what should be":
- WA Security Pillar (PDF/markdown)
- WA Reliability Pillar (PDF/markdown)
- SaaS Lens (PDF/markdown)
- SIP v2 checklist (you author this)
- Resilience Lifecycle Framework stages (you author this)

Loaded into Bedrock Knowledge Bases with OpenSearch Serverless for vector search.

#### D. The Infrastructure (CDK)

A CDK stack that deploys everything:
- Lambda function (or ECS Fargate task) running the agent
- IAM role with read-only policies
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
| Agent runtime | Lambda vs ECS Fargate | **Lambda** for MVP (simpler, cheaper, 15-min timeout sufficient) |
| Agent hosting | Self-managed vs AgentCore | **AgentCore** if available in eu-west-1, else self-managed Lambda |
| Knowledge base | Bedrock KB vs in-prompt context | **Bedrock KB** (scalable, updatable without redeploying agent) |
| Report storage | S3 vs email vs dashboard | **S3** (simple, secure, customer controls access) |
| Trigger | Manual vs scheduled vs both | **Both** — manual for first run, EventBridge for recurring |
| Model | Claude Sonnet vs Haiku | **Sonnet** for assessment quality, Haiku for cost-sensitive reruns |

---

## What You Need to Start

1. **AWS account** with Bedrock model access enabled (Claude Sonnet)
2. **Python 3.11+**
3. **Strands SDK**: `pip install strands-agents strands-agents-tools`
4. **AWS CDK**: `npm install -g aws-cdk`
5. **boto3** (comes with Lambda, needed locally for dev)

---

## Next Step

Say the word and we start building — beginning with the project skeleton and the first security tool.
