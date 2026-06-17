# AWS SaaS Tenant Isolation Strategies

Source: https://docs.aws.amazon.com/whitepapers/latest/saas-tenant-isolation-strategies/

## Core Principle

Tenant isolation is a **non-optional requirement** for any SaaS system. Authentication
and authorization alone are insufficient — you need infrastructure-level enforcement
that prevents one tenant from accessing another tenant's resources.

## Isolation Models

### 1. Silo Model (Dedicated per tenant)
- Separate account, VPC, or full stack per tenant
- **Pros:** Simple isolation, no noisy neighbour, easy cost tracking, limited blast radius
- **Cons:** Expensive, hard to scale past ~20 tenants, slow onboarding, decentralized ops
- **Best for:** Regulated industries, enterprise tier, <50 tenants

### 2. Pool Model (Shared resources)
- All tenants share the same infrastructure (compute, database, storage)
- Isolation enforced at application layer (row-level security, IAM policies, runtime checks)
- **Pros:** Cost efficient, fast onboarding, unified operations
- **Cons:** Noisy neighbour risk, complex isolation logic, harder cost attribution
- **Best for:** High-volume SaaS, self-service tiers, 100+ tenants

### 3. Bridge Model (Hybrid)
- Shared compute, separate data per tenant (e.g., schema-per-tenant in RDS)
- Balances isolation with efficiency
- **Best for:** Mid-market SaaS, compliance-sensitive data with shared compute

## Isolation Enforcement Mechanisms

| Layer | Mechanism | Example |
|-------|-----------|---------|
| Account | AWS Organizations, separate accounts | Account-per-tenant |
| Network | VPC, security groups, PrivateLink | VPC-per-tenant or subnet isolation |
| IAM | Permission boundaries, session policies | Tenant-scoped roles |
| Data | Row-level security, S3 prefixes, DynamoDB leading key | Partition data by tenant_id |
| Application | Runtime tenant context, JWT claims | Request-scoped tenant validation |

## SaaS Operations Best Practices

### Tenant Onboarding
- Fully automated provisioning (IaC: CDK/CloudFormation/Terraform)
- Self-service or admin-triggered (not manual)
- Consistent configuration across all tenants

### Cost Attribution
- Tag resources with tenant identifier
- Activate cost allocation tags in Billing
- Track per-tenant spend for margin analysis

### Noisy Neighbour Prevention
- API throttling per tenant (API Gateway usage plans)
- Lambda reserved concurrency per function
- Database connection limits
- Queue-per-tenant or priority queues

### Observability
- Tenant-aware metrics (CloudWatch dimensions with tenant_id)
- Per-tenant dashboards or filtered views
- Alarms scoped to individual tenants for SLA monitoring

### Control Plane vs Data Plane
- **Control plane:** Tenant management, onboarding, billing, configuration
- **Data plane:** Tenant workloads, application logic, customer-facing APIs
- Separate IAM roles for each (least privilege)
- Control plane should be more highly available than any single tenant's data plane

## Assessment Questions

When evaluating SaaS architecture maturity, assess:
1. Can Tenant A access Tenant B's data through any path? (must be "no")
2. Can one tenant's load affect another tenant's performance? (noisy neighbour)
3. Can you attribute costs to each tenant? (billing visibility)
4. Is tenant provisioning automated or manual?
5. Do you have per-tenant observability? (can you answer "is Tenant X healthy?")
6. Is there separation between control plane and data plane?
7. Are there throttling/quota mechanisms per tenant?
