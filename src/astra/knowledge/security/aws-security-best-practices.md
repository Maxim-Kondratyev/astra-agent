# AWS Security Best Practices (Beyond WA Framework)

Source: AWS Security Reference Architecture, AWS Security Best Practices whitepaper

## Identity and Access Management

### Root Account
- Enable MFA (hardware key preferred)
- Never use root for daily operations
- Remove all root access keys
- Set up alerts for root account usage

### IAM Hygiene
- Enforce MFA for all human users
- Use IAM Identity Center (SSO) over IAM users
- Apply least privilege — start with zero permissions, add as needed
- Use permission boundaries for delegated admin scenarios
- Regularly review unused roles and policies (IAM Access Analyzer)

### Credential Management
- Rotate access keys every 90 days
- Use IAM roles (not long-lived keys) for applications
- Store secrets in Secrets Manager with automatic rotation
- Never hardcode credentials in source code

## Detection and Monitoring

### Minimum Viable Security Monitoring
- CloudTrail enabled in ALL regions (multi-region trail)
- GuardDuty enabled in ALL regions
- Security Hub enabled (aggregates findings)
- VPC Flow Logs on all non-default VPCs
- S3 access logging for sensitive buckets

### Response
- CloudWatch alarms on critical security metrics
- SNS notifications routed to security team
- Automated remediation for common findings (e.g., auto-close public S3)
- Incident response runbook documented and tested

## Data Protection

### Encryption at Rest
- EBS: enable default encryption (account-level setting)
- S3: SSE-S3 or SSE-KMS on all buckets
- RDS: encryption enabled at creation (cannot be added later)
- DynamoDB: encryption enabled by default
- KMS: enable automatic key rotation for customer-managed keys

### Encryption in Transit
- TLS 1.2+ for all external connections
- ALB/NLB with HTTPS listeners
- RDS: require SSL connections
- S3: enforce ssl-only bucket policy

## Network Security

### Defence in Depth
- Account-level S3 public access block (all 4 settings enabled)
- Security groups: deny-all-by-default, allow only required ports
- NACLs for subnet-level controls
- No 0.0.0.0/0 inbound except ports 80/443 on public ALBs
- Private subnets for databases, internal services

### Common Violations
- SSH (port 22) open to 0.0.0.0/0 → use Systems Manager Session Manager instead
- RDP (port 3389) open to internet → use Fleet Manager or bastion in private subnet
- Database ports (3306, 5432, 1433) exposed → always private subnet, no public IP

## Prioritisation Framework

When multiple security issues exist, prioritise by:

1. **CRITICAL:** Identity compromise risk (root without MFA, leaked keys)
2. **HIGH:** Network exposure (open security groups, public databases)
3. **HIGH:** Missing detection (no GuardDuty, no CloudTrail)
4. **MEDIUM:** Encryption gaps (unencrypted EBS, S3 without encryption)
5. **LOW:** Operational hygiene (key rotation, password policy strength)
