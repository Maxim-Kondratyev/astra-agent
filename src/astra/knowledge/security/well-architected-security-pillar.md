# AWS Well-Architected Framework — Security Pillar Best Practices

Source: AWS Well-Architected Framework, Security Pillar Whitepaper (November 2024)

## Design Principles

1. **Implement a strong identity foundation**: Implement least privilege, enforce separation of duties with appropriate authorization. Centralize identity management. Eliminate long-term static credentials.
2. **Maintain traceability**: Monitor, alert, and audit actions in real time. Integrate log and metric collection with automated investigation and response.
3. **Apply security at all layers**: Defence in depth — edge, VPC, load balancing, instance, OS, application, code.
4. **Automate security best practices**: Version-controlled, code-defined security controls. Scale securely and cost-effectively.
5. **Protect data in transit and at rest**: Classify data by sensitivity. Use encryption, tokenization, and access control.
6. **Keep people away from data**: Reduce direct access and manual processing. Minimize mishandling risk.
7. **Prepare for security events**: Incident management policies, simulations, automated detection/investigation/recovery.

## Security Areas

### 1. Security Foundations (SEC 1)

**Question: How do you securely operate your workload?**

Best Practices:
- Separate workloads using accounts (AWS Organizations)
- Secure AWS account root user (MFA, no routine use)
- Keep AWS account contacts up to date
- Use AWS service capabilities to reduce blast radius
- Enable detective controls at organizational level

### 2. Identity and Access Management (SEC 2-3)

**SEC 2: How do you manage authentication for people and machines?**

Best Practices:
- Use strong sign-in mechanisms (MFA required)
- Use temporary credentials (IAM roles, STS)
- Store and use secrets securely (Secrets Manager)
- Rely on a centralized identity provider (IdP)
- Audit and rotate credentials regularly
- Leverage user groups and attributes for access at scale

**SEC 3: How do you manage permissions for people and machines?**

Best Practices:
- Define access requirements (who needs what)
- Grant least privilege access
- Establish emergency access process
- Reduce permissions continuously (IAM Access Analyzer)
- Define permission guardrails for your organization (SCPs)
- Manage access based on lifecycle (JML processes)
- Analyze public and cross-account access
- Share resources securely (RAM, bucket policies)

### 3. Detection (SEC 4)

**SEC 4: How do you detect and investigate security events?**

Best Practices:
- Configure service and application logging (CloudTrail, VPC Flow Logs, DNS logs)
- Analyse logs, findings, and metrics centrally (Security Lake, Security Hub)
- Automate response to events (EventBridge rules, Lambda)
- Implement actionable security events (GuardDuty, Inspector)
- Enable AWS security services in all accounts and regions

Key Services:
- AWS CloudTrail (API audit)
- Amazon GuardDuty (threat detection)
- AWS Security Hub (aggregated findings)
- Amazon Inspector (vulnerability management)
- AWS Config (configuration compliance)
- Amazon Macie (sensitive data discovery)

### 4. Infrastructure Protection (SEC 5-6)

**SEC 5: How do you protect your network resources?**

Best Practices:
- Create network layers (public, private, sensitive subnets)
- Control traffic at all layers (security groups, NACLs, WAF)
- Automate network protection (GuardDuty, Network Firewall)
- Implement inspection and protection (VPC Flow Logs, Traffic Mirroring)
- No direct internet access to resources not requiring it

**SEC 6: How do you protect your compute resources?**

Best Practices:
- Perform vulnerability management (patch, scan, Inspector)
- Reduce attack surface (minimal packages, disable unnecessary services)
- Implement managed services (Lambda, Fargate — reduced OS management)
- Automate compute protection (AMI pipelines, SSM Patch Manager)
- Validate software integrity (code signing, SBOM)

### 5. Data Protection (SEC 7-9)

**SEC 7: How do you classify your data?**

Best Practices:
- Identify the data in your workload (sensitivity levels)
- Define data protection controls (encryption, access policies)
- Define data lifecycle management
- Automate identification and classification (Macie)

**SEC 8: How do you protect your data at rest?**

Best Practices:
- Implement secure key management (KMS, key rotation)
- Enforce encryption at rest (S3 SSE, EBS encryption, RDS encryption)
- Automate data at rest protection
- Enforce access control (bucket policies, resource policies)
- Use mechanisms to keep people away from data

**SEC 9: How do you protect your data in transit?**

Best Practices:
- Implement secure key and certificate management (ACM)
- Enforce encryption in transit (TLS 1.2+, HTTPS only)
- Automate detection of unintended data access
- Authenticate network communications (mTLS, VPN)

### 6. Incident Response (SEC 10)

**SEC 10: How do you anticipate, respond to, and recover from incidents?**

Best Practices:
- Identify key personnel and external resources
- Develop incident management plans (runbooks)
- Prepare forensic capabilities
- Automate containment capability
- Pre-provision access for incident responders
- Pre-deploy tools (forensic AMIs, log analysis)
- Run game days (simulate incidents)

### 7. Application Security (SEC 11)

**SEC 11: How do you incorporate and validate the security properties of applications throughout the design, development, and deployment lifecycle?**

Best Practices:
- Train for application security (secure coding)
- Automate testing throughout development lifecycle (SAST, DAST)
- Perform regular penetration testing
- Conduct manual code reviews for critical logic
- Centralize services for packages and dependencies (prevent supply chain attacks)
- Deploy software programmatically (no human access to production)
- Regularly assess security properties of pipelines

## Critical Security Controls Checklist

| # | Control | Priority |
|---|---------|----------|
| 1 | Root account MFA enabled | CRITICAL |
| 2 | No root account access keys | CRITICAL |
| 3 | All IAM users have MFA | HIGH |
| 4 | No long-term access keys (use roles) | HIGH |
| 5 | CloudTrail enabled in all regions | HIGH |
| 6 | GuardDuty enabled | HIGH |
| 7 | Security Hub enabled with standards | HIGH |
| 8 | S3 Block Public Access (account level) | HIGH |
| 9 | EBS default encryption enabled | MEDIUM |
| 10 | VPC Flow Logs enabled | MEDIUM |
| 11 | AWS Config enabled | MEDIUM |
| 12 | Secrets Manager for credentials | MEDIUM |
| 13 | Inspector enabled for vulnerability scanning | MEDIUM |
| 14 | No security groups with 0.0.0.0/0 on SSH/RDP | HIGH |
| 15 | IAM password policy (14+ chars, complexity) | MEDIUM |
| 16 | SCPs for guardrails in multi-account | HIGH |
| 17 | Encryption in transit (TLS 1.2+) | MEDIUM |
| 18 | VPC endpoints for AWS service access | MEDIUM |
| 19 | WAF for public-facing applications | MEDIUM |
| 20 | Regular access reviews (IAM Access Analyzer) | MEDIUM |
