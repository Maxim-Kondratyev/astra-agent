"""SaaS/Tenancy assessment tools — read-only checks for multi-tenant architecture patterns."""

import boto3
from strands import tool


@tool
def check_tenant_isolation() -> dict:
    """Check tenant isolation patterns: VPC separation, IAM boundaries, resource-level isolation.

    Returns:
        Dictionary with isolation patterns detected across VPCs, IAM, and resource policies.
    """
    result = {}
    ec2 = boto3.client("ec2")
    iam = boto3.client("iam")

    # VPC isolation — count VPCs and check for peering/TGW (multi-tenant network patterns)
    try:
        vpcs = ec2.describe_vpcs().get("Vpcs", [])
        vpc_info = []
        for vpc in vpcs:
            tags = {t["Key"]: t["Value"] for t in vpc.get("Tags", [])}
            vpc_info.append({
                "vpc_id": vpc["VpcId"],
                "cidr": vpc["CidrBlock"],
                "is_default": vpc.get("IsDefault", False),
                "name": tags.get("Name", ""),
                "tenant_tag": tags.get("tenant", tags.get("Tenant", tags.get("TenantId", ""))),
            })
        result["vpcs"] = {"total": len(vpcs), "vpcs": vpc_info, "has_tenant_tagged_vpcs": any(v["tenant_tag"] for v in vpc_info)}

        # VPC peering (shared resources between tenants?)
        peerings = ec2.describe_vpc_peering_connections().get("VpcPeeringConnections", [])
        result["vpc_peering"] = {"count": len(peerings)}
    except Exception as e:
        result["vpcs"] = {"total": 0, "error": str(e)}

    # IAM permission boundaries (tenant-scoped access)
    try:
        users = iam.list_users().get("Users", [])
        roles = iam.list_roles().get("Roles", [])[:50]
        users_with_boundary = sum(1 for u in users if u.get("PermissionsBoundary"))
        roles_with_boundary = sum(1 for r in roles if r.get("PermissionsBoundary"))
        result["iam_boundaries"] = {
            "users_total": len(users),
            "users_with_boundary": users_with_boundary,
            "roles_total": len(roles),
            "roles_with_boundary": roles_with_boundary,
            "boundary_adoption": f"{roles_with_boundary}/{len(roles)} roles" if roles else "N/A",
        }
    except Exception:
        result["iam_boundaries"] = {"users_total": 0, "roles_total": 0}

    # Security groups — check for overly broad rules (tenant bleed)
    try:
        sgs = ec2.describe_security_groups().get("SecurityGroups", [])
        cross_sg_refs = 0
        for sg in sgs:
            for rule in sg.get("IpPermissions", []):
                for pair in rule.get("UserIdGroupPairs", []):
                    if pair.get("GroupId") != sg["GroupId"]:
                        cross_sg_refs += 1
        result["security_groups"] = {"total": len(sgs), "cross_sg_references": cross_sg_refs}
    except Exception:
        result["security_groups"] = {"total": 0}

    return result


@tool
def check_resource_tagging() -> dict:
    """Audit resource tagging strategy for tenant identification and cost allocation.

    Returns:
        Dictionary with tagging coverage, common tag keys, and untagged resources.
    """
    result = {}

    # Use Resource Groups Tagging API
    tagging = boto3.client("resourcegroupstaggingapi")
    try:
        # Get all tag keys
        tag_keys_resp = tagging.get_tag_keys()
        all_keys = tag_keys_resp.get("TagKeys", [])
        result["tag_keys"] = {"total": len(all_keys), "keys": all_keys[:30]}

        # Check for tenant-related tags
        tenant_keys = [k for k in all_keys if k.lower() in ("tenant", "tenantid", "tenant_id", "tenant-id", "customer", "customerid", "customer_id", "team", "project", "environment", "env")]
        result["tenant_tags_found"] = tenant_keys

        # Count resources per tag key (sample the important ones)
        for key in tenant_keys[:3]:
            tagged = tagging.get_resources(TagFilters=[{"Key": key}], ResourcesPerPage=100)
            result[f"tagged_with_{key}"] = len(tagged.get("ResourceTagMappingList", []))

        # Untagged resources
        all_resources = tagging.get_resources(ResourcesPerPage=100)
        resources = all_resources.get("ResourceTagMappingList", [])
        untagged = [r["ResourceARN"] for r in resources if not r.get("Tags")]
        result["sample_untagged_resources"] = untagged[:10]
        result["total_sampled"] = len(resources)
        result["untagged_count"] = len(untagged)

    except Exception as e:
        result["error"] = str(e)

    return result


@tool
def check_control_plane_separation() -> dict:
    """Assess control plane vs data plane separation patterns.

    Checks for: separate IAM roles for admin vs application, API Gateway stages,
    Lambda function separation, and account structure.

    Returns:
        Dictionary with control plane separation indicators.
    """
    result = {}
    iam = boto3.client("iam")

    # IAM role analysis — look for admin vs app role separation
    try:
        roles = iam.list_roles(MaxItems=100).get("Roles", [])
        admin_roles = [r for r in roles if any(k in r["RoleName"].lower() for k in ("admin", "management", "control", "platform"))]
        app_roles = [r for r in roles if any(k in r["RoleName"].lower() for k in ("app", "service", "worker", "data", "tenant", "execution"))]
        aws_service_roles = [r for r in roles if r["Path"].startswith("/aws-service-role/")]

        result["iam_roles"] = {
            "total": len(roles),
            "admin_pattern_roles": len(admin_roles),
            "app_pattern_roles": len(app_roles),
            "aws_service_roles": len(aws_service_roles),
            "separation_detected": len(admin_roles) > 0 and len(app_roles) > 0,
        }
    except Exception:
        result["iam_roles"] = {"total": 0}

    # API Gateway — stages and usage plans (multi-tenant API patterns)
    apigw = boto3.client("apigateway")
    try:
        apis = apigw.get_rest_apis().get("items", [])
        usage_plans = apigw.get_usage_plans().get("items", [])
        api_keys = apigw.get_api_keys().get("items", [])
        result["api_gateway"] = {
            "rest_apis": len(apis),
            "usage_plans": len(usage_plans),
            "api_keys": len(api_keys),
            "has_tenant_plans": len(usage_plans) > 1,
        }
    except Exception:
        result["api_gateway"] = {"rest_apis": 0, "usage_plans": 0}

    # Lambda — check for per-tenant vs shared function patterns
    lam = boto3.client("lambda")
    try:
        functions = lam.list_functions(MaxItems=50).get("Functions", [])
        func_names = [f["FunctionName"] for f in functions]
        # Look for patterns suggesting per-tenant functions
        tenant_funcs = [f for f in func_names if any(k in f.lower() for k in ("tenant", "customer", "client"))]
        result["lambda"] = {
            "total_functions": len(functions),
            "tenant_pattern_functions": len(tenant_funcs),
            "names_sample": func_names[:10],
        }
    except Exception:
        result["lambda"] = {"total_functions": 0}

    # AWS Organizations (account-level isolation)
    orgs = boto3.client("organizations")
    try:
        org = orgs.describe_organization().get("Organization", {})
        accounts = orgs.list_accounts().get("Accounts", [])
        result["organizations"] = {
            "is_org_member": True,
            "master_account": org.get("MasterAccountId", ""),
            "total_accounts": len(accounts),
            "account_level_isolation": len(accounts) > 1,
        }
    except Exception:
        result["organizations"] = {"is_org_member": False, "total_accounts": 1}

    return result


@tool
def check_cost_allocation_tags() -> dict:
    """Check cost allocation tag configuration for per-tenant cost attribution.

    Returns:
        Dictionary with active cost allocation tags and billing configuration.
    """
    result = {}
    ce = boto3.client("ce")

    # Cost allocation tags
    try:
        tags = ce.list_cost_allocation_tags(Status="Active", MaxResults=100).get("CostAllocationTags", [])
        result["active_cost_allocation_tags"] = [{"key": t["TagKey"], "type": t["Type"], "status": t["Status"]} for t in tags]
        result["total_active"] = len(tags)

        # Check if tenant-related tags are activated for billing
        tenant_billing_tags = [t for t in tags if t["TagKey"].lower() in ("tenant", "tenantid", "customer", "team", "project", "environment")]
        result["tenant_billing_tags"] = [t["TagKey"] for t in tenant_billing_tags]
        result["has_tenant_cost_allocation"] = len(tenant_billing_tags) > 0
    except Exception as e:
        result["active_cost_allocation_tags"] = []
        result["total_active"] = 0
        result["has_tenant_cost_allocation"] = False
        result["note"] = f"Could not access cost allocation tags: {e}"

    return result


@tool
def check_tenant_observability() -> dict:
    """Check if observability is configured for per-tenant monitoring (CloudWatch dimensions, log groups, dashboards).

    Returns:
        Dictionary with tenant-aware observability configuration.
    """
    result = {}
    cw = boto3.client("cloudwatch")
    logs = boto3.client("logs")

    # CloudWatch dashboards — look for tenant-specific ones
    try:
        dashboards = cw.list_dashboards().get("DashboardEntries", [])
        tenant_dashboards = [d for d in dashboards if any(k in d["DashboardName"].lower() for k in ("tenant", "customer", "client"))]
        result["dashboards"] = {
            "total": len(dashboards),
            "tenant_specific": len(tenant_dashboards),
            "names": [d["DashboardName"] for d in dashboards[:10]],
        }
    except Exception:
        result["dashboards"] = {"total": 0}

    # CloudWatch alarms — check for tenant-scoped alarms
    try:
        alarms = cw.describe_alarms(MaxRecords=100).get("MetricAlarms", [])
        tenant_alarms = [a for a in alarms if any(k in a["AlarmName"].lower() for k in ("tenant", "customer", "client"))]
        # Check dimensions for tenant-based metrics
        tenant_dimensions = set()
        for a in alarms:
            for d in a.get("Dimensions", []):
                if d["Name"].lower() in ("tenant", "tenantid", "customer"):
                    tenant_dimensions.add(d["Name"])
        result["alarms"] = {
            "total": len(alarms),
            "tenant_scoped": len(tenant_alarms),
            "tenant_dimensions_found": list(tenant_dimensions),
        }
    except Exception:
        result["alarms"] = {"total": 0}

    # Log groups — check for per-tenant log isolation
    try:
        log_groups = logs.describe_log_groups(limit=50).get("logGroups", [])
        tenant_logs = [lg for lg in log_groups if any(k in lg["logGroupName"].lower() for k in ("tenant", "customer", "client"))]
        result["log_groups"] = {
            "total": len(log_groups),
            "tenant_specific": len(tenant_logs),
            "sample_names": [lg["logGroupName"] for lg in log_groups[:10]],
        }
    except Exception:
        result["log_groups"] = {"total": 0}

    return result
