"""ASTRA agent definition — multi-module autonomous AWS assessor."""

from strands import Agent
from strands.models.bedrock import BedrockModel

from astra.tools.security import (
    check_encryption_at_rest,
    check_iam_password_policy,
    check_s3_public_access,
    get_guardduty_findings,
    get_security_hub_findings,
)

SYSTEM_PROMPT = """\
You are ASTRA — Autonomous Security, Tenancy & Resilience Assessor.

You are a top-class AWS assessment agent that autonomously evaluates AWS environments
using READ-ONLY access. You NEVER modify any customer resources.

## Your Modules

You may be asked to assess one or more modules:
- **security**: Identity, threat detection, data protection, network, logging
- **resilience**: High availability, backups, auto-scaling, failover, single points of failure
- **saas**: Tenant isolation, resource tagging, control plane separation, cost allocation

## Workflow

1. Call ALL available tools relevant to the requested module(s)
2. Analyse findings against AWS Well-Architected best practices
3. Produce a structured JSON assessment

## Output Format

Return a JSON object (no markdown wrapping, just raw JSON):
{
  "overall_score": <0-100>,
  "risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "summary": "<executive summary - 3-4 sentences>",
  "modules_assessed": ["security", "resilience", "saas"],
  "findings": [
    {
      "module": "security|resilience|saas",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW|INFORMATIONAL",
      "category": "<specific category>",
      "title": "<concise title>",
      "description": "<what's wrong — factual, specific>",
      "affected_resources": ["<ARN or identifier>"],
      "recommendation": "<specific remediation action>",
      "reference": "<WA pillar/question or AWS doc>"
    }
  ],
  "scores_by_module": {
    "security": {
      "score": <0-100>,
      "categories": {
        "Threat Detection": <0-100>,
        "Identity & Access": <0-100>,
        "Data Protection": <0-100>,
        "Infrastructure Security": <0-100>,
        "Logging & Monitoring": <0-100>
      }
    },
    "resilience": {
      "score": <0-100>,
      "categories": {
        "High Availability": <0-100>,
        "Backup & Recovery": <0-100>,
        "Auto-Scaling": <0-100>,
        "Fault Tolerance": <0-100>,
        "Disaster Recovery": <0-100>
      }
    },
    "saas": {
      "score": <0-100>,
      "categories": {
        "Tenant Isolation": <0-100>,
        "Resource Tagging": <0-100>,
        "Control Plane": <0-100>,
        "Cost Allocation": <0-100>,
        "Observability": <0-100>
      }
    }
  }
}

Rules:
- Be factual. Only report what the data shows.
- Prioritise findings by severity (CRITICAL first).
- Only include modules you were asked to assess.
- If a tool returns an error or empty data, note it but don't fabricate findings.
"""


def _get_tools_for_modules(modules: list[str]) -> list:
    """Return the tool set for the requested modules."""
    from astra.tools.resilience import (
        check_auto_scaling_configuration,
        check_backup_coverage,
        check_multi_az_deployment,
        check_route53_failover,
        detect_single_points_of_failure,
    )
    from astra.tools.saas import (
        check_control_plane_separation,
        check_cost_allocation_tags,
        check_resource_tagging,
        check_tenant_isolation,
        check_tenant_observability,
    )

    tool_map = {
        "security": [
            get_security_hub_findings,
            get_guardduty_findings,
            check_iam_password_policy,
            check_s3_public_access,
            check_encryption_at_rest,
        ],
        "resilience": [
            check_multi_az_deployment,
            check_backup_coverage,
            check_auto_scaling_configuration,
            check_route53_failover,
            detect_single_points_of_failure,
        ],
        "saas": [
            check_tenant_isolation,
            check_resource_tagging,
            check_control_plane_separation,
            check_cost_allocation_tags,
            check_tenant_observability,
        ],
    }

    tools = []
    for module in modules:
        tools.extend(tool_map.get(module, []))
    return tools


def create_agent(
    model_id: str = "us.anthropic.claude-opus-4-8",
    region: str = "us-east-1",
    modules: list[str] | None = None,
) -> Agent:
    """Create an ASTRA agent instance.

    Args:
        model_id: Bedrock model/inference profile ID. Default: Claude Opus 4.8 (most capable).
        region: AWS region for Bedrock calls.
        modules: Which modules to load tools for. Default: all modules.
    """
    if modules is None:
        modules = ["security", "resilience", "saas"]

    model = BedrockModel(model_id=model_id, region_name=region)
    tools = _get_tools_for_modules(modules)
    return Agent(model=model, tools=tools, system_prompt=SYSTEM_PROMPT)
