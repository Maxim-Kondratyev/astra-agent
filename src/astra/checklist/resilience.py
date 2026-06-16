"""Resilience checklist — prebuilt Well-Architected Reliability Pillar checks."""

import boto3

from astra.checklist import CheckResult, Status


# --- Individual checks ---


def check_rds_multi_az() -> CheckResult:
    """REL-01: RDS instances should use Multi-AZ for production workloads."""
    rds = boto3.client("rds")
    try:
        instances = rds.describe_db_instances().get("DBInstances", [])
    except Exception as e:
        return CheckResult("REL-01", "RDS Multi-AZ", Status.ERROR, evidence={"error": str(e)})

    if not instances:
        return CheckResult("REL-01", "RDS Multi-AZ", Status.PASS, evidence={"detail": "No RDS instances found."})

    single_az = [db["DBInstanceIdentifier"] for db in instances if not db.get("MultiAZ", False)]
    if single_az:
        return CheckResult(
            "REL-01", "RDS Multi-AZ", Status.FAIL,
            evidence={"total": len(instances), "single_az": single_az},
            affected_resources=single_az,
            recommendation="Enable Multi-AZ for production RDS instances to survive AZ failure.",
            wa_reference="REL 9 – How do you back up data? / REL 10 – How do you use fault isolation?",
        )
    return CheckResult("REL-01", "RDS Multi-AZ", Status.PASS, evidence={"total": len(instances), "all_multi_az": True})


def check_ec2_az_spread() -> CheckResult:
    """REL-02: EC2 instances should be spread across multiple AZs."""
    ec2 = boto3.client("ec2")
    try:
        reservations = ec2.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}]).get("Reservations", [])
    except Exception as e:
        return CheckResult("REL-02", "EC2 AZ distribution", Status.ERROR, evidence={"error": str(e)})

    az_map: dict[str, list[str]] = {}
    for res in reservations:
        for inst in res["Instances"]:
            az = inst["Placement"]["AvailabilityZone"]
            az_map.setdefault(az, []).append(inst["InstanceId"])

    total = sum(len(v) for v in az_map.values())
    if total == 0:
        return CheckResult("REL-02", "EC2 AZ distribution", Status.PASS, evidence={"detail": "No running instances."})

    if len(az_map) < 2:
        return CheckResult(
            "REL-02", "EC2 AZ distribution", Status.FAIL,
            evidence={"az_distribution": {k: len(v) for k, v in az_map.items()}, "total": total},
            affected_resources=list(az_map.keys()),
            recommendation="Distribute instances across at least 2 AZs. Use ASGs with multi-AZ subnet config.",
            wa_reference="REL 10 – How do you use fault isolation to protect your workload?",
        )
    return CheckResult("REL-02", "EC2 AZ distribution", Status.PASS, evidence={"az_distribution": {k: len(v) for k, v in az_map.items()}})


def check_asg_health_checks() -> CheckResult:
    """REL-03: Auto Scaling Groups should use ELB health checks, not just EC2."""
    asg = boto3.client("autoscaling")
    try:
        groups = asg.describe_auto_scaling_groups(MaxRecords=100).get("AutoScalingGroups", [])
    except Exception as e:
        return CheckResult("REL-03", "ASG health check type", Status.ERROR, evidence={"error": str(e)})

    if not groups:
        return CheckResult("REL-03", "ASG health check type", Status.PASS, evidence={"detail": "No ASGs found."})

    ec2_only = [g["AutoScalingGroupName"] for g in groups if g.get("HealthCheckType") == "EC2" and g.get("TargetGroupARNs")]
    if ec2_only:
        return CheckResult(
            "REL-03", "ASG health check type", Status.WARNING,
            evidence={"total_asgs": len(groups), "ec2_health_only_with_elb": ec2_only},
            affected_resources=ec2_only,
            recommendation="Switch ASGs with attached target groups from EC2 to ELB health checks for faster detection of unhealthy instances.",
            wa_reference="REL 6 – How do you monitor workload resources?",
        )
    return CheckResult("REL-03", "ASG health check type", Status.PASS, evidence={"total_asgs": len(groups)})


def check_asg_multi_az() -> CheckResult:
    """REL-04: ASGs should span multiple AZs."""
    asg = boto3.client("autoscaling")
    try:
        groups = asg.describe_auto_scaling_groups(MaxRecords=100).get("AutoScalingGroups", [])
    except Exception as e:
        return CheckResult("REL-04", "ASG multi-AZ", Status.ERROR, evidence={"error": str(e)})

    if not groups:
        return CheckResult("REL-04", "ASG multi-AZ", Status.PASS, evidence={"detail": "No ASGs found."})

    single_az = [g["AutoScalingGroupName"] for g in groups if len(g.get("AvailabilityZones", [])) < 2]
    if single_az:
        return CheckResult(
            "REL-04", "ASG multi-AZ", Status.FAIL,
            evidence={"total_asgs": len(groups), "single_az_asgs": single_az},
            affected_resources=single_az,
            recommendation="Configure ASGs to span at least 2 AZs for fault isolation.",
            wa_reference="REL 10 – How do you use fault isolation to protect your workload?",
        )
    return CheckResult("REL-04", "ASG multi-AZ", Status.PASS, evidence={"total_asgs": len(groups)})


def check_elb_multi_az() -> CheckResult:
    """REL-05: Load balancers should span multiple AZs."""
    elbv2 = boto3.client("elbv2")
    try:
        lbs = elbv2.describe_load_balancers().get("LoadBalancers", [])
    except Exception as e:
        return CheckResult("REL-05", "ELB multi-AZ", Status.ERROR, evidence={"error": str(e)})

    if not lbs:
        return CheckResult("REL-05", "ELB multi-AZ", Status.PASS, evidence={"detail": "No load balancers found."})

    single_az = [lb["LoadBalancerName"] for lb in lbs if len(lb.get("AvailabilityZones", [])) < 2]
    if single_az:
        return CheckResult(
            "REL-05", "ELB multi-AZ", Status.FAIL,
            evidence={"total_lbs": len(lbs), "single_az_lbs": single_az},
            affected_resources=single_az,
            recommendation="Register subnets in at least 2 AZs for each load balancer.",
            wa_reference="REL 10 – How do you use fault isolation to protect your workload?",
        )
    return CheckResult("REL-05", "ELB multi-AZ", Status.PASS, evidence={"total_lbs": len(lbs)})


def check_backup_plans_exist() -> CheckResult:
    """REL-06: AWS Backup should be configured with backup plans."""
    backup = boto3.client("backup")
    try:
        plans = backup.list_backup_plans().get("BackupPlansList", [])
    except Exception as e:
        return CheckResult("REL-06", "AWS Backup plans", Status.ERROR, evidence={"error": str(e)})

    if not plans:
        return CheckResult(
            "REL-06", "AWS Backup plans", Status.FAIL,
            evidence={"backup_plans": 0},
            recommendation="Create AWS Backup plans to automate backups for RDS, EBS, DynamoDB, and other critical resources.",
            wa_reference="REL 9 – How do you back up data?",
        )
    return CheckResult("REL-06", "AWS Backup plans", Status.PASS, evidence={"backup_plans": len(plans), "names": [p["BackupPlanName"] for p in plans]})


def check_rds_backup_retention() -> CheckResult:
    """REL-07: RDS instances should have backup retention >= 7 days."""
    rds = boto3.client("rds")
    try:
        instances = rds.describe_db_instances().get("DBInstances", [])
    except Exception as e:
        return CheckResult("REL-07", "RDS backup retention", Status.ERROR, evidence={"error": str(e)})

    if not instances:
        return CheckResult("REL-07", "RDS backup retention", Status.PASS, evidence={"detail": "No RDS instances."})

    short = [{"db": db["DBInstanceIdentifier"], "retention_days": db.get("BackupRetentionPeriod", 0)} for db in instances if db.get("BackupRetentionPeriod", 0) < 7]
    if short:
        return CheckResult(
            "REL-07", "RDS backup retention", Status.WARNING,
            evidence={"total": len(instances), "short_retention": short},
            affected_resources=[s["db"] for s in short],
            recommendation="Set backup retention to at least 7 days (14+ recommended for production).",
            wa_reference="REL 9 – How do you back up data?",
        )
    return CheckResult("REL-07", "RDS backup retention", Status.PASS, evidence={"total": len(instances)})


def check_single_nat_gateway() -> CheckResult:
    """REL-08: VPCs should have NAT gateways in multiple AZs."""
    ec2 = boto3.client("ec2")
    try:
        nats = ec2.describe_nat_gateways(Filters=[{"Name": "state", "Values": ["available"]}]).get("NatGateways", [])
    except Exception as e:
        return CheckResult("REL-08", "NAT Gateway redundancy", Status.ERROR, evidence={"error": str(e)})

    if not nats:
        return CheckResult("REL-08", "NAT Gateway redundancy", Status.PASS, evidence={"detail": "No NAT gateways (or fully private networking)."})

    vpc_az_map: dict[str, set[str]] = {}
    for n in nats:
        vpc_az_map.setdefault(n["VpcId"], set()).add(n["SubnetId"])

    single_nat_vpcs = [vpc for vpc, subnets in vpc_az_map.items() if len(subnets) == 1]
    if single_nat_vpcs:
        return CheckResult(
            "REL-08", "NAT Gateway redundancy", Status.WARNING,
            evidence={"vpcs_with_single_nat": single_nat_vpcs, "total_nats": len(nats)},
            affected_resources=single_nat_vpcs,
            recommendation="Deploy a NAT gateway in each AZ that has private subnets to avoid cross-AZ dependency.",
            wa_reference="REL 10 – How do you use fault isolation to protect your workload?",
        )
    return CheckResult("REL-08", "NAT Gateway redundancy", Status.PASS, evidence={"total_nats": len(nats)})


def check_ebs_snapshots() -> CheckResult:
    """REL-09: EBS volumes should have recent snapshots."""
    ec2 = boto3.client("ec2")
    sts = boto3.client("sts")
    try:
        account_id = sts.get_caller_identity()["Account"]
        volumes = ec2.describe_volumes(MaxResults=100).get("Volumes", [])
    except Exception as e:
        return CheckResult("REL-09", "EBS snapshot coverage", Status.ERROR, evidence={"error": str(e)})

    if not volumes:
        return CheckResult("REL-09", "EBS snapshot coverage", Status.PASS, evidence={"detail": "No EBS volumes."})

    volume_ids = [v["VolumeId"] for v in volumes]
    snapshots = ec2.describe_snapshots(OwnerIds=[account_id], Filters=[{"Name": "volume-id", "Values": volume_ids[:200]}]).get("Snapshots", [])
    snapped = {s["VolumeId"] for s in snapshots}
    unsnapped = [vid for vid in volume_ids if vid not in snapped]

    if len(unsnapped) > len(volume_ids) * 0.3:
        return CheckResult(
            "REL-09", "EBS snapshot coverage", Status.FAIL,
            evidence={"total_volumes": len(volumes), "without_snapshots": len(unsnapped), "sample": unsnapped[:10]},
            affected_resources=unsnapped[:20],
            recommendation="Enable automated snapshots via AWS Backup or Data Lifecycle Manager for all production volumes.",
            wa_reference="REL 9 – How do you back up data?",
        )
    if unsnapped:
        return CheckResult(
            "REL-09", "EBS snapshot coverage", Status.WARNING,
            evidence={"total_volumes": len(volumes), "without_snapshots": len(unsnapped)},
            affected_resources=unsnapped[:10],
            recommendation="Consider snapshot coverage for remaining volumes.",
            wa_reference="REL 9 – How do you back up data?",
        )
    return CheckResult("REL-09", "EBS snapshot coverage", Status.PASS, evidence={"total_volumes": len(volumes), "all_have_snapshots": True})


def check_route53_health_checks() -> CheckResult:
    """REL-10: DNS records for critical endpoints should have Route 53 health checks."""
    r53 = boto3.client("route53")
    try:
        health_checks = r53.list_health_checks().get("HealthChecks", [])
        zones = r53.list_hosted_zones().get("HostedZones", [])
    except Exception as e:
        return CheckResult("REL-10", "Route 53 health checks", Status.ERROR, evidence={"error": str(e)})

    if not zones:
        return CheckResult("REL-10", "Route 53 health checks", Status.PASS, evidence={"detail": "No hosted zones."})

    if not health_checks:
        return CheckResult(
            "REL-10", "Route 53 health checks", Status.WARNING,
            evidence={"hosted_zones": len(zones), "health_checks": 0},
            recommendation="Create Route 53 health checks for critical endpoints to enable DNS failover.",
            wa_reference="REL 10 – How do you use fault isolation to protect your workload?",
        )
    return CheckResult("REL-10", "Route 53 health checks", Status.PASS, evidence={"health_checks": len(health_checks), "hosted_zones": len(zones)})


def check_elasticache_multi_az() -> CheckResult:
    """REL-11: ElastiCache replication groups should have Multi-AZ enabled."""
    ec = boto3.client("elasticache")
    try:
        groups = ec.describe_replication_groups().get("ReplicationGroups", [])
    except Exception as e:
        return CheckResult("REL-11", "ElastiCache Multi-AZ", Status.ERROR, evidence={"error": str(e)})

    if not groups:
        return CheckResult("REL-11", "ElastiCache Multi-AZ", Status.PASS, evidence={"detail": "No replication groups."})

    no_multi_az = [g["ReplicationGroupId"] for g in groups if g.get("MultiAZ") != "enabled"]
    if no_multi_az:
        return CheckResult(
            "REL-11", "ElastiCache Multi-AZ", Status.WARNING,
            evidence={"total_groups": len(groups), "no_multi_az": no_multi_az},
            affected_resources=no_multi_az,
            recommendation="Enable Multi-AZ with automatic failover for ElastiCache replication groups.",
            wa_reference="REL 10 – How do you use fault isolation to protect your workload?",
        )
    return CheckResult("REL-11", "ElastiCache Multi-AZ", Status.PASS, evidence={"total_groups": len(groups)})


def check_cloudwatch_alarms() -> CheckResult:
    """REL-12: Critical infrastructure should have CloudWatch alarms configured."""
    cw = boto3.client("cloudwatch")
    try:
        alarms = cw.describe_alarms(MaxRecords=100).get("MetricAlarms", [])
    except Exception as e:
        return CheckResult("REL-12", "CloudWatch alarms", Status.ERROR, evidence={"error": str(e)})

    if not alarms:
        return CheckResult(
            "REL-12", "CloudWatch alarms", Status.FAIL,
            evidence={"alarms": 0},
            recommendation="Configure CloudWatch alarms for key metrics: CPU, memory, error rates, latency, and queue depth.",
            wa_reference="REL 6 – How do you monitor workload resources?",
        )
    # Check for alarm actions (SNS notifications)
    no_actions = [a["AlarmName"] for a in alarms if not a.get("AlarmActions")]
    if len(no_actions) > len(alarms) * 0.5:
        return CheckResult(
            "REL-12", "CloudWatch alarms", Status.WARNING,
            evidence={"total_alarms": len(alarms), "no_actions": len(no_actions)},
            affected_resources=no_actions[:10],
            recommendation="Add SNS alarm actions so that alerts are routed to on-call teams.",
            wa_reference="REL 6 – How do you monitor workload resources?",
        )
    return CheckResult("REL-12", "CloudWatch alarms", Status.PASS, evidence={"total_alarms": len(alarms)})


# --- Checklist runner ---

ALL_CHECKS = [
    check_rds_multi_az,
    check_ec2_az_spread,
    check_asg_health_checks,
    check_asg_multi_az,
    check_elb_multi_az,
    check_backup_plans_exist,
    check_rds_backup_retention,
    check_single_nat_gateway,
    check_ebs_snapshots,
    check_route53_health_checks,
    check_elasticache_multi_az,
    check_cloudwatch_alarms,
]


def run_resilience_checklist() -> list[CheckResult]:
    """Run all prebuilt resilience checks and return results."""
    results = []
    for check_fn in ALL_CHECKS:
        try:
            results.append(check_fn())
        except Exception as e:
            results.append(CheckResult(
                check_id=check_fn.__doc__.split(":")[0] if check_fn.__doc__ else "UNKNOWN",
                title=check_fn.__name__,
                status=Status.ERROR,
                evidence={"error": str(e)},
            ))
    return results
