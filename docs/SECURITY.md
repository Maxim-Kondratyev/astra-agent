# ASTRA Security Model

## Core Principle: Read-Only Only

ASTRA is designed for **zero trust deployment** into customer AWS accounts. The agent cannot modify, create, or delete any resource — this is enforced at multiple layers.

---

## Defence in Depth

ASTRA uses **four layers** of read-only enforcement. Even if one layer fails, the others prevent any modification.

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: IAM Managed Policies                        │
│   SecurityAudit + ReadOnlyAccess                     │
│   (No write permissions granted)                     │
├─────────────────────────────────────────────────────┤
│ Layer 2: Explicit IAM DENY                           │
│   Blocks: Create*, Delete*, Modify*, Update*,        │
│           Terminate*, Put*, Attach*, Detach*          │
│   on ec2, s3, iam, rds, lambda (all resources)       │
├─────────────────────────────────────────────────────┤
│ Layer 3: Code-Level Enforcement                      │
│   Every tool only uses Describe*, List*, Get* APIs   │
│   No boto3 write calls exist in the codebase         │
├─────────────────────────────────────────────────────┤
│ Layer 4: Network Isolation                           │
│   VPC endpoints only (Bedrock, S3)                   │
│   No internet egress — data cannot leave the account │
└─────────────────────────────────────────────────────┘
```

---

## Layer 1: IAM Managed Policies

The ASTRA Lambda role uses two AWS-managed policies:

| Policy | Purpose | Grants |
|--------|---------|--------|
| `SecurityAudit` | Access to security services | Read-only access to Security Hub, GuardDuty, IAM, Config, CloudTrail |
| `ReadOnlyAccess` | General read access | Describe/List/Get on all AWS services |

Neither policy grants any `Create`, `Put`, `Delete`, `Modify`, or `Update` permissions.

---

## Layer 2: Explicit DENY Policy

Even with read-only managed policies, ASTRA adds an **explicit IAM DENY** as a safety net:

```json
{
  "Sid": "DenyAllMutatingActions",
  "Effect": "Deny",
  "Action": [
    "ec2:Terminate*", "ec2:Delete*", "ec2:Modify*", "ec2:Create*",
    "s3:Delete*", "s3:PutBucketPolicy",
    "iam:Create*", "iam:Delete*", "iam:Update*", "iam:Attach*", "iam:Detach*", "iam:Put*",
    "rds:Delete*", "rds:Modify*",
    "lambda:Delete*", "lambda:Update*", "lambda:Create*"
  ],
  "Resource": "*"
}
```

**Why this matters:** IAM DENY always wins over ALLOW. Even if a misconfiguration somewhere grants write access, the explicit DENY blocks it.

---

## Layer 3: Code-Level Enforcement

Every tool in the ASTRA codebase uses only these boto3 call patterns:

| Allowed | Examples |
|---------|----------|
| `describe_*` | `describe_instances`, `describe_db_instances` |
| `list_*` | `list_buckets`, `list_findings`, `list_detectors` |
| `get_*` | `get_findings`, `get_bucket_encryption`, `get_caller_identity` |

**No tool contains** any of: `create_*`, `put_*`, `delete_*`, `modify_*`, `update_*`, `terminate_*`, `run_*`, `start_*`, `stop_*`.

You can verify this yourself:
```bash
grep -rn "create_\|put_\|delete_\|modify_\|update_\|terminate_\|run_instances\|start_\|stop_" src/astra/tools/
# Should return zero results (only s3.put_object for saving reports to the ASTRA-owned bucket)
```

---

## Layer 4: Network Isolation

When deployed with VPC endpoints:

- **No internet gateway** — Lambda runs in private subnets
- **VPC Endpoint for Bedrock** — model calls stay on AWS backbone
- **VPC Endpoint for S3** — report storage stays on AWS backbone
- **No data exfiltration** — even if the model were compromised, there's no path to send data externally

---

## What ASTRA Reads (and Why)

| Service | What's Read | Why |
|---------|-------------|-----|
| Security Hub | Active findings | Assess compliance posture |
| GuardDuty | Active detections | Identify active threats |
| IAM | Password policy, users, roles | Verify identity security |
| S3 | Bucket configs, encryption | Check data protection |
| EC2 | Instances, volumes, security groups | Assess infrastructure security + HA |
| RDS | Instances, backup settings | Check database resilience |
| ELB | Load balancers, AZ config | Verify high availability |
| Route 53 | Health checks, failover records | Assess DNS resilience |
| Auto Scaling | Groups, policies | Check scaling readiness |
| AWS Backup | Plans, vaults, protected resources | Verify backup strategy |
| CloudWatch | Alarms, dashboards | Assess observability |
| Cost Explorer | Cost allocation tags | Verify tenant billing |
| Resource Groups | Tag keys, tagged resources | Assess tagging strategy |
| Organizations | Account structure | Check account isolation |

---

## What ASTRA Writes

Only one write operation exists in the entire system:

| What | Where | Why |
|------|-------|-----|
| Assessment reports (HTML + JSON) | ASTRA's own S3 bucket | Store the output — this is the only bucket the role can write to |

This write is scoped to a single, ASTRA-created S3 bucket. The role cannot write to any other bucket.

---

## Threat Model

| Threat | Mitigation |
|--------|-----------|
| Agent modifies resources | 4 layers of read-only enforcement |
| Model hallucinates dangerous tool calls | No write tools exist in the tool registry |
| Data exfiltration via Bedrock | VPC endpoints — no internet path |
| Report data exposed | S3 bucket: encrypted, SSL-enforced, BlockPublicAccess |
| Credential theft | STS temporary credentials, Lambda execution role (not long-term keys) |
| Supply chain attack (dependencies) | Minimal dependencies: strands-agents, boto3 (AWS-owned) |

---

## Compliance Positioning

When presenting to a CISO:

> "ASTRA uses read-only IAM policies with an explicit DENY on all mutations, runs in your VPC with no internet access, and stores results only in your encrypted S3 bucket. No data leaves your account. You can verify the read-only guarantee by inspecting the IAM policy and the open-source tool code."

---

## Verification Commands

Customers can verify the security model themselves:

```bash
# Check the IAM role policies
aws iam get-role --role-name AstraStack-AstraRole-XXXXX
aws iam list-attached-role-policies --role-name AstraStack-AstraRole-XXXXX
aws iam get-role-policy --role-name AstraStack-AstraRole-XXXXX --policy-name DenyAllMutatingActions

# Verify no write calls in the code
grep -rn "create_\|put_\|delete_\|modify_\|terminate_" src/astra/tools/

# Check S3 bucket configuration
aws s3api get-bucket-encryption --bucket astra-reports-ACCOUNT_ID
aws s3api get-public-access-block --bucket astra-reports-ACCOUNT_ID
```
