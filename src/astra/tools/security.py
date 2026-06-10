"""Security assessment tools — read-only AWS API queries."""

import boto3
from strands import tool


@tool
def get_security_hub_findings(severity: str = "HIGH", max_results: int = 100) -> dict:
    """Retrieve active Security Hub findings filtered by severity.

    Args:
        severity: Minimum severity to return. One of CRITICAL, HIGH, MEDIUM, LOW, INFORMATIONAL.
        max_results: Maximum number of findings to return (1-100).

    Returns:
        Dictionary with finding_count and findings list.
    """
    client = boto3.client("securityhub")
    severity_order = ["INFORMATIONAL", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    try:
        min_idx = severity_order.index(severity.upper())
    except ValueError:
        min_idx = 3
    included = severity_order[min_idx:]

    try:
        response = client.get_findings(
            Filters={
                "SeverityLabel": [{"Value": s, "Comparison": "EQUALS"} for s in included],
                "WorkflowStatus": [{"Value": "NEW", "Comparison": "EQUALS"}],
                "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
            },
            MaxResults=min(max_results, 100),
        )
    except client.exceptions.InvalidAccessException:
        return {"error": "Security Hub is not enabled in this region.", "finding_count": 0, "findings": []}

    findings = []
    for f in response.get("Findings", []):
        findings.append({
            "title": f.get("Title", ""),
            "severity": f.get("Severity", {}).get("Label", ""),
            "compliance_status": f.get("Compliance", {}).get("Status", ""),
            "resources": [{"type": r.get("Type", ""), "id": r.get("Id", "")} for r in f.get("Resources", [])],
            "remediation": f.get("Remediation", {}).get("Recommendation", {}).get("Text", ""),
            "standard": f.get("GeneratorId", ""),
        })
    return {"finding_count": len(findings), "findings": findings}


@tool
def get_guardduty_findings(max_results: int = 50) -> dict:
    """Retrieve active GuardDuty threat findings.

    Args:
        max_results: Maximum number of findings to return.

    Returns:
        Dictionary with detector status, finding_count, and findings list.
    """
    client = boto3.client("guardduty")
    try:
        detectors = client.list_detectors()
    except Exception as e:
        return {"error": f"GuardDuty not accessible: {e}", "finding_count": 0, "findings": []}

    detector_ids = detectors.get("DetectorIds", [])
    if not detector_ids:
        return {"enabled": False, "finding_count": 0, "findings": [], "message": "GuardDuty is not enabled."}

    detector_id = detector_ids[0]
    finding_ids_resp = client.list_findings(
        DetectorId=detector_id,
        FindingCriteria={"Criterion": {"service.archived": {"Eq": ["false"]}}},
        MaxResults=min(max_results, 50),
    )
    finding_ids = finding_ids_resp.get("FindingIds", [])
    if not finding_ids:
        return {"enabled": True, "finding_count": 0, "findings": [], "message": "No active findings."}

    details = client.get_findings(DetectorId=detector_id, FindingIds=finding_ids)
    findings = []
    for f in details.get("Findings", []):
        findings.append({
            "title": f.get("Title", ""),
            "severity": f.get("Severity", 0),
            "type": f.get("Type", ""),
            "description": f.get("Description", ""),
            "resource_type": f.get("Resource", {}).get("ResourceType", ""),
            "updated_at": f.get("UpdatedAt", ""),
        })
    return {"enabled": True, "finding_count": len(findings), "findings": findings}


@tool
def check_iam_password_policy() -> dict:
    """Check the account IAM password policy and root account MFA status.

    Returns:
        Dictionary with password policy settings and root MFA status.
    """
    iam = boto3.client("iam")
    result = {}

    # Password policy
    try:
        policy = iam.get_account_password_policy()["PasswordPolicy"]
        result["password_policy"] = {
            "minimum_length": policy.get("MinimumPasswordLength", 0),
            "require_uppercase": policy.get("RequireUppercaseCharacters", False),
            "require_lowercase": policy.get("RequireLowercaseCharacters", False),
            "require_numbers": policy.get("RequireNumbers", False),
            "require_symbols": policy.get("RequireSymbols", False),
            "max_age_days": policy.get("MaxPasswordAge", None),
            "password_reuse_prevention": policy.get("PasswordReusePrevention", None),
        }
    except iam.exceptions.NoSuchEntityException:
        result["password_policy"] = {"error": "No custom password policy set — using AWS defaults (weak)."}

    # Account summary for root MFA
    summary = iam.get_account_summary()["SummaryMap"]
    result["root_mfa_enabled"] = summary.get("AccountMFAEnabled", 0) == 1
    result["access_keys_total"] = summary.get("AccessKeysPerUserQuota", 0)
    result["mfa_devices_total"] = summary.get("MFADevices", 0)
    result["users_total"] = summary.get("Users", 0)

    return result


@tool
def check_s3_public_access() -> dict:
    """Check S3 buckets for public access settings and policies.

    Returns:
        Dictionary with account-level block settings and per-bucket public access status.
    """
    s3control = boto3.client("s3control")
    s3 = boto3.client("s3")
    sts = boto3.client("sts")
    account_id = sts.get_caller_identity()["Account"]

    result = {"account_id": account_id}

    # Account-level public access block
    try:
        acct_block = s3control.get_public_access_block(AccountId=account_id)["PublicAccessBlockConfiguration"]
        result["account_public_access_block"] = {
            "block_public_acls": acct_block.get("BlockPublicAcls", False),
            "ignore_public_acls": acct_block.get("IgnorePublicAcls", False),
            "block_public_policy": acct_block.get("BlockPublicPolicy", False),
            "restrict_public_buckets": acct_block.get("RestrictPublicBuckets", False),
        }
        all_blocked = all(result["account_public_access_block"].values())
        result["account_fully_blocked"] = all_blocked
    except Exception:
        result["account_public_access_block"] = None
        result["account_fully_blocked"] = False

    # Per-bucket check (sample up to 20 buckets)
    buckets = s3.list_buckets().get("Buckets", [])[:20]
    public_buckets = []
    for b in buckets:
        name = b["Name"]
        try:
            pab = s3.get_public_access_block(Bucket=name)["PublicAccessBlockConfiguration"]
            if not all(pab.values()):
                public_buckets.append({"bucket": name, "block_config": pab})
        except s3.exceptions.ClientError:
            # No block config = potentially public
            public_buckets.append({"bucket": name, "block_config": None})

    result["potentially_public_buckets"] = public_buckets
    result["buckets_checked"] = len(buckets)
    return result


@tool
def check_encryption_at_rest() -> dict:
    """Audit encryption at rest for S3 buckets, EBS volumes, and RDS instances.

    Returns:
        Dictionary with encryption status for each service.
    """
    result = {}

    # S3 bucket encryption
    s3 = boto3.client("s3")
    buckets = s3.list_buckets().get("Buckets", [])[:20]
    s3_results = []
    for b in buckets:
        name = b["Name"]
        try:
            enc = s3.get_bucket_encryption(Bucket=name)
            rules = enc.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
            algo = rules[0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] if rules else "NONE"
            s3_results.append({"bucket": name, "encrypted": True, "algorithm": algo})
        except s3.exceptions.ClientError:
            s3_results.append({"bucket": name, "encrypted": False, "algorithm": "NONE"})
    result["s3"] = {"checked": len(s3_results), "unencrypted": [b for b in s3_results if not b["encrypted"]]}

    # EBS volumes
    ec2 = boto3.client("ec2")
    volumes = ec2.describe_volumes(MaxResults=100).get("Volumes", [])
    unencrypted_ebs = [{"volume_id": v["VolumeId"], "size_gb": v["Size"], "state": v["State"]}
                       for v in volumes if not v.get("Encrypted", False)]
    result["ebs"] = {"total": len(volumes), "unencrypted_count": len(unencrypted_ebs), "unencrypted": unencrypted_ebs[:20]}

    # RDS instances
    rds = boto3.client("rds")
    try:
        instances = rds.describe_db_instances().get("DBInstances", [])
        unencrypted_rds = [{"db_id": db["DBInstanceIdentifier"], "engine": db["Engine"]}
                          for db in instances if not db.get("StorageEncrypted", False)]
        result["rds"] = {"total": len(instances), "unencrypted_count": len(unencrypted_rds), "unencrypted": unencrypted_rds}
    except Exception:
        result["rds"] = {"total": 0, "unencrypted_count": 0, "unencrypted": [], "note": "No RDS instances found."}

    return result
