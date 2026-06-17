"""Mermaid diagram generator — turns infrastructure discovery into visual architecture."""

from astra.checklist import CheckResult, Status


def generate_mermaid_diagram(infra: dict, check_results: list[CheckResult] | None = None) -> str:
    """Generate a Mermaid architecture diagram from discovered infrastructure.

    Args:
        infra: Output from discover_infrastructure()
        check_results: Optional check results to annotate failures on the diagram
    """
    # Build a set of failed resource identifiers for annotation
    failed_resources: set[str] = set()
    if check_results:
        for r in check_results:
            if r.status in (Status.FAIL, Status.WARNING):
                failed_resources.update(r.affected_resources)
                # Also mark by check type
                failed_resources.add(r.check_id)

    lines = ["graph TB"]

    # Style definitions
    lines.append("    classDef vpc fill:#e8f4fd,stroke:#1e88e5,stroke-width:2px")
    lines.append("    classDef az fill:#f3e5f5,stroke:#8e24aa,stroke-width:1px")
    lines.append("    classDef compute fill:#e8f5e9,stroke:#43a047")
    lines.append("    classDef database fill:#fff3e0,stroke:#ef6c00")
    lines.append("    classDef network fill:#e3f2fd,stroke:#1565c0")
    lines.append("    classDef storage fill:#fce4ec,stroke:#c62828")
    lines.append("    classDef warning fill:#fff9c4,stroke:#f9a825,stroke-width:3px")
    lines.append("    classDef serverless fill:#ede7f6,stroke:#5e35b1")
    lines.append("")

    # Internet / external
    lines.append("    Internet((Internet))")
    lines.append("")

    # Route53
    if infra.get("route53_zones", 0) > 0:
        r53_label = f"Route53<br/>{infra['route53_zones']} zone(s)"
        if "REL-10" in failed_resources:
            r53_label += "<br/>⚠️ No health checks"
        lines.append(f"    R53[{r53_label}]:::network")
        lines.append("    Internet --> R53")
        lines.append("")

    # Load Balancers
    lbs = infra.get("load_balancers", [])
    for i, lb in enumerate(lbs):
        lb_id = f"LB{i}"
        az_count = len(lb["azs"])
        warn = "⚠️ " if az_count < 2 or lb["name"] in failed_resources else ""
        label = f"{warn}{lb['name']}<br/>{lb['type'].upper()} · {az_count} AZ(s)"
        lines.append(f"    {lb_id}[{label}]:::network")
        if infra.get("route53_zones", 0) > 0:
            lines.append(f"    R53 --> {lb_id}")
        else:
            lines.append(f"    Internet --> {lb_id}")
    if lbs:
        lines.append("")

    # VPCs
    for vi, vpc in enumerate(infra.get("vpcs", [])):
        if vpc.get("is_default") and vpc["total_instances"] == 0:
            continue  # Skip empty default VPC

        vpc_label = vpc.get("name") or vpc["vpc_id"]
        vpc_node = f"VPC{vi}"
        lines.append(f"    subgraph {vpc_node}[\"{vpc_label} ({vpc['cidr']})\"]")
        lines.append("        direction TB")

        # AZs within VPC
        for az_name, az_data in vpc.get("azs", {}).items():
            az_short = az_name[-2:]  # e.g., "1a"
            az_node = f"AZ{vi}_{az_short.replace('-','')}"
            inst_count = az_data["instances"]
            has_content = False

            lines.append(f"        subgraph {az_node}[\"{az_name}\"]")

            # EC2 instances in this AZ
            if inst_count > 0:
                ec2_node = f"EC2_{vi}_{az_short.replace('-','')}"
                lines.append(f"            {ec2_node}[🖥️ {inst_count} instance(s)]:::compute")
                has_content = True

            # RDS in this AZ
            for db in infra.get("rds_instances", []):
                if db["az"] == az_name:
                    db_node = f"DB_{db['id'].replace('-', '_')}"
                    warn = "⚠️ " if not db["multi_az"] or db["id"] in failed_resources else "✓ "
                    ma = "Multi-AZ" if db["multi_az"] else "Single-AZ"
                    lines.append(f"            {db_node}[(\"{warn}{db['id']}<br/>{db['engine']} · {ma}\")]:::database")
                    has_content = True

            # Mermaid requires at least one node in a subgraph
            if not has_content:
                placeholder = f"empty_{vi}_{az_short.replace('-','')}"
                lines.append(f"            {placeholder}[subnet]:::az")

            lines.append("        end")

        # NAT Gateways
        nat_count = vpc.get("nat_gateways", 0)
        if nat_count > 0:
            warn = "⚠️ " if nat_count == 1 and len(vpc.get("azs", {})) > 1 else ""
            lines.append(f"        NAT{vi}[{warn}NAT Gateway x{nat_count}]:::network")

        lines.append("    end")
        lines.append(f"    class {vpc_node} vpc")

        # Connect LBs to VPC
        for i, lb in enumerate(lbs):
            lines.append(f"    LB{i} --> {vpc_node}")
            break  # Connect first LB only to avoid clutter

        lines.append("")

    # Lambda
    lambda_count = infra.get("lambda_functions", 0)
    if lambda_count > 0:
        lines.append(f"    Lambda[\"⚡ Lambda<br/>{lambda_count} function(s)\"]:::serverless")
        if lbs:
            lines.append("    LB0 -.-> Lambda")
        lines.append("")

    # S3
    buckets = infra.get("s3_buckets", [])
    if buckets:
        bucket_label = f"🪣 S3<br/>{len(buckets)} bucket(s)"
        lines.append(f"    S3[({bucket_label})]:::storage")
        lines.append("")

    return "\n".join(lines)
