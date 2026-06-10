# ASTRA Modules

ASTRA performs assessments across three modules, each addressing a different pillar of cloud maturity. Run one, two, or all three.

---

## Module 1: Security

**Assesses against:** AWS Well-Architected Security Pillar, CIS Benchmarks, AWS Security Best Practices

| Tool | What It Checks | Key Findings |
|------|---------------|--------------|
| `get_security_hub_findings` | Active compliance failures across all AWS services | Prioritised by CRITICAL/HIGH severity, maps to WA controls |
| `get_guardduty_findings` | Active threat detections (recon, crypto-mining, credential compromise) | Real-time threats from GuardDuty's ML-based detection |
| `check_iam_password_policy` | Root MFA, password complexity, user MFA enrollment | Identity is #1 attack vector — catches the most impactful gaps |
| `check_s3_public_access` | Account-level + per-bucket public access blocks | Data exposure is the most common breach cause |
| `check_encryption_at_rest` | S3, EBS, and RDS encryption coverage | Compliance requirement for GDPR, SOC2, ISO 27001 |

### Scoring Categories

| Category | Weight | What's Measured |
|----------|--------|----------------|
| Threat Detection | 20% | GuardDuty enabled + no active threats |
| Identity & Access | 25% | Root MFA, password policy, user MFA, permission boundaries |
| Data Protection | 25% | Encryption, S3 public access, data classification |
| Infrastructure Security | 20% | Security groups, network exposure, patching |
| Logging & Monitoring | 10% | CloudTrail, log integrity, alerting |

---

## Module 2: Resilience

**Assesses against:** AWS Well-Architected Reliability Pillar, AWS Resilience Lifecycle Framework

| Tool | What It Checks | Key Findings |
|------|---------------|--------------|
| `check_multi_az_deployment` | RDS, ElastiCache, ELB, and EC2 AZ distribution | Single-AZ deployments = AZ failure takes down the service |
| `check_backup_coverage` | AWS Backup plans/vaults, RDS automated backups, EBS snapshots | Unprotected resources with no recovery path |
| `check_auto_scaling_configuration` | ASG configs, scaling policies, health checks | Static infrastructure that can't absorb load or self-heal |
| `check_route53_failover` | DNS health checks, failover routing, weighted records | No DNS-level redundancy for regional/AZ failures |
| `detect_single_points_of_failure` | Single NAT GWs, single-instance ASGs, standalone EC2, single-AZ ELBs | Any component whose failure takes down the system |

### Scoring Categories

| Category | Weight | What's Measured |
|----------|--------|----------------|
| High Availability | 25% | Multi-AZ deployments, ELB AZ spread, EC2 distribution |
| Backup & Recovery | 25% | Backup plans, retention periods, recovery points |
| Auto-Scaling | 20% | ASG existence, scaling policies, health check types |
| Fault Tolerance | 20% | SPOF detection, redundancy, self-healing |
| Disaster Recovery | 10% | Cross-region, failover routing, recovery objectives |

---

## Module 3: SaaS / Tenancy

**Assesses against:** AWS SaaS Lens (Well-Architected), AWS SaaS Architecture Patterns, Tenant Isolation Best Practices

| Tool | What It Checks | Key Findings |
|------|---------------|--------------|
| `check_tenant_isolation` | VPC separation, IAM permission boundaries, security group cross-refs | Noisy-neighbour risk, data bleed between tenants |
| `check_resource_tagging` | Tag keys, tenant-identifying tags, untagged resources | Can't attribute costs or audit access without tags |
| `check_control_plane_separation` | IAM role patterns, API GW usage plans, Lambda isolation, Organizations | Control plane/data plane blur = blast radius issues |
| `check_cost_allocation_tags` | Active billing tags, tenant cost attribution | Can't do per-tenant P&L without cost allocation |
| `check_tenant_observability` | Dashboards, alarms, log groups with tenant dimensions | Can't SLA or troubleshoot per-tenant without observability |

### Scoring Categories

| Category | Weight | What's Measured |
|----------|--------|----------------|
| Tenant Isolation | 30% | VPC/account separation, IAM boundaries, SG isolation |
| Resource Tagging | 20% | Consistent tenant tags across resources |
| Control Plane | 20% | Admin vs app role separation, API management |
| Cost Allocation | 15% | Billing tags activated, per-tenant attribution possible |
| Observability | 15% | Tenant-scoped dashboards, alarms, log dimensions |

---

## Running Individual Modules

```bash
# Security only (fastest — ~2 minutes)
python -m astra --module security --html security.html

# Resilience only
python -m astra --module resilience --html resilience.html

# SaaS/Tenancy only
python -m astra --module saas --html saas.html

# All modules (comprehensive — ~5 minutes)
python -m astra --html full-assessment.html
```

---

## Interpreting Scores

| Score Range | Rating | Meaning |
|-------------|--------|---------|
| 80-100 | 🟢 Low Risk | Well-architected, minor improvements possible |
| 60-79 | 🟡 Medium Risk | Gaps exist that should be addressed proactively |
| 40-59 | 🟠 High Risk | Significant gaps — prioritised remediation needed |
| 0-39 | 🔴 Critical Risk | Fundamental issues — immediate action required |

---

## Adding Custom Modules

ASTRA's architecture supports custom modules. To add one:

1. Create `src/astra/tools/your_module.py` with `@tool`-decorated functions
2. Add the module to `_get_tools_for_modules()` in `agent.py`
3. Update the system prompt to include the new module's categories
4. Update the CLI `VALID_MODULES` tuple

Each tool must:
- Use only read-only boto3 calls (`describe_*`, `list_*`, `get_*`)
- Return a structured dictionary
- Handle service-not-enabled gracefully (return empty data, not errors)
- Be idempotent (no side effects)
