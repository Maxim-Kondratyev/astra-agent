"""Infrastructure discovery — collect account topology for architecture diagram."""

import boto3


def discover_infrastructure() -> dict:
    """Discover infrastructure topology: VPCs, subnets, instances, databases, LBs, Lambda, S3.

    Returns a structured dict representing the account's architecture.
    """
    infra = {"vpcs": [], "lambda_functions": 0, "s3_buckets": [], "route53_zones": 0}

    ec2 = boto3.client("ec2")
    # VPCs and subnets
    try:
        vpcs = ec2.describe_vpcs().get("Vpcs", [])
        subnets = ec2.describe_subnets().get("Subnets", [])
        instances_resp = ec2.describe_instances(Filters=[{"Name": "instance-state-name", "Values": ["running"]}])
        nat_gws = ec2.describe_nat_gateways(Filters=[{"Name": "state", "Values": ["available"]}]).get("NatGateways", [])

        # Group subnets by VPC
        subnet_map: dict[str, list] = {}
        for s in subnets:
            subnet_map.setdefault(s["VpcId"], []).append(s)

        # Group instances by subnet
        instance_map: dict[str, list] = {}
        for res in instances_resp.get("Reservations", []):
            for inst in res["Instances"]:
                sid = inst.get("SubnetId", "unknown")
                instance_map.setdefault(sid, []).append(inst)

        # Group NATs by VPC
        nat_map: dict[str, list] = {}
        for n in nat_gws:
            nat_map.setdefault(n["VpcId"], []).append(n)

        for vpc in vpcs:
            vpc_id = vpc["VpcId"]
            tags = {t["Key"]: t["Value"] for t in vpc.get("Tags", [])}
            vpc_subnets = subnet_map.get(vpc_id, [])

            # Group subnets by AZ
            az_groups: dict[str, dict] = {}
            for s in vpc_subnets:
                az = s["AvailabilityZone"]
                if az not in az_groups:
                    az_groups[az] = {"subnet_count": 0, "instances": 0, "subnet_ids": []}
                az_groups[az]["subnet_count"] += 1
                az_groups[az]["subnet_ids"].append(s["SubnetId"])
                az_groups[az]["instances"] += len(instance_map.get(s["SubnetId"], []))

            infra["vpcs"].append({
                "vpc_id": vpc_id,
                "cidr": vpc["CidrBlock"],
                "name": tags.get("Name", ""),
                "is_default": vpc.get("IsDefault", False),
                "azs": az_groups,
                "nat_gateways": len(nat_map.get(vpc_id, [])),
                "total_instances": sum(az["instances"] for az in az_groups.values()),
            })
    except Exception:
        pass

    # RDS
    try:
        rds = boto3.client("rds")
        dbs = rds.describe_db_instances().get("DBInstances", [])
        infra["rds_instances"] = [{"id": db["DBInstanceIdentifier"], "engine": db["Engine"],
                                    "az": db.get("AvailabilityZone", ""), "multi_az": db.get("MultiAZ", False)}
                                   for db in dbs]
    except Exception:
        infra["rds_instances"] = []

    # ELBv2
    try:
        elbv2 = boto3.client("elbv2")
        lbs = elbv2.describe_load_balancers().get("LoadBalancers", [])
        infra["load_balancers"] = [{"name": lb["LoadBalancerName"], "type": lb["Type"],
                                     "azs": [az["ZoneName"] for az in lb.get("AvailabilityZones", [])]}
                                    for lb in lbs]
    except Exception:
        infra["load_balancers"] = []

    # Lambda
    try:
        lam = boto3.client("lambda")
        funcs = lam.list_functions(MaxItems=50).get("Functions", [])
        infra["lambda_functions"] = len(funcs)
    except Exception:
        pass

    # S3
    try:
        s3 = boto3.client("s3")
        buckets = s3.list_buckets().get("Buckets", [])
        infra["s3_buckets"] = [b["Name"] for b in buckets]
    except Exception:
        infra["s3_buckets"] = []

    # Route53
    try:
        r53 = boto3.client("route53")
        zones = r53.list_hosted_zones().get("HostedZones", [])
        infra["route53_zones"] = len(zones)
    except Exception:
        pass

    return infra
