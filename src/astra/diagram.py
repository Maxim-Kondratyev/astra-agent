"""HTML diagram generator — pure HTML/CSS, no Mermaid dependency."""

from astra.checklist import CheckResult, Status


def generate_html_diagram(infra: dict, check_results: list[CheckResult] | None = None) -> str:
    """Generate a pure HTML/CSS infrastructure diagram. Always renders, no JS needed."""
    failed_ids = set()
    if check_results:
        for r in check_results:
            if r.status in (Status.FAIL, Status.WARNING):
                failed_ids.update(r.affected_resources)
                failed_ids.add(r.check_id)

    html_parts = ['<div style="display:flex;flex-wrap:wrap;gap:1rem;margin-top:1rem;">']

    # VPCs
    for vpc in infra.get("vpcs", []):
        if vpc.get("is_default") and vpc["total_instances"] == 0:
            continue
        vpc_name = vpc.get("name") or vpc["vpc_id"]
        nat_count = vpc.get("nat_gateways", 0)
        nat_warn = " ⚠️" if nat_count == 1 and len(vpc.get("azs", {})) > 1 else ""

        az_html = ""
        for az_name, az_data in vpc.get("azs", {}).items():
            inst = az_data["instances"]
            inst_label = f"🖥️ {inst} instance(s)" if inst > 0 else "—"
            az_html += f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:6px;padding:0.5rem;margin:0.3rem 0;font-size:0.72rem;"><strong>{az_name}</strong><br/>{inst_label}</div>'

        # RDS in this VPC
        rds_html = ""
        for db in infra.get("rds_instances", []):
            warn = " ⚠️" if not db["multi_az"] else " ✓"
            ma = "Multi-AZ" if db["multi_az"] else "Single-AZ"
            rds_html += f'<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:6px;padding:0.4rem;margin:0.3rem 0;font-size:0.72rem;">{warn} {db["id"]} ({db["engine"]}, {ma})</div>'

        html_parts.append(f'''<div style="flex:1;min-width:280px;background:#eff6ff;border:2px solid #1e88e5;border-radius:12px;padding:1rem;">
<div style="font-weight:600;font-size:0.85rem;margin-bottom:0.5rem;">🌐 {vpc_name}</div>
<div style="font-size:0.72rem;color:#64748b;margin-bottom:0.5rem;">CIDR: {vpc["cidr"]} · NAT: {nat_count}{nat_warn}</div>
{az_html}
{rds_html}
</div>''')

    html_parts.append('</div>')

    # Services row
    services = []
    lbs = infra.get("load_balancers", [])
    if lbs:
        lb_items = ", ".join(f'{lb["name"]} ({lb["type"]}, {len(lb["azs"])} AZ)' for lb in lbs[:3])
        services.append(f'<div style="background:#e3f2fd;border:1px solid #90caf9;border-radius:8px;padding:0.6rem;font-size:0.75rem;">⚖️ <strong>Load Balancers:</strong> {lb_items}</div>')

    lambda_count = infra.get("lambda_functions", 0)
    if lambda_count:
        services.append(f'<div style="background:#ede7f6;border:1px solid #b39ddb;border-radius:8px;padding:0.6rem;font-size:0.75rem;">⚡ <strong>Lambda:</strong> {lambda_count} function(s)</div>')

    buckets = infra.get("s3_buckets", [])
    if buckets:
        services.append(f'<div style="background:#fce4ec;border:1px solid #ef9a9a;border-radius:8px;padding:0.6rem;font-size:0.75rem;">🪣 <strong>S3:</strong> {len(buckets)} bucket(s)</div>')

    r53 = infra.get("route53_zones", 0)
    if r53:
        services.append(f'<div style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:8px;padding:0.6rem;font-size:0.75rem;">🌍 <strong>Route 53:</strong> {r53} hosted zone(s)</div>')

    if services:
        html_parts.append('<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:0.5rem;margin-top:1rem;">')
        html_parts.extend(services)
        html_parts.append('</div>')

    return "\n".join(html_parts)
