# AWS Well-Architected Framework — Security Pillar

Source: https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html

The Security pillar encompasses the ability to protect data, systems, and assets
to take advantage of cloud technologies to improve your security.

## Best Practice Areas

1. Security Foundations (SEC 1)
2. Identity and Access Management (SEC 2–3)
3. Detection (SEC 4)
4. Infrastructure Protection (SEC 5–6)
5. Data Protection (SEC 7–8)
6. Incident Response (SEC 10)
7. Application Security (SEC 11)

---

## Security Foundations

### SEC 1 — How do you securely operate your workload?

Operate workloads securely by using AWS Organizations, multi-account strategy,
and establishing security governance.

Best practices:
- SEC01-BP01: Separate workloads using accounts
- SEC01-BP02: Secure AWS account root user and properties
- SEC01-BP03: Identify and validate control objectives
- SEC01-BP04: Stay up to date with security threats and recommendations
- SEC01-BP05: Reduce security management scope (use managed services)
- SEC01-BP06: Automate testing and validation of security controls in pipelines
- SEC01-BP07: Identify threats and prioritize mitigations using a threat model
- SEC01-BP08: Evaluate and implement new security services and features regularly

---

## Identity and Access Management

### SEC 2 — How do you manage identities for people and machines?

Establish and manage identities with defined lifecycle (creation, use, deactivation).

Best practices:
- SEC02-BP01: Use strong sign-in mechanisms (MFA, password policies)
- SEC02-BP02: Use temporary credentials (roles, not long-lived keys)
- SEC02-BP03: Store and use secrets securely (Secrets Manager, rotation)
- SEC02-BP04: Rely on a centralized identity provider (IAM Identity Center, SSO)
- SEC02-BP05: Audit and rotate credentials regularly
- SEC02-BP06: Leverage user groups and attributes for access at scale

### SEC 3 — How do you manage permissions for people and machines?

Grant least-privilege access, establish guardrails, and reduce permissions continuously.

Best practices:
- SEC03-BP01: Define access requirements
- SEC03-BP02: Grant least privilege access
- SEC03-BP03: Establish emergency access process
- SEC03-BP04: Reduce permissions continuously (Access Analyzer)
- SEC03-BP05: Define permission guardrails for your organization (SCPs)
- SEC03-BP06: Manage access based on lifecycle (joiners/movers/leavers)
- SEC03-BP07: Analyze public and cross-account access
- SEC03-BP08: Share resources securely within your organization

---

## Detection

### SEC 4 — How do you detect and investigate security events?

Capture, centralize, and analyse logs. Automate alerting and response.

Best practices:
- SEC04-BP01: Configure service and application logging (CloudTrail, VPC Flow Logs)
- SEC04-BP02: Analyse logs, findings, and metrics centrally (Security Hub)
- SEC04-BP03: Automate response to events (EventBridge + Lambda)
- SEC04-BP04: Implement actionable security events (GuardDuty, detective controls)

---

## Infrastructure Protection

### SEC 5 — How do you protect your network resources?

Apply defence in depth at network layer.

Best practices:
- SEC05-BP01: Create network layers (public/private subnets)
- SEC05-BP02: Control traffic at all layers (security groups, NACLs, WAF)
- SEC05-BP03: Automate network protection (AWS Network Firewall, Shield)
- SEC05-BP04: Implement inspection and protection (flow logs, traffic mirroring)

### SEC 6 — How do you protect your compute resources?

Reduce attack surface of compute, manage vulnerabilities, automate patching.

Best practices:
- SEC06-BP01: Perform vulnerability management
- SEC06-BP02: Reduce attack surface (remove unnecessary packages, ports)
- SEC06-BP03: Implement managed services (Lambda, Fargate reduce OS management)
- SEC06-BP04: Automate compute protection (Inspector, SSM Patch Manager)
- SEC06-BP05: Validate software integrity (code signing, verified images)

---

## Data Protection

### SEC 7 — How do you protect your data at rest?

Encrypt data at rest, manage keys, and control access to data.

Best practices:
- SEC07-BP01: Understand your data classification and protection requirements
- SEC07-BP02: Apply data protection controls based on data sensitivity
- SEC07-BP03: Automate data at rest protection (default encryption)
- SEC07-BP04: Enforce access control (S3 policies, KMS key policies)
- SEC07-BP05: Use mechanisms to keep people away from data (no direct access)

### SEC 8 — How do you protect your data in transit?

Encrypt data in transit with TLS. Authenticate network communications.

Best practices:
- SEC08-BP01: Implement secure key and certificate management (ACM)
- SEC08-BP02: Enforce encryption in transit (TLS 1.2+, HTTPS only)
- SEC08-BP03: Automate detection of unencrypted data in transit
- SEC08-BP04: Authenticate network communications (mutual TLS, VPN)

---

## Incident Response

### SEC 10 — How do you anticipate, respond to, and recover from incidents?

Prepare for incidents, simulate events, automate containment, and learn.

Best practices:
- SEC10-BP01: Identify key personnel and external resources
- SEC10-BP02: Develop incident management plans
- SEC10-BP03: Prepare forensic capabilities
- SEC10-BP04: Develop and test security incident response playbooks
- SEC10-BP05: Pre-provision access for incident response
- SEC10-BP06: Pre-deploy tools for incident response
- SEC10-BP07: Run simulations regularly (game days)

---

## Application Security

### SEC 11 — How do you incorporate and validate security throughout the lifecycle?

Shift security left — integrate into design, development, and deployment.

Best practices:
- SEC11-BP01: Train for application security
- SEC11-BP02: Automate testing throughout the development lifecycle
- SEC11-BP03: Perform regular penetration testing
- SEC11-BP04: Manual code reviews for critical paths
- SEC11-BP05: Centralize services for packages and dependencies
- SEC11-BP06: Deploy software programmatically (no manual deployments)
- SEC11-BP07: Regularly assess the security properties of pipelines

---

## ASTRA Check Coverage

| Check | SEC Question | Automated? |
|-------|-------------|------------|
| SEC-01 Security Hub | SEC 4 (Detection) | ✅ Yes |
| SEC-02 GuardDuty | SEC 4 (Detection) | ✅ Yes |
| SEC-03 Root MFA | SEC 1 (Foundations) | ✅ Yes |
| SEC-04 Password Policy | SEC 2 (Identity) | ✅ Yes |
| SEC-05 S3 Public Block | SEC 7 (Data at Rest) | ✅ Yes |
| SEC-06 CloudTrail | SEC 4 (Detection) | ✅ Yes |
| SEC-07 VPC Flow Logs | SEC 4 (Detection) | ✅ Yes |
| SEC-08 Security Groups | SEC 5 (Network) | ✅ Yes |
| SEC-09 Access Analyzer | SEC 3 (Permissions) | ✅ Yes |
| SEC-10 EBS Encryption | SEC 7 (Data at Rest) | ✅ Yes |
| SEC-11 Secrets Rotation | SEC 2 (Identity) | ✅ Yes |
| SEC-12 KMS Key Rotation | SEC 7 (Data at Rest) | ✅ Yes |
| SEC 1 (Governance) | Design decisions | With customer docs |
| SEC 6 (Compute) | Vulnerability mgmt | With customer docs |
| SEC 8 (Data in Transit) | TLS config | With customer docs |
| SEC 10 (Incident Response) | Playbooks, readiness | With customer docs |
| SEC 11 (App Security) | SDLC practices | With customer docs |
