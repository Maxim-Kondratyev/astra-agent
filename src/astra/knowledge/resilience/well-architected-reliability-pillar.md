# Well-Architected Framework — Reliability Pillar (Official Reference)

Source: https://docs.aws.amazon.com/wellarchitected/latest/framework/a-reliability.html

The Reliability pillar encompasses the ability of a workload to perform its intended
function correctly and consistently when it's expected to.

## Best Practice Areas

1. Foundations (REL 1–5)
2. Workload Architecture (REL 5)
3. Change Management (REL 6–8)
4. Failure Management (REL 9–13)

---

## Change Management

### REL 6 — How do you monitor workload resources?

Logs and metrics are powerful tools to gain insight into the health of your workload.
Configure your workload to monitor logs and metrics and send notifications when
thresholds are crossed or significant events occur.

Best practices:
- REL06-BP01: Monitor all components for the workload (Generation)
- REL06-BP02: Define and calculate metrics (Aggregation)
- REL06-BP03: Send notifications (Real-time processing and alarming)
- REL06-BP04: Automate responses (Real-time processing and alarming)
- REL06-BP05: Analyze logs
- REL06-BP06: Regularly review monitoring scope and metrics
- REL06-BP07: Monitor end-to-end tracing of requests through your system

### REL 7 — How do you design your workload to adapt to changes in demand?

A scalable workload provides elasticity to add or remove resources automatically
so that they closely match the current demand at any given point in time.

Best practices:
- REL07-BP01: Use automation when obtaining or scaling resources
- REL07-BP02: Obtain resources upon detection of impairment to a workload
- REL07-BP03: Obtain resources upon detection that more resources are needed
- REL07-BP04: Load test your workload

### REL 8 — How do you implement change?

Controlled changes are necessary to deploy new functionality and ensure that the
workloads and operating environments are running known, properly patched software.

---

## Failure Management

### REL 9 — How do you back up data?

Back up data, applications, and configuration to meet your requirements for
recovery time objectives (RTO) and recovery point objectives (RPO).

Best practices:
- REL09-BP01: Identify and back up all data that needs to be backed up, or reproduce the data from sources
- REL09-BP02: Secure and encrypt backups
- REL09-BP03: Perform data backup automatically
- REL09-BP04: Perform periodic recovery of the data to verify backup integrity and processes

### REL 10 — How do you use fault isolation to protect your workload?

Fault isolation limits the impact of a component or system failure to a defined
boundary. With proper isolation, components outside of the boundary are unaffected
by the failure.

Best practices:
- REL10-BP01: Deploy the workload to multiple locations
- REL10-BP02: Automate recovery for components constrained to a single location
- REL10-BP03: Use bulkhead architectures to limit scope of impact

### REL 11 — How do you design your workload to withstand component failures?

Workloads with a requirement for high availability and low mean time to recovery
(MTTR) must be architected for resiliency.

Best practices:
- REL11-BP01: Monitor all components of the workload to detect failures
- REL11-BP02: Fail over to healthy resources
- REL11-BP03: Automate healing on all layers
- REL11-BP04: Rely on the data plane and not the control plane during recovery
- REL11-BP05: Use static stability to prevent bimodal behavior
- REL11-BP06: Send notifications when events impact availability
- REL11-BP07: Architect your product to meet availability targets and uptime SLAs

### REL 12 — How do you test reliability?

Test the resiliency of your workload to help you find latent bugs that only appear
in production. Exercise these tests regularly.

### REL 13 — How do you plan for disaster recovery (DR)?

Having backups and redundant workload components in place is the start of your DR
strategy. RTO and RPO are your objectives for restoration of your workload.

Best practices:
- REL13-BP01: Define recovery objectives for downtime and data loss
- REL13-BP02: Use defined recovery strategies to meet the recovery objectives
- REL13-BP03: Test disaster recovery implementation to validate the implementation
- REL13-BP04: Manage configuration drift at the DR site or Region
- REL13-BP05: Automate recovery

---

## ASTRA Check Mapping

| Check ID | ASTRA Check | WA Best Practice |
|----------|-------------|-----------------|
| REL-01 | RDS Multi-AZ | REL10-BP01: Deploy to multiple locations |
| REL-02 | EC2 AZ distribution | REL10-BP01: Deploy to multiple locations |
| REL-03 | ASG health check type | REL06-BP01: Monitor all components |
| REL-04 | ASG multi-AZ | REL10-BP01: Deploy to multiple locations |
| REL-05 | ELB multi-AZ | REL10-BP01: Deploy to multiple locations |
| REL-06 | AWS Backup plans | REL09-BP03: Perform data backup automatically |
| REL-07 | RDS backup retention | REL09-BP01: Identify and back up all data |
| REL-08 | NAT Gateway redundancy | REL10-BP01: Deploy to multiple locations |
| REL-09 | EBS snapshot coverage | REL09-BP03: Perform data backup automatically |
| REL-10 | Route 53 health checks | REL11-BP02: Fail over to healthy resources |
| REL-11 | ElastiCache Multi-AZ | REL10-BP01: Deploy to multiple locations |
| REL-12 | CloudWatch alarms | REL06-BP03: Send notifications |
