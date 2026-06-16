"""SaaS checklist — prebuilt Well-Architected SaaS Lens checks.

Maps to SaaS Lens questions covering tenant isolation, operational efficiency,
cost optimization, and governance.
"""

import boto3

from astra.checklist import CheckResult, Status


def check_tenant_tagging_strategy() -> CheckResult:
    """SAS-01: Resources should be tagged with a tenant identifier."""
    tagging = boto3.client("resourcegroupstaggingapi")
    try:
        all_keys = tagging.get_tag_keys().get("TagKeys", [])
        tenant_keys = [k for k in all_keys if k.lower() in ("tenant", "tenantid", "tenant_id", "tenant-id", "customer", "customerid", "customer_id", "client")]
        if not tenant_keys:
            return CheckResult("SAS-01", "Tenant tagging strategy", Status.FAIL,
                             evidence={"tag_keys_found": all_keys[:20]},
                             recommendation="Establish a mandatory tenant tag (e.g., 'TenantId') on all resources for isolation, cost allocation, and observability.",
                             wa_reference="SaaS Lens – How do you manage tenant resource allocation?")
        # Check coverage
        tagged = tagging.get_resources(TagFilters=[{"Key": tenant_keys[0]}], ResourcesPerPage=100)
        count = len(tagged.get("ResourceTagMappingList", []))
        if count < 10:
            return CheckResult("SAS-01", "Tenant tagging strategy", Status.WARNING,
                             evidence={"tenant_tag": tenant_keys[0], "tagged_resources": count},
                             recommendation=f"Tag '{tenant_keys[0]}' exists but has low coverage ({count} resources). Enforce tagging via SCP or Config rules.",
                             wa_reference="SaaS Lens – How do you manage tenant resource allocation?")
        return CheckResult("SAS-01", "Tenant tagging strategy", Status.PASS, evidence={"tenant_tags": tenant_keys, "sample_coverage": count})
    except Exception as e:
        return CheckResult("SAS-01", "Tenant tagging strategy", Status.ERROR, evidence={"error": str(e)})


def check_cost_allocation_tags() -> CheckResult:
    """SAS-02: Cost allocation tags should be activated for tenant billing."""
    ce = boto3.client("ce")
    try:
        tags = ce.list_cost_allocation_tags(Status="Active", MaxResults=100).get("CostAllocationTags", [])
        tenant_tags = [t for t in tags if t["TagKey"].lower() in ("tenant", "tenantid", "customer", "team", "project")]
        if not tenant_tags:
            return CheckResult("SAS-02", "Cost allocation tags", Status.FAIL,
                             evidence={"active_tags": [t["TagKey"] for t in tags[:10]]},
                             recommendation="Activate cost allocation tags for tenant-related keys to enable per-tenant cost reporting.",
                             wa_reference="SaaS Lens – How do you manage tenant cost attribution?")
        return CheckResult("SAS-02", "Cost allocation tags", Status.PASS, evidence={"active_tenant_tags": [t["TagKey"] for t in tenant_tags]})
    except Exception as e:
        return CheckResult("SAS-02", "Cost allocation tags", Status.ERROR, evidence={"error": str(e)})


def check_permission_boundaries() -> CheckResult:
    """SAS-03: IAM roles should use permission boundaries for tenant scoping."""
    iam = boto3.client("iam")
    try:
        roles = iam.list_roles(MaxItems=100).get("Roles", [])
        app_roles = [r for r in roles if not r["Path"].startswith("/aws-service-role/")]
        if not app_roles:
            return CheckResult("SAS-03", "Permission boundaries", Status.PASS, evidence={"detail": "No custom roles."})
        with_boundary = sum(1 for r in app_roles if r.get("PermissionsBoundary"))
        ratio = with_boundary / len(app_roles) if app_roles else 0
        if ratio < 0.1:
            return CheckResult("SAS-03", "Permission boundaries", Status.WARNING,
                             evidence={"custom_roles": len(app_roles), "with_boundary": with_boundary},
                             recommendation="Apply permission boundaries to application/tenant roles to enforce access scope limits.",
                             wa_reference="SaaS Lens – How do you enforce tenant isolation?")
        return CheckResult("SAS-03", "Permission boundaries", Status.PASS, evidence={"custom_roles": len(app_roles), "with_boundary": with_boundary})
    except Exception as e:
        return CheckResult("SAS-03", "Permission boundaries", Status.ERROR, evidence={"error": str(e)})


def check_resource_isolation() -> CheckResult:
    """SAS-04: Multi-tenant workloads should have isolation boundaries (VPC, account, or resource-level)."""
    ec2 = boto3.client("ec2")
    try:
        vpcs = ec2.describe_vpcs().get("Vpcs", [])
        non_default = [v for v in vpcs if not v.get("IsDefault")]
        if len(non_default) > 1:
            # Multiple VPCs suggest isolation
            tagged_vpcs = sum(1 for v in non_default if any(t["Key"].lower() in ("tenant", "environment", "team") for t in v.get("Tags", [])))
            return CheckResult("SAS-04", "Resource isolation", Status.PASS,
                             evidence={"vpcs": len(non_default), "tenant_tagged_vpcs": tagged_vpcs})
        if non_default:
            return CheckResult("SAS-04", "Resource isolation", Status.WARNING,
                             evidence={"vpcs": 1},
                             recommendation="Consider VPC-per-tenant or subnet-per-tenant isolation for stronger blast radius containment.",
                             wa_reference="SaaS Lens – How do you enforce tenant isolation?")
        return CheckResult("SAS-04", "Resource isolation", Status.PASS, evidence={"detail": "No custom VPCs (likely serverless or account-level isolation)."})
    except Exception as e:
        return CheckResult("SAS-04", "Resource isolation", Status.ERROR, evidence={"error": str(e)})


def check_per_tenant_monitoring() -> CheckResult:
    """SAS-05: Monitoring should include tenant-specific dimensions/dashboards."""
    cw = boto3.client("cloudwatch")
    try:
        dashboards = cw.list_dashboards().get("DashboardEntries", [])
        alarms = cw.describe_alarms(MaxRecords=50).get("MetricAlarms", [])
        tenant_dims = set()
        for a in alarms:
            for d in a.get("Dimensions", []):
                if d["Name"].lower() in ("tenant", "tenantid", "customer"):
                    tenant_dims.add(d["Name"])
        tenant_dashboards = [d for d in dashboards if any(k in d["DashboardName"].lower() for k in ("tenant", "customer"))]
        if not tenant_dims and not tenant_dashboards:
            return CheckResult("SAS-05", "Per-tenant monitoring", Status.WARNING,
                             evidence={"dashboards": len(dashboards), "tenant_dimensions": 0},
                             recommendation="Add tenant-specific CloudWatch dimensions and dashboards for per-tenant visibility into errors, latency, and usage.",
                             wa_reference="SaaS Lens – How do you monitor tenant activity?")
        return CheckResult("SAS-05", "Per-tenant monitoring", Status.PASS, evidence={"tenant_dimensions": list(tenant_dims), "tenant_dashboards": len(tenant_dashboards)})
    except Exception as e:
        return CheckResult("SAS-05", "Per-tenant monitoring", Status.ERROR, evidence={"error": str(e)})


def check_api_throttling() -> CheckResult:
    """SAS-06: APIs should have per-tenant throttling to prevent noisy neighbour issues."""
    apigw = boto3.client("apigateway")
    try:
        apis = apigw.get_rest_apis().get("items", [])
        if not apis:
            return CheckResult("SAS-06", "API throttling", Status.PASS, evidence={"detail": "No API Gateway REST APIs."})
        usage_plans = apigw.get_usage_plans().get("items", [])
        if not usage_plans:
            return CheckResult("SAS-06", "API throttling", Status.WARNING,
                             evidence={"rest_apis": len(apis), "usage_plans": 0},
                             recommendation="Create API Gateway usage plans with per-tenant rate limits to prevent noisy neighbour issues.",
                             wa_reference="SaaS Lens – How do you prevent noisy neighbour issues?")
        return CheckResult("SAS-06", "API throttling", Status.PASS, evidence={"usage_plans": len(usage_plans)})
    except Exception as e:
        return CheckResult("SAS-06", "API throttling", Status.ERROR, evidence={"error": str(e)})


def check_control_plane_separation() -> CheckResult:
    """SAS-07: Control plane (management) should be separated from data plane (tenant workloads)."""
    iam = boto3.client("iam")
    try:
        roles = iam.list_roles(MaxItems=100).get("Roles", [])
        admin_roles = [r for r in roles if any(k in r["RoleName"].lower() for k in ("admin", "management", "control", "platform", "infra"))]
        app_roles = [r for r in roles if any(k in r["RoleName"].lower() for k in ("app", "service", "worker", "data", "tenant", "execution", "task"))]
        if admin_roles and app_roles:
            return CheckResult("SAS-07", "Control plane separation", Status.PASS,
                             evidence={"admin_roles": len(admin_roles), "app_roles": len(app_roles)})
        return CheckResult("SAS-07", "Control plane separation", Status.WARNING,
                         evidence={"admin_roles": len(admin_roles), "app_roles": len(app_roles)},
                         recommendation="Separate control plane (admin/management) IAM roles from data plane (application/tenant) roles for least privilege.",
                         wa_reference="SaaS Lens – How do you separate control plane and data plane?")
    except Exception as e:
        return CheckResult("SAS-07", "Control plane separation", Status.ERROR, evidence={"error": str(e)})


def check_cross_tenant_access() -> CheckResult:
    """SAS-08: S3 bucket policies and KMS key policies should prevent cross-tenant data access."""
    s3 = boto3.client("s3")
    try:
        buckets = s3.list_buckets().get("Buckets", [])[:20]
        wildcard_policies = []
        for b in buckets:
            try:
                import json
                policy_str = s3.get_bucket_policy(Bucket=b["Name"])["Policy"]
                policy = json.loads(policy_str)
                for stmt in policy.get("Statement", []):
                    principal = stmt.get("Principal", "")
                    if principal == "*" or (isinstance(principal, dict) and principal.get("AWS") == "*"):
                        if stmt.get("Effect") == "Allow":
                            wildcard_policies.append(b["Name"])
                            break
            except s3.exceptions.ClientError:
                continue  # No bucket policy = OK
        if wildcard_policies:
            return CheckResult("SAS-08", "Cross-tenant data access", Status.FAIL,
                             evidence={"buckets_with_wildcard_allow": wildcard_policies},
                             affected_resources=wildcard_policies,
                             recommendation="Remove wildcard (*) principals from S3 bucket policies. Use explicit account/role conditions.",
                             wa_reference="SaaS Lens – How do you enforce tenant isolation?")
        return CheckResult("SAS-08", "Cross-tenant data access", Status.PASS, evidence={"buckets_checked": len(buckets)})
    except Exception as e:
        return CheckResult("SAS-08", "Cross-tenant data access", Status.ERROR, evidence={"error": str(e)})


def check_tenant_onboarding_automation() -> CheckResult:
    """SAS-09: Tenant provisioning should be automated (CloudFormation, CDK, or custom)."""
    cfn = boto3.client("cloudformation")
    try:
        stacks = cfn.list_stacks(StackStatusFilter=["CREATE_COMPLETE", "UPDATE_COMPLETE"]).get("StackSummaries", [])
        tenant_stacks = [s for s in stacks if any(k in s["StackName"].lower() for k in ("tenant", "customer", "onboard"))]
        if tenant_stacks:
            return CheckResult("SAS-09", "Tenant onboarding automation", Status.PASS,
                             evidence={"tenant_stacks": [s["StackName"] for s in tenant_stacks[:5]]})
        if len(stacks) > 5:
            return CheckResult("SAS-09", "Tenant onboarding automation", Status.PASS,
                             evidence={"detail": "IaC in use (many CloudFormation stacks). Tenant automation likely handled externally."})
        return CheckResult("SAS-09", "Tenant onboarding automation", Status.WARNING,
                         evidence={"cloudformation_stacks": len(stacks)},
                         recommendation="Automate tenant onboarding with IaC (CloudFormation/CDK) to ensure consistent, repeatable provisioning.",
                         wa_reference="SaaS Lens – How do you onboard new tenants?")
    except Exception as e:
        return CheckResult("SAS-09", "Tenant onboarding automation", Status.ERROR, evidence={"error": str(e)})


def check_noisy_neighbour_detection() -> CheckResult:
    """SAS-10: Shared resources should have throttling or capacity limits per tenant."""
    lam = boto3.client("lambda")
    try:
        functions = lam.list_functions(MaxItems=50).get("Functions", [])
        if not functions:
            return CheckResult("SAS-10", "Noisy neighbour detection", Status.PASS, evidence={"detail": "No Lambda functions."})
        with_concurrency = sum(1 for f in functions if f.get("ReservedConcurrentExecutions") is not None or "concurrency" in str(f.get("FunctionName", "")).lower())
        if with_concurrency == 0 and len(functions) > 5:
            return CheckResult("SAS-10", "Noisy neighbour detection", Status.WARNING,
                             evidence={"functions": len(functions), "with_concurrency_limits": with_concurrency},
                             recommendation="Set reserved concurrency limits on shared Lambda functions to prevent a single tenant from consuming all capacity.",
                             wa_reference="SaaS Lens – How do you prevent noisy neighbour issues?")
        return CheckResult("SAS-10", "Noisy neighbour detection", Status.PASS, evidence={"functions": len(functions), "with_limits": with_concurrency})
    except Exception as e:
        return CheckResult("SAS-10", "Noisy neighbour detection", Status.ERROR, evidence={"error": str(e)})


ALL_CHECKS = [
    check_tenant_tagging_strategy,
    check_cost_allocation_tags,
    check_permission_boundaries,
    check_resource_isolation,
    check_per_tenant_monitoring,
    check_api_throttling,
    check_control_plane_separation,
    check_cross_tenant_access,
    check_tenant_onboarding_automation,
    check_noisy_neighbour_detection,
]


def run_saas_checklist() -> list[CheckResult]:
    """Run all prebuilt SaaS checks."""
    results = []
    for check_fn in ALL_CHECKS:
        try:
            results.append(check_fn())
        except Exception as e:
            results.append(CheckResult(check_id="UNKNOWN", title=check_fn.__name__, status=Status.ERROR, evidence={"error": str(e)}))
    return results
