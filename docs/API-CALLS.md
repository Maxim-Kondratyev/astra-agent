# ASTRA — AWS API Calls Reference

This document lists every AWS API call ASTRA makes. All calls are **read-only** (`Describe*`, `List*`, `Get*`). ASTRA never modifies, creates, or deletes any resource.

## How ASTRA Works

ASTRA operates in two phases:

### Phase 1: Deterministic Checks (no AI)

Each module (Security, Resilience, SaaS) runs ~12 hardcoded Python checks that call AWS APIs via boto3. These are not AI-powered — they're plain read-only API calls that return structured results (PASS/FAIL/WARNING).

All 3 modules run **concurrently** — ~36 checks complete in a few seconds.

### Phase 2: LLM Analysis (optional)

The raw check results + Well-Architected best-practice context are sent to Claude (Bedrock) which:
1. Scores each module (0-100)
2. Writes an executive summary
3. Prioritises findings by risk
4. Generates actionable remediation steps

This phase can be skipped with `--checks-only` (free, fast, CI/CD-friendly).

### Customer Architecture Context (optional)

If you provide architecture documentation (`--context-dir`), the LLM **tailors its recommendations** to your stated goals (RTO/RPO, SLAs, design intent). This does NOT add more API calls — it improves the quality and relevance of the analysis.

---

## Security Module — 12 Checks

| Check ID | What It Verifies | AWS APIs Called |
|----------|-----------------|----------------|
| SEC-01 | Security Hub is enabled | `securityhub:DescribeHub` |
| SEC-02 | GuardDuty is enabled and active | `guardduty:ListDetectors`, `guardduty:GetDetector` |
| SEC-03 | Root account has MFA enabled | `iam:GetAccountSummary` |
| SEC-04 | IAM password policy is strong | `iam:GetAccountPasswordPolicy` |
| SEC-05 | S3 account-level public access block | `s3control:GetPublicAccessBlock`, `sts:GetCallerIdentity` |
| SEC-06 | CloudTrail with multi-region trail | `cloudtrail:DescribeTrails` |
| SEC-07 | VPC Flow Logs on all VPCs | `ec2:DescribeVpcs`, `ec2:DescribeFlowLogs` |
| SEC-08 | No unrestricted security group ingress | `ec2:DescribeSecurityGroups` |
| SEC-09 | IAM Access Analyzer enabled | `accessanalyzer:ListAnalyzers` |
| SEC-10 | EBS default encryption enabled | `ec2:GetEbsEncryptionByDefault` |
| SEC-11 | Secrets Manager rotation enabled | `secretsmanager:ListSecrets` |
| SEC-12 | KMS customer keys auto-rotate | `kms:ListKeys`, `kms:DescribeKey`, `kms:GetKeyRotationStatus` |

**Well-Architected mapping**: SEC 1 (governance), SEC 2 (identity), SEC 3 (permissions), SEC 4 (detection), SEC 5 (network), SEC 7 (data at rest).

---

## Resilience Module — 12 Checks

| Check ID | What It Verifies | AWS APIs Called |
|----------|-----------------|----------------|
| REL-01 | RDS instances are Multi-AZ | `rds:DescribeDBInstances` |
| REL-02 | EC2 instances spread across AZs | `ec2:DescribeInstances` |
| REL-03 | Auto Scaling Groups use ELB health checks | `autoscaling:DescribeAutoScalingGroups` |
| REL-04 | Auto Scaling Groups span multiple AZs | `autoscaling:DescribeAutoScalingGroups` |
| REL-05 | Load balancers span multiple AZs | `elbv2:DescribeLoadBalancers` |
| REL-06 | NAT Gateway redundancy (not single NAT) | `ec2:DescribeNatGateways`, `ec2:DescribeVpcs` |
| REL-07 | AWS Backup plans exist | `backup:ListBackupPlans` |
| REL-08 | RDS backup retention ≥ 7 days | `rds:DescribeDBInstances` |
| REL-09 | EBS volumes have recent snapshots | `ec2:DescribeVolumes`, `ec2:DescribeSnapshots` |
| REL-10 | Route 53 health checks configured | `route53:ListHostedZones`, `route53:ListHealthChecks` |
| REL-11 | ElastiCache replication groups are Multi-AZ | `elasticache:DescribeReplicationGroups` |
| REL-12 | CloudWatch alarms exist (monitoring) | `cloudwatch:DescribeAlarms` |

**Well-Architected mapping**: REL 1 (foundations), REL 2 (change management), REL 3 (failure management).

---

## SaaS / Tenancy Module — 10 Checks

| Check ID | What It Verifies | AWS APIs Called |
|----------|-----------------|----------------|
| SAA-01 | Resource tagging strategy exists | `resourcegroupstaggingapi:GetResources`, `resourcegroupstaggingapi:GetTagKeys` |
| SAA-02 | VPC isolation between tenants | `ec2:DescribeVpcs`, `ec2:DescribeSubnets` |
| SAA-03 | IAM permission boundaries used | `iam:ListPolicies`, `iam:ListRoles` |
| SAA-04 | Separate AWS accounts per tenant/env | `organizations:ListAccounts` (if available) |
| SAA-05 | Resource sharing (RAM) governance | `ram:GetResourceShares` |
| SAA-06 | Per-tenant observability (CW dimensions) | `cloudwatch:ListMetrics` |
| SAA-07 | Cost allocation tags activated | `ce:GetCostAndUsageTags` or `ce:ListCostAllocationTags` |
| SAA-08 | Service Quotas monitoring | `service-quotas:ListServiceQuotas` |
| SAA-09 | Tenant data isolation (DynamoDB/RDS) | `dynamodb:ListTables`, `rds:DescribeDBInstances` |
| SAA-10 | API throttling/rate limiting | `apigateway:GetRestApis`, `apigateway:GetUsagePlans` |

**Well-Architected mapping**: SaaS Lens — Tenant Isolation, Operations, Security, Cost Optimization.

---

## Infrastructure Discovery (Architecture Diagram)

These calls map the account topology for the visual diagram in the report:

| What | AWS APIs Called |
|------|----------------|
| VPCs + Subnets + AZ layout | `ec2:DescribeVpcs`, `ec2:DescribeSubnets` |
| Running instances | `ec2:DescribeInstances` (state=running) |
| NAT Gateways | `ec2:DescribeNatGateways` |
| Databases | `rds:DescribeDBInstances` |
| Load balancers | `elbv2:DescribeLoadBalancers` |
| Lambda functions | `lambda:ListFunctions` |
| S3 buckets | `s3:ListBuckets` |
| DNS zones | `route53:ListHostedZones` |

---

## What ASTRA Does NOT Do

- ❌ Does NOT enumerate every resource in the account (no full inventory)
- ❌ Does NOT read S3 object content (files/data)
- ❌ Does NOT read Secrets Manager secret values
- ❌ Does NOT read CloudWatch log content
- ❌ Does NOT call services irrelevant to WA assessment (SageMaker, GameLift, etc.)
- ❌ Does NOT make any mutating API calls — ever
- ❌ Does NOT send data outside the account (runs locally or in-account Lambda)

---

## IAM Permissions Required

ASTRA works with these AWS managed policies:

- `arn:aws:iam::aws:policy/SecurityAudit` — security-related read access
- `arn:aws:iam::aws:policy/ReadOnlyAccess` — general read access

Plus an **explicit deny** policy that blocks:
- `s3:GetObject` (no reading file content)
- `secretsmanager:GetSecretValue` (no reading secrets)
- All mutating actions (`Create*`, `Delete*`, `Modify*`, `Put*`, `Terminate*`, etc.)

See [SECURITY.md](./SECURITY.md) for the full deny policy.

---

## Estimated API Call Volume

A full assessment (all 3 modules) makes approximately:
- **40-60 API calls** total (varies by account complexity)
- Completes in **3-8 seconds**
- Costs **$0** in API charges (standard AWS API calls are free)
- Bedrock cost (if using LLM): **~$0.10-0.50** per assessment run

---

## FAQ

**Q: Will ASTRA trigger any CloudTrail alerts?**  
A: It will generate read-only CloudTrail events (Describe*/List*/Get*). If you have alerts on unusual API activity, you may want to whitelist the ASTRA role or run it during a maintenance window for the first time.

**Q: Does customer documentation add more API calls?**  
A: No. The 36 checks are always the same. Customer docs only improve the LLM's recommendations — it tailors advice to your stated architecture goals, SLAs, and RTO/RPO targets instead of giving generic best-practice guidance.

**Q: Can I add custom checks?**  
A: Yes — add a function to the relevant module in `src/astra/checklist/` that returns a `CheckResult`. It will automatically be included in the next run.
