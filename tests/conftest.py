"""Shared fixtures for ASTRA tests — simulates a realistic AWS account using moto."""

import json
import os

import boto3
import pytest
from moto import mock_aws


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    """Set fake AWS credentials for all tests."""
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "testing")
    monkeypatch.setenv("AWS_SECURITY_TOKEN", "testing")
    monkeypatch.setenv("AWS_SESSION_TOKEN", "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture
def aws():
    """Start moto mock for all AWS services."""
    with mock_aws():
        yield


@pytest.fixture
def aws_account_with_issues(aws):
    """Create a realistic AWS account with some good config and some issues.

    This simulates a customer account that has:
    - Some things done right (encryption on some resources, MFA on root)
    - Some things wrong (single-AZ RDS, no backup plans, open security groups)
    """
    region = "us-east-1"

    # --- EC2 ---
    ec2 = boto3.client("ec2", region_name=region)
    # Create a VPC
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    # Create subnets in 2 AZs
    sub1 = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24", AvailabilityZone="us-east-1a")
    sub2 = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.2.0/24", AvailabilityZone="us-east-1b")

    # Security group with open access (issue!)
    sg = ec2.create_security_group(GroupName="open-sg", Description="test", VpcId=vpc_id)
    ec2.authorize_security_group_ingress(
        GroupId=sg["GroupId"],
        IpPermissions=[{"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}],
    )

    # Run instances in single AZ only (issue!)
    ec2.run_instances(ImageId="ami-12345", MinCount=2, MaxCount=2, InstanceType="t3.micro",
                      Placement={"AvailabilityZone": "us-east-1a"})

    # --- RDS ---
    rds = boto3.client("rds", region_name=region)
    # Single-AZ instance (issue!)
    rds.create_db_instance(
        DBInstanceIdentifier="mydb-single-az",
        DBInstanceClass="db.t3.micro",
        Engine="mysql",
        MasterUsername="admin",
        MasterUserPassword="password123",
        MultiAZ=False,
        BackupRetentionPeriod=3,  # Too short (issue!)
    )
    # Multi-AZ instance (good)
    rds.create_db_instance(
        DBInstanceIdentifier="mydb-multi-az",
        DBInstanceClass="db.t3.micro",
        Engine="mysql",
        MasterUsername="admin",
        MasterUserPassword="password123",
        MultiAZ=True,
        BackupRetentionPeriod=14,
    )

    # --- S3 ---
    s3 = boto3.client("s3", region_name=region)
    s3.create_bucket(Bucket="my-data-bucket")
    s3.create_bucket(Bucket="my-logs-bucket")

    # --- IAM ---
    iam = boto3.client("iam", region_name=region)
    # Set a weak password policy (issue!)
    iam.update_account_password_policy(
        MinimumPasswordLength=8,
        RequireSymbols=False,
        RequireNumbers=True,
        RequireUppercaseCharacters=True,
        RequireLowercaseCharacters=True,
    )

    # --- CloudTrail ---
    ct = boto3.client("cloudtrail", region_name=region)
    ct.create_trail(Name="main-trail", S3BucketName="my-logs-bucket", IsMultiRegionTrail=True)

    # --- ELBv2 ---
    elbv2 = boto3.client("elbv2", region_name=region)
    # Single-AZ load balancer (issue!)
    elbv2.create_load_balancer(
        Name="my-single-az-lb",
        Subnets=[sub1["Subnet"]["SubnetId"]],
        Type="application",
    )

    return {
        "vpc_id": vpc_id,
        "subnet_ids": [sub1["Subnet"]["SubnetId"], sub2["Subnet"]["SubnetId"]],
        "region": region,
    }


@pytest.fixture
def aws_account_compliant(aws):
    """Create a well-configured AWS account that should pass most checks."""
    region = "us-east-1"

    ec2 = boto3.client("ec2", region_name=region)
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    sub1 = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24", AvailabilityZone="us-east-1a")
    sub2 = ec2.create_subnet(VpcId=vpc_id, CidrBlock="10.0.2.0/24", AvailabilityZone="us-east-1b")

    # Instances in multiple AZs (good)
    ec2.run_instances(ImageId="ami-12345", MinCount=1, MaxCount=1, InstanceType="t3.micro",
                      Placement={"AvailabilityZone": "us-east-1a"})
    ec2.run_instances(ImageId="ami-12345", MinCount=1, MaxCount=1, InstanceType="t3.micro",
                      Placement={"AvailabilityZone": "us-east-1b"})

    # Multi-AZ RDS
    rds = boto3.client("rds", region_name=region)
    rds.create_db_instance(
        DBInstanceIdentifier="prod-db",
        DBInstanceClass="db.t3.micro",
        Engine="mysql",
        MasterUsername="admin",
        MasterUserPassword="password123",
        MultiAZ=True,
        BackupRetentionPeriod=14,
    )

    # Strong password policy
    iam = boto3.client("iam", region_name=region)
    iam.update_account_password_policy(
        MinimumPasswordLength=14,
        RequireSymbols=True,
        RequireNumbers=True,
        RequireUppercaseCharacters=True,
        RequireLowercaseCharacters=True,
        MaxPasswordAge=90,
    )

    # CloudTrail
    s3 = boto3.client("s3", region_name=region)
    s3.create_bucket(Bucket="audit-logs")
    ct = boto3.client("cloudtrail", region_name=region)
    ct.create_trail(Name="org-trail", S3BucketName="audit-logs", IsMultiRegionTrail=True)

    # Multi-AZ ELB
    elbv2 = boto3.client("elbv2", region_name=region)
    elbv2.create_load_balancer(
        Name="prod-lb",
        Subnets=[sub1["Subnet"]["SubnetId"], sub2["Subnet"]["SubnetId"]],
        Type="application",
    )

    return {"vpc_id": vpc_id, "region": region}
