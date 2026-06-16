# Example Customer Architecture Document

This is a sample document showing what customers can provide for context-aware assessments.

## System Overview

Our platform serves 500+ enterprise tenants. We process ~2M API requests/day.

## Architecture

- **Compute**: ECS Fargate (3 services) + Lambda (event processing)
- **Database**: Aurora PostgreSQL (primary) + DynamoDB (sessions, cache)
- **Storage**: S3 (tenant data, separated by prefix per tenant)
- **Networking**: 3 VPCs (production, staging, management), peered

## Requirements

- **RTO**: 4 hours for full recovery
- **RPO**: 1 hour (no more than 1 hour of data loss acceptable)
- **Availability target**: 99.9% (8.7 hours downtime/year max)

## Tenant Isolation Model

- Pool model (shared resources) with tenant ID in all API requests
- Data separated by tenant_id column in Aurora, S3 prefix per tenant
- IAM roles: one per service, not per tenant
- No per-tenant VPCs (all tenants share production VPC)

## Known Gaps (we want ASTRA to validate)

- Not sure if our backup retention meets RPO
- Single-AZ NAT gateway — is this a risk?
- No Route 53 failover configured yet
- GuardDuty enabled but nobody monitors alerts
