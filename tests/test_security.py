"""Tests for Security checklist checks."""

import boto3
from moto import mock_aws

from astra.checklist import Status
from astra.checklist.security import (
    check_cloudtrail_enabled,
    check_ebs_encryption_default,
    check_guardduty_enabled,
    check_iam_access_analyzer,
    check_iam_password_policy,
    check_root_mfa,
    check_s3_account_public_access_block,
    check_security_groups_open,
    check_security_hub_enabled,
    check_vpc_flow_logs,
    run_security_checklist,
)


class TestSecurityHub:
    def test_not_enabled(self, aws):
        # SecurityHub not enabled → FAIL
        result = check_security_hub_enabled()
        assert result.status in (Status.FAIL, Status.ERROR)
        assert result.check_id == "SEC-01"


class TestGuardDuty:
    def test_not_enabled(self, aws):
        result = check_guardduty_enabled()
        # No detectors → FAIL
        assert result.status == Status.FAIL
        assert result.check_id == "SEC-02"

    def test_enabled(self, aws):
        gd = boto3.client("guardduty", region_name="us-east-1")
        gd.create_detector(Enable=True)
        result = check_guardduty_enabled()
        assert result.status == Status.PASS


class TestRootMFA:
    def test_check_runs(self, aws):
        # moto doesn't fully support account summary MFA, but check shouldn't crash
        result = check_root_mfa()
        assert result.check_id == "SEC-03"
        assert result.status in (Status.PASS, Status.FAIL, Status.ERROR)


class TestPasswordPolicy:
    def test_no_policy(self, aws):
        result = check_iam_password_policy()
        assert result.status == Status.FAIL
        assert "password policy" in result.recommendation.lower()

    def test_weak_policy(self, aws):
        iam = boto3.client("iam", region_name="us-east-1")
        iam.update_account_password_policy(MinimumPasswordLength=8, RequireSymbols=False)
        result = check_iam_password_policy()
        assert result.status == Status.WARNING

    def test_strong_policy(self, aws):
        iam = boto3.client("iam", region_name="us-east-1")
        iam.update_account_password_policy(
            MinimumPasswordLength=14, RequireSymbols=True, MaxPasswordAge=90,
            RequireNumbers=True, RequireUppercaseCharacters=True, RequireLowercaseCharacters=True,
        )
        result = check_iam_password_policy()
        assert result.status == Status.PASS


class TestS3PublicAccessBlock:
    def test_not_set(self, aws):
        result = check_s3_account_public_access_block()
        assert result.status == Status.FAIL
        assert result.check_id == "SEC-05"

    def test_fully_blocked(self, aws):
        s3control = boto3.client("s3control", region_name="us-east-1")
        sts = boto3.client("sts", region_name="us-east-1")
        account_id = sts.get_caller_identity()["Account"]
        s3control.put_public_access_block(
            AccountId=account_id,
            PublicAccessBlockConfiguration={
                "BlockPublicAcls": True, "IgnorePublicAcls": True,
                "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
            },
        )
        result = check_s3_account_public_access_block()
        assert result.status == Status.PASS


class TestCloudTrail:
    def test_no_trail(self, aws):
        result = check_cloudtrail_enabled()
        assert result.status == Status.FAIL

    def test_multi_region_trail(self, aws):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="trail-bucket")
        ct = boto3.client("cloudtrail", region_name="us-east-1")
        ct.create_trail(Name="main", S3BucketName="trail-bucket", IsMultiRegionTrail=True)
        result = check_cloudtrail_enabled()
        assert result.status == Status.PASS


class TestVPCFlowLogs:
    def test_no_flow_logs(self, aws):
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ec2.create_vpc(CidrBlock="10.0.0.0/16")
        result = check_vpc_flow_logs()
        assert result.status == Status.FAIL
        assert result.affected_resources


class TestSecurityGroups:
    def test_open_sg(self, aws):
        ec2 = boto3.client("ec2", region_name="us-east-1")
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        sg = ec2.create_security_group(GroupName="open", Description="t", VpcId=vpc["Vpc"]["VpcId"])
        ec2.authorize_security_group_ingress(
            GroupId=sg["GroupId"],
            IpPermissions=[{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
        )
        result = check_security_groups_open()
        assert result.status == Status.FAIL

    def test_restricted_sg(self, aws):
        ec2 = boto3.client("ec2", region_name="us-east-1")
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        ec2.create_security_group(GroupName="safe", Description="t", VpcId=vpc["Vpc"]["VpcId"])
        result = check_security_groups_open()
        assert result.status == Status.PASS


class TestIAMAccessAnalyzer:
    def test_not_enabled(self, aws):
        result = check_iam_access_analyzer()
        # moto doesn't support Access Analyzer, so this returns ERROR or FAIL
        assert result.check_id == "SEC-09"
        assert result.status in (Status.FAIL, Status.ERROR)


class TestEBSEncryption:
    def test_check_runs(self, aws):
        result = check_ebs_encryption_default()
        assert result.check_id == "SEC-10"
        assert result.status in (Status.PASS, Status.FAIL)


class TestRunAll:
    def test_all_checks_return_results(self, aws):
        results = run_security_checklist()
        assert len(results) == 12
        for r in results:
            assert r.check_id.startswith("SEC-")
            assert r.status in (Status.PASS, Status.FAIL, Status.WARNING, Status.ERROR)
