"""Resilience assessment tools — read-only AWS API queries for availability and recovery."""

import boto3
from strands import tool


@tool
def check_multi_az_deployment() -> dict:
    """Check Multi-AZ deployment status of RDS, ElastiCache, ELBs, and EC2 instances.

    Returns:
        Dictionary with Multi-AZ status for each service.
    """
    result = {}

    # RDS Multi-AZ
    rds = boto3.client("rds")
    try:
        instances = rds.describe_db_instances().get("DBInstances", [])
        rds_findings = []
        for db in instances:
            rds_findings.append({
                "db_id": db["DBInstanceIdentifier"],
                "engine": db["Engine"],
                "multi_az": db.get("MultiAZ", False),
                "availability_zone": db.get("AvailabilityZone", ""),
            })
        single_az = [d for d in rds_findings if not d["multi_az"]]
        result["rds"] = {"total": len(rds_findings), "single_az_count": len(single_az), "single_az_instances": single_az}
    except Exception:
        result["rds"] = {"total": 0, "single_az_count": 0, "single_az_instances": [], "note": "No RDS instances or access denied."}

    # ElastiCache
    ec = boto3.client("elasticache")
    try:
        clusters = ec.describe_cache_clusters().get("CacheClusters", [])
        replication_groups = ec.describe_replication_groups().get("ReplicationGroups", [])
        single_node = [c for c in clusters if c.get("NumCacheNodes", 1) == 1 and not c.get("ReplicationGroupId")]
        multi_az_groups = [rg for rg in replication_groups if rg.get("MultiAZ") == "enabled"]
        result["elasticache"] = {
            "clusters": len(clusters),
            "replication_groups": len(replication_groups),
            "multi_az_groups": len(multi_az_groups),
            "single_node_clusters": [{"id": c["CacheClusterId"], "engine": c["Engine"]} for c in single_node],
        }
    except Exception:
        result["elasticache"] = {"clusters": 0, "note": "No ElastiCache or access denied."}

    # ELBs (check cross-zone and multi-AZ)
    elbv2 = boto3.client("elbv2")
    try:
        lbs = elbv2.describe_load_balancers().get("LoadBalancers", [])
        lb_findings = []
        for lb in lbs:
            azs = [az["ZoneName"] for az in lb.get("AvailabilityZones", [])]
            lb_findings.append({
                "name": lb["LoadBalancerName"],
                "type": lb["Type"],
                "az_count": len(azs),
                "availability_zones": azs,
                "single_az": len(azs) < 2,
            })
        single_az_lbs = [lb for lb in lb_findings if lb["single_az"]]
        result["load_balancers"] = {"total": len(lb_findings), "single_az_count": len(single_az_lbs), "single_az_lbs": single_az_lbs}
    except Exception:
        result["load_balancers"] = {"total": 0, "single_az_count": 0, "note": "No ELBs or access denied."}

    # EC2 AZ distribution
    ec2 = boto3.client("ec2")
    try:
        instances = ec2.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])
        az_distribution = {}
        for res in instances.get("Reservations", []):
            for inst in res.get("Instances", []):
                az = inst.get("Placement", {}).get("AvailabilityZone", "unknown")
                az_distribution[az] = az_distribution.get(az, 0) + 1
        total = sum(az_distribution.values())
        result["ec2"] = {"running_instances": total, "az_distribution": az_distribution, "single_az": len(az_distribution) < 2 and total > 0}
    except Exception:
        result["ec2"] = {"running_instances": 0, "note": "No EC2 or access denied."}

    return result


@tool
def check_backup_coverage() -> dict:
    """Check AWS Backup plans, backup vaults, and recovery points for key resources.

    Returns:
        Dictionary with backup plan details, vault info, and unprotected resources.
    """
    backup = boto3.client("backup")
    result = {}

    # Backup plans
    try:
        plans = backup.list_backup_plans().get("BackupPlansList", [])
        result["backup_plans"] = [{"name": p["BackupPlanName"], "id": p["BackupPlanId"]} for p in plans]
    except Exception:
        result["backup_plans"] = []

    # Backup vaults and recovery points
    try:
        vaults = backup.list_backup_vaults().get("BackupVaultList", [])
        vault_info = []
        for v in vaults[:10]:
            vault_info.append({
                "name": v["BackupVaultName"],
                "recovery_points": v.get("NumberOfRecoveryPoints", 0),
                "encrypted": v.get("EncryptionKeyArn", "") != "",
            })
        result["backup_vaults"] = vault_info
    except Exception:
        result["backup_vaults"] = []

    # Protected resources
    try:
        protected = backup.list_protected_resources(MaxResults=100).get("Results", [])
        result["protected_resources_count"] = len(protected)
        result["protected_resource_types"] = list({r["ResourceType"] for r in protected})
    except Exception:
        result["protected_resources_count"] = 0
        result["protected_resource_types"] = []

    # Check RDS automated backups
    rds = boto3.client("rds")
    try:
        instances = rds.describe_db_instances().get("DBInstances", [])
        no_backup = [{"db_id": db["DBInstanceIdentifier"], "retention_days": db.get("BackupRetentionPeriod", 0)}
                     for db in instances if db.get("BackupRetentionPeriod", 0) == 0]
        short_backup = [{"db_id": db["DBInstanceIdentifier"], "retention_days": db.get("BackupRetentionPeriod", 0)}
                        for db in instances if 0 < db.get("BackupRetentionPeriod", 0) < 7]
        result["rds_backups"] = {"total": len(instances), "no_backup": no_backup, "short_retention": short_backup}
    except Exception:
        result["rds_backups"] = {"total": 0, "no_backup": [], "short_retention": []}

    # EBS snapshots — check if volumes have recent snapshots
    ec2 = boto3.client("ec2")
    try:
        volumes = ec2.describe_volumes(MaxResults=50).get("Volumes", [])
        volume_ids = [v["VolumeId"] for v in volumes]
        if volume_ids:
            snapshots = ec2.describe_snapshots(Filters=[{"Name": "volume-id", "Values": volume_ids[:20]}], OwnerIds=["self"]).get("Snapshots", [])
            snapped_volumes = {s["VolumeId"] for s in snapshots}
            unsnapped = [v["VolumeId"] for v in volumes if v["VolumeId"] not in snapped_volumes]
            result["ebs_backups"] = {"total_volumes": len(volumes), "without_snapshots": unsnapped[:20]}
        else:
            result["ebs_backups"] = {"total_volumes": 0, "without_snapshots": []}
    except Exception:
        result["ebs_backups"] = {"total_volumes": 0, "without_snapshots": []}

    return result


@tool
def check_auto_scaling_configuration() -> dict:
    """Check Auto Scaling groups configuration, health checks, and scaling policies.

    Returns:
        Dictionary with ASG details, health check settings, and scaling policies.
    """
    asg_client = boto3.client("autoscaling")
    result = {}

    try:
        groups = asg_client.describe_auto_scaling_groups(MaxRecords=50).get("AutoScalingGroups", [])
        asg_findings = []
        for g in groups:
            policies = asg_client.describe_policies(AutoScalingGroupName=g["AutoScalingGroupName"]).get("ScalingPolicies", [])
            azs = g.get("AvailabilityZones", [])
            asg_findings.append({
                "name": g["AutoScalingGroupName"],
                "min_size": g["MinSize"],
                "max_size": g["MaxSize"],
                "desired_capacity": g["DesiredCapacity"],
                "health_check_type": g.get("HealthCheckType", ""),
                "health_check_grace_period": g.get("HealthCheckGracePeriod", 0),
                "az_count": len(azs),
                "availability_zones": azs,
                "scaling_policies_count": len(policies),
                "has_target_tracking": any(p["PolicyType"] == "TargetTrackingScaling" for p in policies),
                "instances_count": len(g.get("Instances", [])),
            })

        no_scaling = [a for a in asg_findings if a["scaling_policies_count"] == 0]
        single_az = [a for a in asg_findings if a["az_count"] < 2]
        ec2_health_only = [a for a in asg_findings if a["health_check_type"] == "EC2"]

        result["auto_scaling_groups"] = {
            "total": len(asg_findings),
            "groups": asg_findings,
            "no_scaling_policies": no_scaling,
            "single_az": single_az,
            "ec2_health_only": ec2_health_only,
        }
    except Exception as e:
        result["auto_scaling_groups"] = {"total": 0, "groups": [], "error": str(e)}

    return result


@tool
def check_route53_failover() -> dict:
    """Check Route 53 hosted zones for failover routing, health checks, and DNS resilience.

    Returns:
        Dictionary with health checks, failover records, and DNS configuration.
    """
    r53 = boto3.client("route53")
    result = {}

    # Health checks
    try:
        health_checks = r53.list_health_checks().get("HealthChecks", [])
        result["health_checks"] = {
            "total": len(health_checks),
            "checks": [{"id": hc["Id"], "type": hc["HealthCheckConfig"].get("Type", ""), "disabled": hc["HealthCheckConfig"].get("Disabled", False)} for hc in health_checks[:20]],
        }
    except Exception:
        result["health_checks"] = {"total": 0, "checks": []}

    # Hosted zones and record types
    try:
        zones = r53.list_hosted_zones().get("HostedZones", [])
        zone_findings = []
        for zone in zones[:10]:
            zone_id = zone["Id"].split("/")[-1]
            records = r53.list_resource_record_sets(HostedZoneId=zone_id, MaxItems="100").get("ResourceRecordSets", [])
            failover_records = [r for r in records if r.get("Failover")]
            weighted_records = [r for r in records if r.get("Weight") is not None]
            latency_records = [r for r in records if r.get("Region")]
            alias_records = [r for r in records if r.get("AliasTarget")]
            zone_findings.append({
                "zone_name": zone["Name"],
                "record_count": len(records),
                "failover_records": len(failover_records),
                "weighted_records": len(weighted_records),
                "latency_records": len(latency_records),
                "alias_records": len(alias_records),
                "has_failover": len(failover_records) > 0,
            })
        result["hosted_zones"] = {"total": len(zones), "zones": zone_findings}
    except Exception:
        result["hosted_zones"] = {"total": 0, "zones": []}

    return result


@tool
def detect_single_points_of_failure() -> dict:
    """Detect single points of failure: single-instance deployments, NAT gateways, and non-redundant services.

    Returns:
        Dictionary identifying potential single points of failure across the infrastructure.
    """
    result = {"single_points_of_failure": []}
    ec2 = boto3.client("ec2")

    # Single NAT Gateways per AZ
    try:
        nat_gws = ec2.describe_nat_gateways(Filters=[{"Name": "state", "Values": ["available"]}]).get("NatGateways", [])
        subnets_with_nat = {}
        for ng in nat_gws:
            subnet = ng.get("SubnetId", "")
            vpc = ng.get("VpcId", "")
            subnets_with_nat.setdefault(vpc, []).append(subnet)
        for vpc, subnets in subnets_with_nat.items():
            if len(subnets) == 1:
                result["single_points_of_failure"].append({
                    "type": "Single NAT Gateway",
                    "resource": f"VPC {vpc}",
                    "detail": "Only one NAT gateway — all private subnet internet access depends on a single AZ.",
                    "recommendation": "Deploy NAT gateways in each AZ with private subnets.",
                })
    except Exception:
        pass

    # ASGs with min=max=1 or desired=1
    asg_client = boto3.client("autoscaling")
    try:
        groups = asg_client.describe_auto_scaling_groups(MaxRecords=50).get("AutoScalingGroups", [])
        for g in groups:
            if g["MaxSize"] == 1 or g["DesiredCapacity"] == 1:
                result["single_points_of_failure"].append({
                    "type": "Single-instance ASG",
                    "resource": g["AutoScalingGroupName"],
                    "detail": f"max={g['MaxSize']}, desired={g['DesiredCapacity']} — no redundancy.",
                    "recommendation": "Increase min/desired to at least 2 across multiple AZs.",
                })
    except Exception:
        pass

    # Standalone EC2 instances (not in ASG, not in ECS)
    try:
        reservations = ec2.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}]).get("Reservations", [])
        standalone = []
        for res in reservations:
            for inst in res.get("Instances", []):
                tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                if "aws:autoscaling:groupName" not in tags and "aws:ecs:clusterName" not in tags:
                    standalone.append(inst["InstanceId"])
        if standalone:
            result["single_points_of_failure"].append({
                "type": "Standalone EC2 instances",
                "resource": ", ".join(standalone[:10]),
                "detail": f"{len(standalone)} instance(s) not in an ASG or ECS cluster — no auto-recovery.",
                "recommendation": "Place instances behind an ASG with health checks, or migrate to containers/serverless.",
            })
    except Exception:
        pass

    # Single-AZ VPC subnets used by ELBs
    elbv2 = boto3.client("elbv2")
    try:
        lbs = elbv2.describe_load_balancers().get("LoadBalancers", [])
        for lb in lbs:
            azs = lb.get("AvailabilityZones", [])
            if len(azs) == 1:
                result["single_points_of_failure"].append({
                    "type": "Single-AZ Load Balancer",
                    "resource": lb["LoadBalancerName"],
                    "detail": f"Only in {azs[0]['ZoneName']} — AZ failure takes down all traffic.",
                    "recommendation": "Add subnets in at least 2 AZs.",
                })
    except Exception:
        pass

    result["spof_count"] = len(result["single_points_of_failure"])
    return result
