# AWS Well-Architected SaaS Lens

Source: https://docs.aws.amazon.com/wellarchitected/latest/saas-lens/saas-lens.html

The SaaS Lens adds multi-tenant considerations to the six pillars of the
AWS Well-Architected Framework, focusing on how to design, deploy, and
operate multi-tenant SaaS workloads.

## Key Concept Areas

1. Tenants — logical isolation units (may map to customers or accounts)
2. Silo/Pool/Bridge models — resource sharing strategies
3. SaaS identity — tenant context in every request
4. Tenant isolation — preventing cross-tenant access
5. Data partitioning — separating tenant data
6. Noisy neighbour — preventing one tenant from impacting others
7. Tenant onboarding — automated provisioning
8. Tenant tiers — differentiated service levels
9. Tenant activity and consumption — tracking per-tenant usage
10. Tenant-aware operations — monitoring, alerting, debugging per tenant

---

## Operational Excellence (SaaS-specific)

### How do you onboard tenants?
- Centralize onboarding through a SaaS control plane
- Single, repeatable mechanism for all tiers
- Support multiple entry points (self-service + admin)
- Automate infrastructure provisioning per tier
- Handle tiering policies during onboarding

### How do you manage tenant-aware operations?
- Per-tenant health dashboards and metrics
- Tenant-scoped logging (filter by tenant_id)
- Tiered operational response (premium tenants get faster response)
- Centralized control plane for fleet management

### How do you manage deployments across tenants?
- Deploy simultaneously to all tenants (no version fragmentation)
- Support tenant-specific feature flags where needed
- Canary deployments with tenant-awareness

---

## Security (SaaS-specific)

### How do you manage tenant identity and isolation?
- Inject tenant context into every authenticated request
- Enforce isolation at infrastructure level (not just application code)
- Use session policies, permission boundaries, or resource policies
- Never rely solely on application logic for isolation

### How do you prevent cross-tenant access?
- Test isolation boundaries regularly
- Use IAM condition keys to scope access
- Validate tenant context at every service boundary
- Audit access patterns for cross-tenant anomalies

---

## Reliability (SaaS-specific)

### How do you handle noisy neighbour conditions?
- Per-tenant throttling (API Gateway usage plans, Lambda concurrency)
- Resource quotas per tenant (DynamoDB capacity, queue limits)
- Tenant activity monitoring with alerting on anomalous usage
- Graceful degradation rather than total service failure

### How do you ensure per-tenant availability?
- Monitor health per tenant, not just per service
- Isolate blast radius (one tenant's failure shouldn't cascade)
- Design for tenant-specific recovery (not system-wide restart)
- Test failure scenarios with tenant context

---

## Performance Efficiency (SaaS-specific)

### How do you scale for unpredictable tenant load?
- Auto-scaling with tenant-aware metrics
- Pool model: scale the shared fleet dynamically
- Silo model: scale each tenant's resources independently
- Use serverless where possible (inherent per-request scaling)

### How do you manage performance across tiers?
- Differentiate resource allocation by tier (premium gets more capacity)
- Priority queues for high-tier tenants
- Dedicated compute for enterprise tier (silo within pool)

---

## Cost Optimization (SaaS-specific)

### How do you attribute costs to tenants?
- Tag all resources with tenant identifier
- Activate cost allocation tags in AWS Billing
- For shared resources: use consumption metrics to allocate
- Track cost-per-tenant trends over time

### How do you optimise across tenant tiers?
- Basic tier: high-density pooling (lowest cost per tenant)
- Premium tier: dedicated resources (higher cost, better isolation)
- Right-size infrastructure based on actual per-tier consumption

---

## ASTRA SaaS Check Coverage

| Check | SaaS Lens Area | Automated? |
|-------|---------------|------------|
| SAS-01 Tenant tagging | Cost Optimization | ✅ Yes |
| SAS-02 Cost allocation tags | Cost Optimization | ✅ Yes |
| SAS-03 Permission boundaries | Security (isolation) | ✅ Yes |
| SAS-04 Resource isolation | Security (isolation) | ✅ Yes |
| SAS-05 Per-tenant monitoring | Operational Excellence | ✅ Yes |
| SAS-06 API throttling | Reliability (noisy neighbour) | ✅ Yes |
| SAS-07 Control plane separation | Operational Excellence | ✅ Yes |
| SAS-08 Cross-tenant access | Security (isolation) | ✅ Yes |
| SAS-09 Onboarding automation | Operational Excellence | ✅ Yes |
| SAS-10 Noisy neighbour detection | Reliability | ✅ Yes |
| Identity model | Security | With customer docs |
| Data partitioning strategy | Security / Reliability | With customer docs |
| Tier differentiation | Performance / Cost | With customer docs |
| Deployment strategy | Operational Excellence | With customer docs |
