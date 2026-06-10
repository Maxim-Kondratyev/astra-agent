# AWS Well-Architected Framework — Reliability Pillar Best Practices

Source: AWS Well-Architected Framework, Reliability Pillar Whitepaper (November 2024)
Additional: AWS Resilience Lifecycle Framework, Resilient Application Readiness Assessment (RA2)

## Design Principles

1. **Automatically recover from failure**: Monitor KPIs (business value), trigger automation on breach. Anticipate and remediate before occurrence.
2. **Test recovery procedures**: Test how workloads fail. Validate recovery strategies. Simulate different failures using automation.
3. **Scale horizontally**: Replace large resources with multiple small ones. Distribute requests to avoid shared failure points.
4. **Stop guessing capacity**: Monitor demand, automate resource addition/removal. Maintain optimal level without over/under-provisioning.
5. **Manage change through automation**: Infrastructure changes via automation. Track and review changes to automation itself.

## Reliability Areas

### 1. Foundations (REL 1-2)

**REL 1: How do you manage service quotas and constraints?**

Best Practices:
- Be aware of service quotas and constraints (hard/soft limits)
- Manage service quotas across accounts and regions
- Accommodate fixed service quotas through architecture
- Monitor and manage quotas (CloudWatch, Service Quotas)
- Automate quota management (request increases before hitting limits)
- Ensure sufficient gap between current usage and quotas

**REL 2: How do you plan your network topology?**

Best Practices:
- Use highly available network connectivity for public endpoints (multi-AZ, multi-region)
- Provision redundant connectivity between VPCs and on-premises (Direct Connect + VPN)
- Ensure IP subnet allocation accounts for expansion and availability
- Prefer hub-and-spoke topologies over many-to-many mesh
- Enforce non-overlapping private IP address ranges

### 2. Workload Architecture (REL 3-4)

**REL 3: How do you design your workload service architecture?**

Best Practices:
- Choose how to segment your workload (microservices, SOA, monolith)
- Build services focused on specific business domains
- Provide service contracts per API (versioned, backward-compatible)
- Design for resilience to dependencies (circuit breakers, retries with backoff)

**REL 4: How do you design interactions in a distributed system to prevent failures?**

Best Practices:
- Identify which kind of distributed system is required
- Implement loosely coupled dependencies (async, queues, event-driven)
- Make all responses idempotent
- Do constant work (avoid bimodal patterns that fail under load)

### 3. Change Management (REL 5-7)

**REL 5: How do you monitor workload resources?**

Best Practices:
- Monitor all components of the workload (instances, containers, serverless, DB)
- Define and calculate metrics (aggregate, percentiles)
- Send notifications based on thresholds (alarms)
- Automate responses (EventBridge → Lambda/SSM)
- Monitor end-to-end tracing (X-Ray, OpenTelemetry)
- Conduct reviews regularly (weekly ops meetings)

**REL 6: How do you design your workload to adapt to changes in demand?**

Best Practices:
- Use automation when obtaining or scaling resources
- Obtain resources upon detection of impairment
- Obtain resources upon detection that more are needed for demand
- Load test your workload (simulate peak + burst)

**REL 7: How do you implement change?**

Best Practices:
- Use runbooks for standard activities (documented procedures)
- Integrate functional testing as part of deployment
- Integrate resiliency testing as part of deployment
- Deploy using immutable infrastructure (blue/green, canary)
- Deploy changes with automation (CI/CD pipelines)

### 4. Failure Management (REL 8-12)

**REL 8: How do you back up data?**

Best Practices:
- Identify and back up all data that needs to be backed up (AWS Backup)
- Secure and encrypt backups
- Perform data backup automatically (scheduled, policy-based)
- Perform periodic recovery of data to verify backup integrity
- Define and enforce backup retention policies (regulatory requirements)

**REL 9: How do you use fault isolation to protect your workload?**

Best Practices:
- Deploy the workload to multiple locations (Multi-AZ minimum, Multi-Region for critical)
- Automate recovery for components constrained to a single location
- Use bulkhead architectures to limit blast radius
- Use static stability (pre-provisioned capacity)

**REL 10: How do you design your workload to withstand component failures?**

Best Practices:
- Monitor all components and fail over when thresholds are breached
- Use health checks for load balancers and auto-scaling
- Design for graceful degradation (serve stale data, reduce features)
- Test resiliency using chaos engineering (FIS)
- Design with no single points of failure (redundancy at every layer)

**REL 11: How do you test reliability?**

Best Practices:
- Use playbooks to investigate failures
- Perform post-incident analysis (5 Whys, blameless)
- Test functional requirements (unit, integration, end-to-end)
- Test scaling and performance requirements (load, stress)
- Test resiliency (chaos engineering, game days)
- Conduct game days regularly (quarterly minimum)

**REL 12: How do you plan for disaster recovery (DR)?**

Best Practices:
- Define recovery objectives (RTO and RPO per workload tier)
- Use defined recovery strategies (backup/restore, pilot light, warm standby, active-active)
- Test disaster recovery implementation (at least annually)
- Manage configuration drift at the DR site
- Automate recovery (runbooks → automation documents)

## AWS Resilience Lifecycle Framework (5 Stages)

| Stage | Activities | Tools/Mechanisms |
|-------|-----------|-----------------|
| 1. Set Objectives | Define RTO/RPO, identify critical workloads, set resilience goals | Business Impact Analysis |
| 2. Design & Implement | Architecture for HA, deploy across AZs/Regions, implement backups | Well-Architected Reviews, RA2 |
| 3. Evaluate & Test | Assess against objectives, run chaos experiments | Resilience Hub, FIS, Game Days |
| 4. Operate | Monitor, respond to events, maintain operational readiness | CloudWatch, EventBridge, Incident Manager |
| 5. Respond & Learn | Incident response, post-incident review, continuous improvement | Runbooks, Post-mortems, Corrections of Error |

## Resilient Application Readiness Assessment (RA2)

RA2 is a deep-dive resilience assessment built by AWS Professional Services that evaluates:

### Assessment Areas:
1. **Architecture Resilience** — Multi-AZ/Region deployment, redundancy, fault isolation
2. **Data Protection** — Backup strategy, RPO compliance, cross-region replication
3. **Scaling & Capacity** — Auto-scaling policies, capacity planning, burst handling
4. **Operational Readiness** — Runbooks, monitoring, alerting, incident response
5. **Recovery Capability** — DR strategy, RTO compliance, tested recovery procedures
6. **Dependency Management** — External dependencies, circuit breakers, fallback patterns

### RA2 Key Questions:
- Are all stateful services deployed Multi-AZ or Multi-Region?
- Are RTO/RPO objectives defined and documented?
- Has disaster recovery been tested in the last 12 months?
- Are there automated recovery procedures (runbooks)?
- Are single points of failure identified and mitigated?
- Is there capacity headroom for traffic spikes?
- Are dependencies mapped with fallback patterns?
- Is chaos engineering practised regularly?

## Critical Reliability Controls Checklist

| # | Control | Priority |
|---|---------|----------|
| 1 | Multi-AZ deployment for all stateful services (RDS, ElastiCache) | CRITICAL |
| 2 | Auto-scaling enabled with appropriate policies | HIGH |
| 3 | Automated backups with tested recovery | CRITICAL |
| 4 | No single points of failure (redundant NAT GWs, ELBs across AZs) | HIGH |
| 5 | Health checks configured (ELB + ASG) | HIGH |
| 6 | RTO/RPO objectives defined and documented | HIGH |
| 7 | Cross-region backup/replication for critical data | MEDIUM |
| 8 | Load balancers span 2+ AZs | HIGH |
| 9 | Route 53 health checks for failover | MEDIUM |
| 10 | Disaster recovery tested (annual minimum) | HIGH |
| 11 | Chaos engineering practised (FIS game days) | MEDIUM |
| 12 | Circuit breakers for external dependencies | MEDIUM |
| 13 | Immutable deployments (blue/green or canary) | MEDIUM |
| 14 | Monitoring covers all components (metrics + alarms) | HIGH |
| 15 | Runbooks for common failure scenarios | MEDIUM |
| 16 | Service quota monitoring (before hitting limits) | MEDIUM |
| 17 | Data backup retention meets compliance requirements | HIGH |
| 18 | EBS snapshots exist for all critical volumes | MEDIUM |
| 19 | Standalone instances in ASGs (self-healing) | MEDIUM |
| 20 | Graceful degradation patterns implemented | LOW |
