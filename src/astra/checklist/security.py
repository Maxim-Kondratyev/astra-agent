"""Security checklist — prebuilt Well-Architected Security Pillar checks.

Maps to SEC questions: SEC 1 (governance), SEC 2 (identity), SEC 3 (permissions),
SEC 4 (detection), SEC 5 (network), SEC 6 (compute), SEC 7 (data at rest),
SEC 8 (data in transit), SEC 9 (incident response).
"""

import boto3

from astra.checklist.resilience import CheckResult, Status


def check_security_hub_enabled() -> CheckResult:
    """SEC-01: Security Hub should be enabled for centralized security findings."""
    client = boto3.client("securityhub")
    try:
        hub = client.describe_hub()
        return CheckResult("SEC-01", "Security Hub enabled", Status.PASS, evidence={"hub_arn": hub.get("HubArn", "")})
    except client.exceptions.InvalidAccessException:
        return CheckResult(
            "SEC-01", "Security Hub enabled", Status.FAIL,
            recommendation="Enable Security Hub to aggregate findings from GuardDuty, Inspector, IAM Access Analyzer, and Config.",
            wa_reference="SEC 4 – How do you detect and investigate security events?",
        )
    except Exception as e:
        return CheckResult("SEC-01", "Security Hub enabled", Status.ERROR, evidence={"error": str(e)})


def check_guardduty_enabled() -> CheckResult:
    """SEC-02: GuardDuty should be enabled for threat detection."""
    client = boto3.client("guardduty")
    try:
        detectors = client.list_detectors().get("DetectorIds", [])
        if not detectors:
            return CheckResult(
                "SEC-02", "GuardDuty enabled", Status.FAIL,
                recommendation="Enable GuardDuty for continuous threat detection (malicious activity, unauthorized behavior).",
                wa_reference="SEC 4 – How do you detect and investigate security events?",
            )
        det = client.get_detector(DetectorId=detectors[0])
        if det.get("Status") != "ENABLED":
            return CheckResult("SEC-02", "GuardDuty enabled", Status.FAIL, evidence={"status": det.get("Status")},
                             recommendation="Re-enable GuardDuty — it is currently disabled.",
                             wa_reference="SEC 4 – How do you detect and investigate security events?")
        return CheckResult("SEC-02", "GuardDuty enabled", Status.PASS, evidence={"detector_id": detectors[0]})
    except Exception as e:
        return CheckResult("SEC-02", "GuardDuty enabled", Status.ERROR, evidence={"error": str(e)})


def check_root_mfa() -> CheckResult:
    """SEC-03: Root account must have MFA enabled."""
    iam = boto3.client("iam")
    try:
        summary = iam.get_account_summary()["SummaryMap"]
        if summary.get("AccountMFAEnabled", 0) == 1:
            return CheckResult("SEC-03", "Root account MFA", Status.PASS)
        return CheckResult(
            "SEC-03", "Root account MFA", Status.FAIL,
            recommendation="Enable MFA on the root account immediately. Use a hardware MFA device for highest security.",
            wa_reference="SEC 2 – How do you manage identities for people and machines?",
        )
    except Exception as e:
        return CheckResult("SEC-03", "Root account MFA", Status.ERROR, evidence={"error": str(e)})


def check_iam_password_policy() -> CheckResult:
    """SEC-04: IAM password policy should enforce strong passwords."""
    iam = boto3.client("iam")
    try:
        policy = iam.get_account_password_policy()["PasswordPolicy"]
        issues = []
        if policy.get("MinimumPasswordLength", 0) < 14:
            issues.append(f"min length {policy.get('MinimumPasswordLength', 0)} (should be ≥14)")
        if not policy.get("RequireSymbols"):
            issues.append("symbols not required")
        if not policy.get("MaxPasswordAge"):
            issues.append("no password expiry")
        if issues:
            return CheckResult("SEC-04", "IAM password policy", Status.WARNING,
                             evidence={"issues": issues, "policy": policy},
                             recommendation=f"Strengthen password policy: {'; '.join(issues)}.",
                             wa_reference="SEC 2 – How do you manage identities for people and machines?")
        return CheckResult("SEC-04", "IAM password policy", Status.PASS, evidence={"policy": policy})
    except iam.exceptions.NoSuchEntityException:
        return CheckResult("SEC-04", "IAM password policy", Status.FAIL,
                         recommendation="Set a custom IAM password policy (≥14 chars, symbols, rotation).",
                         wa_reference="SEC 2 – How do you manage identities for people and machines?")
    except Exception as e:
        return CheckResult("SEC-04", "IAM password policy", Status.ERROR, evidence={"error": str(e)})


def check_s3_account_public_access_block() -> CheckResult:
    """SEC-05: S3 account-level public access block should be fully enabled."""
    s3control = boto3.client("s3control")
    sts = boto3.client("sts")
    try:
        account_id = sts.get_caller_identity()["Account"]
        block = s3control.get_public_access_block(AccountId=account_id)["PublicAccessBlockConfiguration"]
        if all(block.values()):
            return CheckResult("SEC-05", "S3 public access block", Status.PASS)
        disabled = [k for k, v in block.items() if not v]
        return CheckResult("SEC-05", "S3 public access block", Status.FAIL,
                         evidence={"disabled_settings": disabled},
                         recommendation="Enable all 4 S3 account-level public access block settings.",
                         wa_reference="SEC 7 – How do you protect your data at rest?")
    except Exception:
        return CheckResult("SEC-05", "S3 public access block", Status.FAIL,
                         recommendation="Configure S3 account-level public access block (currently not set).",
                         wa_reference="SEC 7 – How do you protect your data at rest?")


def check_cloudtrail_enabled() -> CheckResult:
    """SEC-06: CloudTrail should be enabled with multi-region trail."""
    ct = boto3.client("cloudtrail")
    try:
        trails = ct.describe_trails().get("trailList", [])
        if not trails:
            return CheckResult("SEC-06", "CloudTrail enabled", Status.FAIL,
                             recommendation="Create a CloudTrail trail with multi-region enabled for audit logging.",
                             wa_reference="SEC 4 – How do you detect and investigate security events?")
        multi_region = [t for t in trails if t.get("IsMultiRegionTrail")]
        if not multi_region:
            return CheckResult("SEC-06", "CloudTrail enabled", Status.WARNING,
                             evidence={"trails": len(trails), "multi_region": 0},
                             recommendation="Enable multi-region on your CloudTrail trail to capture events in all regions.",
                             wa_reference="SEC 4 – How do you detect and investigate security events?")
        return CheckResult("SEC-06", "CloudTrail enabled", Status.PASS, evidence={"multi_region_trails": len(multi_region)})
    except Exception as e:
        return CheckResult("SEC-06", "CloudTrail enabled", Status.ERROR, evidence={"error": str(e)})


def check_vpc_flow_logs() -> CheckResult:
    """SEC-07: VPCs should have flow logs enabled for network monitoring."""
    ec2 = boto3.client("ec2")
    try:
        vpcs = ec2.describe_vpcs().get("Vpcs", [])
        if not vpcs:
            return CheckResult("SEC-07", "VPC flow logs", Status.PASS, evidence={"detail": "No VPCs."})
        vpc_ids = [v["VpcId"] for v in vpcs if not v.get("IsDefault")]
        if not vpc_ids:
            vpc_ids = [v["VpcId"] for v in vpcs]
        flow_logs = ec2.describe_flow_logs(Filters=[{"Name": "resource-id", "Values": vpc_ids}]).get("FlowLogs", [])
        covered_vpcs = {fl["ResourceId"] for fl in flow_logs}
        uncovered = [v for v in vpc_ids if v not in covered_vpcs]
        if uncovered:
            return CheckResult("SEC-07", "VPC flow logs", Status.FAIL,
                             evidence={"vpcs_without_flow_logs": uncovered},
                             affected_resources=uncovered,
                             recommendation="Enable VPC Flow Logs for all non-default VPCs (send to CloudWatch Logs or S3).",
                             wa_reference="SEC 5 – How do you protect your network resources?")
        return CheckResult("SEC-07", "VPC flow logs", Status.PASS, evidence={"all_vpcs_covered": True})
    except Exception as e:
        return CheckResult("SEC-07", "VPC flow logs", Status.ERROR, evidence={"error": str(e)})


def check_security_groups_open() -> CheckResult:
    """SEC-08: Security groups should not allow unrestricted inbound access (0.0.0.0/0)."""
    ec2 = boto3.client("ec2")
    try:
        sgs = ec2.describe_security_groups().get("SecurityGroups", [])
        open_sgs = []
        for sg in sgs:
            for rule in sg.get("IpPermissions", []):
                for ip_range in rule.get("IpRanges", []):
                    if ip_range.get("CidrIp") == "0.0.0.0/0" and rule.get("FromPort") not in (80, 443):
                        open_sgs.append({"sg_id": sg["GroupId"], "name": sg.get("GroupName", ""), "port": rule.get("FromPort")})
                        break
        if open_sgs:
            return CheckResult("SEC-08", "Security groups open access", Status.FAIL,
                             evidence={"open_security_groups": open_sgs[:10]},
                             affected_resources=[s["sg_id"] for s in open_sgs[:10]],
                             recommendation="Restrict security group rules — only allow 0.0.0.0/0 for ports 80/443. Use specific CIDR blocks for other ports.",
                             wa_reference="SEC 5 – How do you protect your network resources?")
        return CheckResult("SEC-08", "Security groups open access", Status.PASS, evidence={"checked": len(sgs)})
    except Exception as e:
        return CheckResult("SEC-08", "Security groups open access", Status.ERROR, evidence={"error": str(e)})


def check_iam_access_analyzer() -> CheckResult:
    """SEC-09: IAM Access Analyzer should be enabled to detect external access."""
    client = boto3.client("accessanalyzer")
    try:
        analyzers = client.list_analyzers(Type="ACCOUNT").get("analyzers", [])
        if not analyzers:
            return CheckResult("SEC-09", "IAM Access Analyzer", Status.FAIL,
                             recommendation="Enable IAM Access Analyzer to detect resources shared with external entities.",
                             wa_reference="SEC 3 – How do you manage permissions for people and machines?")
        active = [a for a in analyzers if a.get("status") == "ACTIVE"]
        if not active:
            return CheckResult("SEC-09", "IAM Access Analyzer", Status.WARNING,
                             evidence={"analyzers": len(analyzers), "active": 0},
                             recommendation="Ensure at least one IAM Access Analyzer is in ACTIVE status.",
                             wa_reference="SEC 3 – How do you manage permissions for people and machines?")
        return CheckResult("SEC-09", "IAM Access Analyzer", Status.PASS, evidence={"active_analyzers": len(active)})
    except Exception as e:
        return CheckResult("SEC-09", "IAM Access Analyzer", Status.ERROR, evidence={"error": str(e)})


def check_ebs_encryption_default() -> CheckResult:
    """SEC-10: EBS default encryption should be enabled."""
    ec2 = boto3.client("ec2")
    try:
        resp = ec2.get_ebs_encryption_by_default()
        if resp.get("EbsEncryptionByDefault"):
            return CheckResult("SEC-10", "EBS default encryption", Status.PASS)
        return CheckResult("SEC-10", "EBS default encryption", Status.FAIL,
                         recommendation="Enable EBS encryption by default so all new volumes are automatically encrypted.",
                         wa_reference="SEC 7 – How do you protect your data at rest?")
    except Exception as e:
        return CheckResult("SEC-10", "EBS default encryption", Status.ERROR, evidence={"error": str(e)})


def check_secrets_rotation() -> CheckResult:
    """SEC-11: Secrets Manager secrets should have rotation enabled."""
    sm = boto3.client("secretsmanager")
    try:
        secrets = sm.list_secrets(MaxResults=100).get("SecretList", [])
        if not secrets:
            return CheckResult("SEC-11", "Secrets rotation", Status.PASS, evidence={"detail": "No secrets found."})
        no_rotation = [s["Name"] for s in secrets if not s.get("RotationEnabled")]
        if len(no_rotation) > len(secrets) * 0.5:
            return CheckResult("SEC-11", "Secrets rotation", Status.WARNING,
                             evidence={"total": len(secrets), "without_rotation": len(no_rotation), "sample": no_rotation[:5]},
                             affected_resources=no_rotation[:10],
                             recommendation="Enable automatic rotation for secrets (especially database credentials).",
                             wa_reference="SEC 2 – How do you manage identities for people and machines?")
        return CheckResult("SEC-11", "Secrets rotation", Status.PASS, evidence={"total": len(secrets), "with_rotation": len(secrets) - len(no_rotation)})
    except Exception as e:
        return CheckResult("SEC-11", "Secrets rotation", Status.ERROR, evidence={"error": str(e)})


def check_kms_key_rotation() -> CheckResult:
    """SEC-12: Customer-managed KMS keys should have automatic rotation enabled."""
    kms = boto3.client("kms")
    try:
        keys = kms.list_keys(Limit=100).get("Keys", [])
        if not keys:
            return CheckResult("SEC-12", "KMS key rotation", Status.PASS, evidence={"detail": "No KMS keys."})
        no_rotation = []
        for key in keys[:50]:
            try:
                meta = kms.describe_key(KeyId=key["KeyId"])["KeyMetadata"]
                if meta.get("KeyManager") == "CUSTOMER" and meta.get("KeyState") == "Enabled":
                    rot = kms.get_key_rotation_status(KeyId=key["KeyId"])
                    if not rot.get("KeyRotationEnabled"):
                        no_rotation.append(key["KeyId"])
            except Exception:
                continue
        if no_rotation:
            return CheckResult("SEC-12", "KMS key rotation", Status.WARNING,
                             evidence={"keys_without_rotation": no_rotation[:5]},
                             affected_resources=no_rotation[:5],
                             recommendation="Enable automatic annual rotation for customer-managed KMS keys.",
                             wa_reference="SEC 7 – How do you protect your data at rest?")
        return CheckResult("SEC-12", "KMS key rotation", Status.PASS, evidence={"all_rotated": True})
    except Exception as e:
        return CheckResult("SEC-12", "KMS key rotation", Status.ERROR, evidence={"error": str(e)})


ALL_CHECKS = [
    check_security_hub_enabled,
    check_guardduty_enabled,
    check_root_mfa,
    check_iam_password_policy,
    check_s3_account_public_access_block,
    check_cloudtrail_enabled,
    check_vpc_flow_logs,
    check_security_groups_open,
    check_iam_access_analyzer,
    check_ebs_encryption_default,
    check_secrets_rotation,
    check_kms_key_rotation,
]


def run_security_checklist() -> list[CheckResult]:
    """Run all prebuilt security checks."""
    results = []
    for check_fn in ALL_CHECKS:
        try:
            results.append(check_fn())
        except Exception as e:
            results.append(CheckResult(check_id="UNKNOWN", title=check_fn.__name__, status=Status.ERROR, evidence={"error": str(e)}))
    return results
