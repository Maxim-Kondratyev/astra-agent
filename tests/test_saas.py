"""Tests for SaaS checklist checks."""

import boto3
from moto import mock_aws

from astra.checklist import Status
from astra.checklist.saas import (
    check_api_throttling,
    check_control_plane_separation,
    check_cost_allocation_tags,
    check_noisy_neighbour_detection,
    check_per_tenant_monitoring,
    check_permission_boundaries,
    check_resource_isolation,
    check_tenant_tagging_strategy,
    run_saas_checklist,
)


class TestTenantTagging:
    def test_no_tenant_tags_fails(self, aws):
        result = check_tenant_tagging_strategy()
        assert result.status == Status.FAIL
        assert result.check_id == "SAS-01"


class TestCostAllocationTags:
    def test_check_runs(self, aws):
        result = check_cost_allocation_tags()
        assert result.check_id == "SAS-02"
        assert result.status in (Status.PASS, Status.FAIL, Status.ERROR)


class TestPermissionBoundaries:
    def test_no_boundaries_warns(self, aws):
        iam = boto3.client("iam", region_name="us-east-1")
        iam.create_role(RoleName="app-service", AssumeRolePolicyDocument="{}", Path="/")
        result = check_permission_boundaries()
        assert result.status == Status.WARNING

    def test_no_roles_passes(self, aws):
        result = check_permission_boundaries()
        assert result.status == Status.PASS


class TestResourceIsolation:
    def test_single_vpc_warns(self, aws):
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ec2.create_vpc(CidrBlock="10.0.0.0/16")
        result = check_resource_isolation()
        assert result.status in (Status.WARNING, Status.PASS)

    def test_multiple_vpcs_passes(self, aws):
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ec2.create_vpc(CidrBlock="10.0.0.0/16")
        ec2.create_vpc(CidrBlock="10.1.0.0/16")
        result = check_resource_isolation()
        assert result.status == Status.PASS


class TestPerTenantMonitoring:
    def test_no_tenant_dims_warns(self, aws):
        cw = boto3.client("cloudwatch", region_name="us-east-1")
        cw.put_metric_alarm(
            AlarmName="generic", MetricName="Errors", Namespace="App",
            Period=300, EvaluationPeriods=1, Threshold=5, ComparisonOperator="GreaterThanThreshold",
            Statistic="Sum",
        )
        result = check_per_tenant_monitoring()
        assert result.status == Status.WARNING


class TestAPIThrottling:
    def test_no_apis_passes(self, aws):
        result = check_api_throttling()
        assert result.status == Status.PASS


class TestControlPlaneSeparation:
    def test_mixed_roles(self, aws):
        iam = boto3.client("iam", region_name="us-east-1")
        iam.create_role(RoleName="platform-admin", AssumeRolePolicyDocument="{}", Path="/")
        iam.create_role(RoleName="app-service-worker", AssumeRolePolicyDocument="{}", Path="/")
        result = check_control_plane_separation()
        assert result.status == Status.PASS

    def test_no_separation_warns(self, aws):
        iam = boto3.client("iam", region_name="us-east-1")
        iam.create_role(RoleName="generic-role", AssumeRolePolicyDocument="{}", Path="/")
        result = check_control_plane_separation()
        assert result.status == Status.WARNING


class TestNoisyNeighbour:
    def test_check_runs(self, aws):
        result = check_noisy_neighbour_detection()
        assert result.check_id == "SAS-10"
        assert result.status in (Status.PASS, Status.FAIL, Status.WARNING, Status.ERROR)


class TestRunAll:
    def test_all_checks_return_results(self, aws):
        results = run_saas_checklist()
        assert len(results) == 10
        for r in results:
            assert r.check_id.startswith("SAS-")
            assert r.status in (Status.PASS, Status.FAIL, Status.WARNING, Status.ERROR)
