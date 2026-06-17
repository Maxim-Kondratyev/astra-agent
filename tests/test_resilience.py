"""Tests for Resilience checklist checks."""

import boto3
from moto import mock_aws

from astra.checklist import Status
from astra.checklist.resilience import (
    check_asg_health_checks,
    check_asg_multi_az,
    check_backup_plans_exist,
    check_cloudwatch_alarms,
    check_ebs_snapshots,
    check_ec2_az_spread,
    check_elb_multi_az,
    check_elasticache_multi_az,
    check_rds_backup_retention,
    check_rds_multi_az,
    check_route53_health_checks,
    check_single_nat_gateway,
    run_resilience_checklist,
)


class TestRDSMultiAZ:
    def test_single_az_fails(self, aws):
        rds = boto3.client("rds", region_name="us-east-1")
        rds.create_db_instance(
            DBInstanceIdentifier="single-db", DBInstanceClass="db.t3.micro",
            Engine="mysql", MasterUsername="a", MasterUserPassword="b", MultiAZ=False,
        )
        result = check_rds_multi_az()
        assert result.status == Status.FAIL
        assert "single-db" in result.affected_resources

    def test_multi_az_passes(self, aws):
        rds = boto3.client("rds", region_name="us-east-1")
        rds.create_db_instance(
            DBInstanceIdentifier="ha-db", DBInstanceClass="db.t3.micro",
            Engine="mysql", MasterUsername="a", MasterUserPassword="b", MultiAZ=True,
        )
        result = check_rds_multi_az()
        assert result.status == Status.PASS

    def test_no_instances_passes(self, aws):
        result = check_rds_multi_az()
        assert result.status == Status.PASS


class TestEC2AZSpread:
    def test_single_az_fails(self, aws):
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ec2.run_instances(ImageId="ami-12345", MinCount=3, MaxCount=3,
                         Placement={"AvailabilityZone": "us-east-1a"})
        result = check_ec2_az_spread()
        assert result.status == Status.FAIL

    def test_multi_az_passes(self, aws):
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ec2.run_instances(ImageId="ami-12345", MinCount=1, MaxCount=1,
                         Placement={"AvailabilityZone": "us-east-1a"})
        ec2.run_instances(ImageId="ami-12345", MinCount=1, MaxCount=1,
                         Placement={"AvailabilityZone": "us-east-1b"})
        result = check_ec2_az_spread()
        assert result.status == Status.PASS

    def test_no_instances_passes(self, aws):
        result = check_ec2_az_spread()
        assert result.status == Status.PASS


class TestASGHealthChecks:
    def test_no_asgs_passes(self, aws):
        result = check_asg_health_checks()
        assert result.status == Status.PASS


class TestASGMultiAZ:
    def test_no_asgs_passes(self, aws):
        result = check_asg_multi_az()
        assert result.status == Status.PASS


class TestELBMultiAZ:
    def test_single_az_fails(self, aws):
        ec2 = boto3.client("ec2", region_name="us-east-1")
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        sub = ec2.create_subnet(VpcId=vpc["Vpc"]["VpcId"], CidrBlock="10.0.1.0/24", AvailabilityZone="us-east-1a")
        elbv2 = boto3.client("elbv2", region_name="us-east-1")
        elbv2.create_load_balancer(Name="single-lb", Subnets=[sub["Subnet"]["SubnetId"]], Type="application")
        result = check_elb_multi_az()
        assert result.status == Status.FAIL
        assert "single-lb" in result.affected_resources

    def test_multi_az_passes(self, aws):
        ec2 = boto3.client("ec2", region_name="us-east-1")
        vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
        sub1 = ec2.create_subnet(VpcId=vpc["Vpc"]["VpcId"], CidrBlock="10.0.1.0/24", AvailabilityZone="us-east-1a")
        sub2 = ec2.create_subnet(VpcId=vpc["Vpc"]["VpcId"], CidrBlock="10.0.2.0/24", AvailabilityZone="us-east-1b")
        elbv2 = boto3.client("elbv2", region_name="us-east-1")
        elbv2.create_load_balancer(Name="ha-lb", Subnets=[sub1["Subnet"]["SubnetId"], sub2["Subnet"]["SubnetId"]], Type="application")
        result = check_elb_multi_az()
        assert result.status == Status.PASS

    def test_no_lbs_passes(self, aws):
        result = check_elb_multi_az()
        assert result.status == Status.PASS


class TestBackupPlans:
    def test_no_plans_fails(self, aws):
        result = check_backup_plans_exist()
        assert result.status == Status.FAIL

    def test_has_plan_passes(self, aws):
        backup = boto3.client("backup", region_name="us-east-1")
        backup.create_backup_plan(BackupPlan={"BackupPlanName": "daily", "Rules": [
            {"RuleName": "daily", "TargetBackupVaultName": "Default", "ScheduleExpression": "cron(0 12 * * ? *)"}
        ]})
        result = check_backup_plans_exist()
        assert result.status == Status.PASS


class TestRDSBackupRetention:
    def test_short_retention_warns(self, aws):
        rds = boto3.client("rds", region_name="us-east-1")
        rds.create_db_instance(
            DBInstanceIdentifier="low-backup", DBInstanceClass="db.t3.micro",
            Engine="mysql", MasterUsername="a", MasterUserPassword="b", BackupRetentionPeriod=3,
        )
        result = check_rds_backup_retention()
        assert result.status == Status.WARNING

    def test_good_retention_passes(self, aws):
        rds = boto3.client("rds", region_name="us-east-1")
        rds.create_db_instance(
            DBInstanceIdentifier="good-backup", DBInstanceClass="db.t3.micro",
            Engine="mysql", MasterUsername="a", MasterUserPassword="b", BackupRetentionPeriod=14,
        )
        result = check_rds_backup_retention()
        assert result.status == Status.PASS


class TestNATGateway:
    def test_no_nats_passes(self, aws):
        result = check_single_nat_gateway()
        assert result.status == Status.PASS


class TestEBSSnapshots:
    def test_check_runs(self, aws):
        result = check_ebs_snapshots()
        assert result.check_id == "REL-09"
        assert result.status in (Status.PASS, Status.FAIL, Status.WARNING, Status.ERROR)


class TestRoute53HealthChecks:
    def test_no_zones_passes(self, aws):
        result = check_route53_health_checks()
        assert result.status == Status.PASS


class TestElastiCacheMultiAZ:
    def test_no_groups_passes(self, aws):
        result = check_elasticache_multi_az()
        assert result.status == Status.PASS


class TestCloudWatchAlarms:
    def test_no_alarms_fails(self, aws):
        result = check_cloudwatch_alarms()
        assert result.status == Status.FAIL

    def test_has_alarms_passes(self, aws):
        cw = boto3.client("cloudwatch", region_name="us-east-1")
        cw.put_metric_alarm(
            AlarmName="cpu-high", MetricName="CPUUtilization", Namespace="AWS/EC2",
            Period=300, EvaluationPeriods=1, Threshold=80, ComparisonOperator="GreaterThanThreshold",
            Statistic="Average", AlarmActions=["arn:aws:sns:us-east-1:123456789:alerts"],
        )
        result = check_cloudwatch_alarms()
        assert result.status == Status.PASS


class TestRunAll:
    def test_all_checks_return_results(self, aws):
        results = run_resilience_checklist()
        assert len(results) == 12
        for r in results:
            assert r.check_id.startswith("REL-")
            assert r.status in (Status.PASS, Status.FAIL, Status.WARNING, Status.ERROR)
