# AWS Well-Architected Framework — SaaS Lens Best Practices

Source: AWS Well-Architected SaaS Lens (2024), AWS SaaS Architecture Patterns

## Core SaaS Concepts

### Deployment Models

| Model | Description | Isolation Level | Cost Efficiency |
|-------|-------------|-----------------|-----------------|
| **Silo** | Dedicated infrastructure per tenant | Highest | Lowest |
| **Pool** | Shared infrastructure, logical separation | Lower | Highest |
| **Bridge** | Hybrid — shared some, dedicated others | Medium | Medium |

### Tenant Tiers

| Tier | Characteristics | Typical Model |
|------|----------------|---------------|
| Basic/Free | Low SLA, shared resources, rate-limited | Pool |
| Standard | Medium SLA, shared with guardrails | Pool/Bridge |
| Premium | High SLA, dedicated resources, priority | Bridge/Silo |
| Enterprise | Highest SLA, full isolation, custom | Silo |

## SaaS Lens Best Practice Areas

### 1. Tenant Isolation (SaaS-SEC 1)

**How do you prevent cross-tenant access to resources?**

Best Practices:
- Implement isolation at every layer (compute, storage, network)
- Use IAM policies with tenant context (condition keys, session tags)
- Apply runtime isolation enforcement (not just deployment-time)
- Verify isolation with automated testing
- Use tenant-scoped IAM roles (assume role per tenant context)
- Implement permission boundaries to prevent privilege escalation

Isolation Patterns:
| Layer | Silo Pattern | Pool Pattern |
|-------|-------------|-------------|
| Network | Separate VPCs per tenant | Shared VPC, security groups per tenant |
| Compute | Separate clusters/functions | Shared with tenant context |
| Storage | Separate databases/buckets | Row-level security, prefix isolation |
| IAM | Separate roles per tenant | Session policies with tenant conditions |

Key AWS Services:
- IAM Session Tags + Condition Keys (dynamic tenant scoping)
- Amazon Verified Permissions (policy-based authorization)
- VPC + Security Groups (network isolation)
- DynamoDB Leading Key Conditions (data isolation)
- S3 Prefix Policies (storage isolation)

### 2. SaaS Identity (SaaS-SEC 2)

**How do you manage tenant-aware identity?**

Best Practices:
- Separate authentication from authorization
- Inject tenant context into every authenticated session
- Use tenant-scoped tokens (JWT claims with tenant_id)
- Integrate with customer IdPs (Okta, Azure Entra, Google)
- Support per-tenant identity configurations (SSO, MFA policies)
- Map external identity to internal tenant context at the gateway layer

### 3. Data Partitioning (SaaS-REL 1)

**How do you partition data across tenants?**

Best Practices:
- Choose partitioning strategy aligned with isolation requirements
- Silo: Separate databases/tables per tenant
- Pool: Shared tables with tenant_id partition key
- Bridge: Separate schemas within shared database
- Enforce tenant boundaries at the data access layer (not application logic alone)
- Implement row-level security or IAM policies for data isolation
- Plan for tenant data migration between tiers

### 4. Noisy Neighbour Prevention (SaaS-PERF 1)

**How do you prevent one tenant from impacting others?**

Best Practices:
- Implement per-tenant throttling (API Gateway usage plans)
- Use resource quotas per tenant (DynamoDB provisioned capacity, Lambda concurrency)
- Monitor per-tenant resource consumption
- Implement fair queuing for shared resources
- Alert on tenants exceeding baselines
- Use tenant tier-based capacity allocation

Key Services:
- API Gateway Usage Plans + API Keys (per-tenant rate limiting)
- DynamoDB On-Demand with DAX (burst absorption)
- Lambda Reserved Concurrency (per-function limits)
- CloudWatch Metrics with Tenant Dimension

### 5. Tenant Onboarding (SaaS-OPS 1)

**How do you onboard new tenants?**

Best Practices:
- Automate the entire onboarding process (single API call)
- Create all tenant resources via IaC (CDK/CloudFormation)
- Support multiple entry points (self-service, admin portal, API)
- Apply tenant tier configuration during onboarding
- Provision isolation constructs during onboarding (IAM roles, policies)
- Validate tenant configuration before activation

### 6. Tenant Activity and Consumption (SaaS-COST 1)

**How do you track per-tenant costs and usage?**

Best Practices:
- Tag ALL resources with tenant identifier
- Enable Cost Allocation Tags for tenant-related keys
- Implement application-level metering (custom metrics)
- Calculate per-tenant cost using a combination of:
  - Infrastructure cost (tagged resources → Cost Explorer)
  - Shared cost allocation (proportional by usage metrics)
- Provide usage dashboards per tenant
- Alert on cost anomalies per tenant

Key Services:
- AWS Cost Explorer (cost allocation by tag)
- CloudWatch Custom Metrics (tenant-dimension usage)
- AWS Billing Conductor (per-tenant billing groups)

### 7. Tenant-Aware Operations (SaaS-OPS 2)

**How do you operate a multi-tenant environment?**

Best Practices:
- Implement tenant-aware monitoring (per-tenant dashboards)
- Create per-tenant CloudWatch dimensions (not just per-service)
- Route alerts to tenant-aware runbooks
- Support per-tenant debugging (filter logs by tenant_id)
- Implement tenant-scoped deployment (deploy to one tenant first)
- Track SLAs per tenant tier (different SLA per tier)

Key Services:
- CloudWatch Dashboards (per-tenant views)
- CloudWatch Contributor Insights (top tenants by metric)
- X-Ray / OpenTelemetry (per-tenant traces)
- CloudWatch Logs (structured JSON with tenant_id field)

### 8. Control Plane / Data Plane Separation (SaaS-ARCH 1)

**How do you separate tenant management from tenant workloads?**

Best Practices:
- Maintain a SaaS control plane that handles:
  - Tenant registration and onboarding
  - Identity and authentication
  - Billing and metering
  - Tenant configuration
  - Deployment orchestration
- Keep data plane (tenant workloads) separate from control plane
- Control plane should be highly available (independent of tenant failures)
- Data plane failures should not impact the control plane
- Use separate IAM roles for control plane vs data plane
- Different scaling characteristics (control plane scales with tenants, data plane with usage)

Architecture Pattern:
```
┌─────────────────────────┐     ┌─────────────────────────┐
│     CONTROL PLANE        │     │      DATA PLANE          │
│                          │     │                          │
│  Tenant Management       │     │  Tenant Workloads        │
│  Identity/Auth           │     │  Application Logic       │
│  Billing/Metering        │     │  Data Storage            │
│  Config/Settings         │     │  Compute                 │
│  Deployment/Provisioning │     │  API Endpoints           │
│                          │     │                          │
│  (Admin-only access)     │     │  (Tenant-scoped access)  │
└─────────────────────────┘     └─────────────────────────┘
```

## SaaS Maturity Assessment Checklist

| # | Area | Question | Priority |
|---|------|----------|----------|
| 1 | Isolation | Is there a defined isolation strategy per tier? | CRITICAL |
| 2 | Isolation | Are IAM policies enforcing tenant boundaries at runtime? | CRITICAL |
| 3 | Isolation | Is cross-tenant access tested and prevented? | CRITICAL |
| 4 | Identity | Is tenant context injected into every authenticated request? | HIGH |
| 5 | Identity | Do tokens contain tenant_id claims? | HIGH |
| 6 | Data | Is tenant data logically or physically partitioned? | CRITICAL |
| 7 | Data | Can you restore a single tenant's data independently? | HIGH |
| 8 | Noisy Neighbour | Are per-tenant rate limits in place? | HIGH |
| 9 | Noisy Neighbour | Is per-tenant resource consumption monitored? | HIGH |
| 10 | Onboarding | Is tenant onboarding fully automated? | MEDIUM |
| 11 | Onboarding | Can a new tenant be provisioned in < 5 minutes? | MEDIUM |
| 12 | Cost | Are resources tagged with tenant identifiers? | HIGH |
| 13 | Cost | Are Cost Allocation Tags activated for tenant keys? | HIGH |
| 14 | Cost | Can you produce a per-tenant cost report? | MEDIUM |
| 15 | Operations | Are there per-tenant CloudWatch dashboards? | MEDIUM |
| 16 | Operations | Can you filter logs by tenant_id? | HIGH |
| 17 | Operations | Are SLAs defined per tenant tier? | MEDIUM |
| 18 | Architecture | Is control plane separated from data plane? | HIGH |
| 19 | Architecture | Can the control plane survive data plane failures? | HIGH |
| 20 | Architecture | Are admin roles separated from application roles? | HIGH |
