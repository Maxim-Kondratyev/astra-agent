# ASTRA Modules & Checks

ASTRA runs **34 prebuilt checks** across three modules. Each check maps to an official AWS Well-Architected Framework best practice.

---

## 🛡️ Security Module (12 checks)

Based on the [Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/framework/a-security.html).

| ID | Check | WA Reference | What It Tests |
|----|-------|--------------|---------------|
| SEC-01 | Security Hub enabled | SEC 4 | Centralized security findings aggregation |
| SEC-02 | GuardDuty enabled | SEC 4 | Continuous threat detection |
| SEC-03 | Root account MFA | SEC 2 | Root account protection |
| SEC-04 | IAM password policy | SEC 2 | Password strength requirements |
| SEC-05 | S3 public access block | SEC 7 | Account-level S3 public access prevention |
| SEC-06 | CloudTrail enabled | SEC 4 | Multi-region audit logging |
| SEC-07 | VPC flow logs | SEC 5 | Network traffic monitoring |
| SEC-08 | Security groups | SEC 5 | Unrestricted inbound access (0.0.0.0/0) |
| SEC-09 | IAM Access Analyzer | SEC 3 | External access detection |
| SEC-10 | EBS default encryption | SEC 7 | Storage encryption by default |
| SEC-11 | Secrets rotation | SEC 2 | Automated credential rotation |
| SEC-12 | KMS key rotation | SEC 7 | Encryption key rotation |

---

## 🏗️ Resilience Module (12 checks)

Based on the [Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/framework/a-reliability.html).

| ID | Check | WA Reference | What It Tests |
|----|-------|--------------|---------------|
| REL-01 | RDS Multi-AZ | REL 10 | Database high availability |
| REL-02 | EC2 AZ distribution | REL 10 | Compute spread across AZs |
| REL-03 | ASG health check type | REL 6 | ELB vs EC2 health detection |
| REL-04 | ASG multi-AZ | REL 10 | Auto Scaling across AZs |
| REL-05 | ELB multi-AZ | REL 10 | Load balancer AZ coverage |
| REL-06 | AWS Backup plans | REL 9 | Automated backup existence |
| REL-07 | RDS backup retention | REL 9 | Backup retention >= 7 days |
| REL-08 | NAT Gateway redundancy | REL 10 | NAT per AZ (avoid SPOF) |
| REL-09 | EBS snapshot coverage | REL 9 | Volume backup coverage |
| REL-10 | Route 53 health checks | REL 11 | DNS failover readiness |
| REL-11 | ElastiCache Multi-AZ | REL 10 | Cache high availability |
| REL-12 | CloudWatch alarms | REL 6 | Monitoring with actions |

---

## 🏢 SaaS Module (10 checks)

Based on the [Well-Architected SaaS Lens](https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/saas-lens.html).

| ID | Check | WA Reference | What It Tests |
|----|-------|--------------|---------------|
| SAS-01 | Tenant tagging | Resource allocation | Tenant identifier on resources |
| SAS-02 | Cost allocation tags | Cost attribution | Per-tenant billing tags active |
| SAS-03 | Permission boundaries | Tenant isolation | IAM boundaries on app roles |
| SAS-04 | Resource isolation | Tenant isolation | VPC/account-level separation |
| SAS-05 | Per-tenant monitoring | Tenant activity | Tenant-scoped CloudWatch dimensions |
| SAS-06 | API throttling | Noisy neighbour | Usage plans with rate limits |
| SAS-07 | Control plane separation | Control/data plane | Admin vs app role separation |
| SAS-08 | Cross-tenant access | Tenant isolation | Wildcard S3 bucket policies |
| SAS-09 | Onboarding automation | Governance | IaC for tenant provisioning |
| SAS-10 | Noisy neighbour detection | Noisy neighbour | Lambda concurrency limits |

---

## Running Individual Modules

```bash
# Single module
astra -m security --html security.html

# Multiple modules
astra -m security -m resilience --html report.html

# All modules (default)
astra --html full-report.html
```

## Check Results

Each check returns one of:

| Status | Meaning |
|--------|---------|
| ✅ PASS | Compliant with best practice |
| ❌ FAIL | Non-compliant — action required |
| ⚠️ WARNING | Partially compliant — improvement recommended |
| 🚫 ERROR | Could not evaluate (service not enabled or access denied) |
