# Getting Started with ASTRA

## TL;DR

```bash
pip install -e .    # Install
astra               # Run (guides you through everything)
```

ASTRA needs: **Python 3.11+** · **AWS read-only credentials** · **Bedrock model access (Opus 4.8)**

Takes 5 minutes to set up, 60 seconds to run, costs < $0.10 per assessment.

---

## How ASTRA Works (Transparency)

When you run `astra`, here's exactly what happens:

### Phase 1: Infrastructure Checks (10-20 seconds, $0.00)

ASTRA calls **read-only AWS APIs** to inspect your environment. These are the same APIs you'd use if you ran `aws ec2 describe-instances` or `aws rds describe-db-instances` manually — just automated across 34 checks.

**What it reads:**
- EC2: instances, security groups, VPCs, subnets, NAT gateways, EBS volumes
- RDS: database instances, backup configuration
- IAM: password policy, roles, permission boundaries, access analyzers
- Security services: Security Hub, GuardDuty, CloudTrail, KMS keys, Secrets Manager
- Networking: load balancers, Route 53 health checks, VPC flow logs
- Storage: S3 bucket configurations and policies
- Compute: Lambda functions, Auto Scaling groups
- Monitoring: CloudWatch alarms and dashboards
- Backup: AWS Backup plans and vaults
- Tags: resource tagging and cost allocation tags

**What it does NOT read:** S3 object contents (explicitly denied via IAM), Secrets Manager secret values (explicitly denied), application data, logs content, or any customer data. See [SECURITY.md](SECURITY.md) for the full deny policy.

### Phase 2: AI Analysis (15-30 seconds, ~$0.04)

The structured check results (PASS/FAIL/WARNING for each of 34 checks) are sent to **Amazon Bedrock** (Claude Opus 4.8) along with:
- Well-Architected Framework best practices (built-in knowledge base)
- Your architecture documents (if you provided them via `--context-dir`)

The AI produces:
- An overall score (0-100) and risk level
- Executive summary connecting findings across modules
- Priority-ordered recommendations with risk consequences
- Per-module scoring

**Where your data goes:** To Amazon Bedrock in your configured AWS region. Data does not leave AWS. No data is stored after the response is generated.

### Phase 3: Report & Chat (instant)

The AI's JSON output is transformed into a styled HTML report with:
- Score visualisation
- Architecture diagram (from infrastructure discovery in Phase 1)
- Checklist summary table
- Detailed findings with affected resources
- Top recommendations with "risk if not addressed"

If you choose chat mode, a new conversation begins with the full report as context — allowing you to ask specific questions about remediation.

### What ASTRA References

All checks map to official AWS Well-Architected Framework best practices:

| Reference | Source |
|-----------|--------|
| SEC 1–9 | [Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/framework/a-security.html) |
| REL 6–13 | [Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/framework/a-reliability.html) |
| SaaS Lens | [Well-Architected SaaS Lens](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/saas-lens.html) |

Each finding in the report includes the specific WA question it maps to, so you can trace recommendations back to AWS official guidance.

---

This guide covers everything you need before running your first assessment.

---

## What You'll Need (5 minutes setup)

| Requirement | What It Is | How to Get It |
|-------------|-----------|---------------|
| Python 3.11+ | Runs the agent | [python.org/downloads](https://www.python.org/downloads/) |
| AWS CLI | Configures credentials | `pip install awscli` or [install guide](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) |
| AWS Credentials | Read-only access to your account | See below |
| Bedrock Model Access | Powers the AI report (optional) | See below |

---

## Step 1: AWS Credentials

ASTRA needs **read-only** access to your AWS account. Choose the method your team uses:

### Option A: AWS SSO (most common in enterprises)

```bash
aws configure sso
# Enter your SSO portal URL, region, and choose a role
aws sso login
```

### Option B: IAM Access Keys

```bash
aws configure
# Enter your Access Key ID and Secret Access Key
# Default region: us-east-1 (or your preferred region)
```

### Option C: Temporary Credentials (from your admin)

```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_SESSION_TOKEN=FwoGZXIvY...    # if using temp credentials
export AWS_DEFAULT_REGION=us-east-1
```

### Verify it works:

```bash
aws sts get-caller-identity
```

You should see:
```json
{
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-name"
}
```

---

## Step 2: Required IAM Permissions

Your IAM user or role needs these policies:

| Policy | What It Allows |
|--------|---------------|
| `SecurityAudit` | Read security configurations (GuardDuty, Security Hub, IAM) |
| `ReadOnlyAccess` | Read all other resources (EC2, RDS, S3, Lambda, etc.) |
| Bedrock invoke (inline) | Call Claude model for report generation and chat |

### How to attach (if you have IAM admin access):

```bash
# Replace YOUR_USER_NAME with your IAM user name

# Read-only policies
aws iam attach-user-policy --user-name YOUR_USER_NAME \
  --policy-arn arn:aws:iam::aws:policy/SecurityAudit

aws iam attach-user-policy --user-name YOUR_USER_NAME \
  --policy-arn arn:aws:iam::aws:policy/ReadOnlyAccess

# Bedrock invoke permission (for AI report generation)
aws iam put-user-policy --user-name YOUR_USER_NAME \
  --policy-name BedrockInvoke \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
      "Resource": "arn:aws:bedrock:*::foundation-model/anthropic.*"
    }]
  }'
```

### Or ask your admin to:
> "Please attach `SecurityAudit` and `ReadOnlyAccess` managed policies, plus `bedrock:InvokeModel` permission for Anthropic models. ASTRA only reads infrastructure and calls Bedrock for AI analysis — it never modifies any resources."

### Why Bedrock access?
ASTRA is **read-only for your infrastructure** — it never creates, modifies, or deletes any AWS resource. However, it calls Amazon Bedrock (Claude) to:
- Generate the scored assessment report
- Power the interactive chat about findings

If you don't want to grant Bedrock access, use `astra --checks-only` for raw results without AI analysis.

---

## Step 3: Enable Bedrock Model Access (for AI reports)

ASTRA uses Claude (e.g. Opus 4.8 or latest available) to generate the analysis report. This is optional — you can run `--checks-only` without it.

### How to enable:

1. Go to **AWS Console** → **Amazon Bedrock** → **Model access** (region: us-east-1)
2. Click **Manage model access**
3. Enable **Anthropic Claude models** (Opus 4.8 recommended)
4. Click **Save changes**

> ⏭️ **Skip this step?** Use `astra --checks-only` to get results without AI analysis (free, instant).

---

## Step 4: Install ASTRA

```bash
git clone https://github.com/Maxim-Kondratyev/astra-agent.git
cd astra-agent
pip install -e .
```

---

## Step 5: Run

```bash
astra
```

That's it. The agent will guide you from here.

---

## Quick Verification Checklist

Before running, verify these work:

```bash
# ✅ Python installed
python3 --version            # Should be 3.11 or higher

# ✅ AWS credentials configured
aws sts get-caller-identity  # Should show your account ID

# ✅ Read access works
aws ec2 describe-vpcs        # Should return your VPCs (or empty list)

# ✅ Bedrock access (optional — only if you want AI reports)
aws bedrock list-foundation-models --region us-east-1 | head -5
```

---

## Common Issues

| Problem | Cause | Fix |
|---------|-------|-----|
| "Unable to locate credentials" | No AWS credentials configured | Run `aws configure` or `aws sso login` |
| "Access Denied" on EC2/RDS calls | Missing ReadOnlyAccess policy | Ask admin to attach the policy |
| "AccessDeniedException" on Bedrock | Model not enabled or SCP blocks it | Enable model in console, or use `--checks-only` |
| "Could not connect to endpoint" | Wrong region or network issue | Check `AWS_DEFAULT_REGION` is set |

---

## What ASTRA Does NOT Need

- ❌ **No write access** — never creates, modifies, or deletes anything
- ❌ **No admin access** — only read policies required
- ❌ **No EC2 instance** — runs from your laptop
- ❌ **No internet-facing resources** — works in any account configuration
- ❌ **No secrets or passwords** — uses standard AWS credential chain
