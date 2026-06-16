"""Unified assessment runner — runs any combination of checklists + optional customer context."""

from dataclasses import asdict
from pathlib import Path

import boto3
from strands import Agent
from strands.models.bedrock import BedrockModel

from astra.checklist.resilience import CheckResult, Status, run_resilience_checklist
from astra.checklist.saas import run_saas_checklist
from astra.checklist.security import run_security_checklist

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

_REPORT_PROMPT = """\
You are ASTRA — an autonomous AWS assessment agent producing executive-grade reports.

## Account: {account_id}
## Modules assessed: {modules_str}

## Checklist Results

{results_text}

## Well-Architected Best Practice Context

{wa_context}

{customer_context_section}

## Your Task

Produce a JSON report with this exact structure:
{{
  "account_id": "{account_id}",
  "overall_score": <0-100>,
  "risk_level": "CRITICAL|HIGH|MEDIUM|LOW",
  "executive_summary": "<4-6 sentences summarising posture across all modules. If customer context was provided, reference how findings relate to their stated architecture.>",
  "modules_assessed": {modules_json},
  "scores_by_module": {{
    "<module>": {{
      "score": <0-100>,
      "summary": "<1-2 sentences>"
    }}
  }},
  "checks": [
    {{
      "check_id": "<id>",
      "module": "<security|resilience|saas>",
      "title": "<title>",
      "status": "PASS|FAIL|WARNING|ERROR",
      "wa_reference": "<WA question/best practice>",
      "finding": "<what was found — specific with numbers>",
      "recommendation": "<actionable remediation step>",
      "priority": "CRITICAL|HIGH|MEDIUM|LOW",
      "affected_resources": ["<resource ids>"]
    }}
  ],
  "top_recommendations": [
    "<most impactful recommendation 1>",
    "<most impactful recommendation 2>",
    "<most impactful recommendation 3>",
    "<most impactful recommendation 4>",
    "<most impactful recommendation 5>"
  ]
}}

Rules:
- Score per module: 100 = all PASS. Deduct ~8 per FAIL, ~4 per WARNING.
- Overall score = weighted average of module scores.
- Only include detailed finding/recommendation for non-PASS checks. PASS checks: finding="Compliant", recommendation="None required".
- Priority: FAIL affecting many resources or critical services = CRITICAL/HIGH. Single-service = MEDIUM. WARNING = LOW.
- Be specific — cite resource IDs, counts, and concrete fix steps.
- If customer context was provided, tailor recommendations to their specific architecture (e.g. if they document RTO requirements, compare against actual backup configuration).
- Return ONLY valid JSON, no markdown wrapping.
"""


def _load_wa_context(modules: list[str]) -> str:
    """Load Well-Architected knowledge base files for requested modules."""
    sections = []
    for mod in modules:
        kb_dir = _KNOWLEDGE_DIR / mod
        if kb_dir.exists():
            for f in kb_dir.glob("*.md"):
                sections.append(f.read_text()[:3000])
    return "\n---\n".join(sections) if sections else "No WA context available."


def _load_customer_context(context_dir: str | Path | None) -> str:
    """Load customer documentation from the context directory."""
    if not context_dir:
        return ""
    context_path = Path(context_dir)
    if not context_path.exists():
        return ""

    docs = []
    for ext in ("*.md", "*.txt", "*.yaml", "*.yml", "*.json"):
        for f in sorted(context_path.glob(ext)):
            content = f.read_text(errors="ignore")[:5000]
            docs.append(f"### {f.name}\n{content}")

    if not docs:
        return ""
    return "\n\n".join(docs[:10])  # Cap at 10 files


def _format_results(results: list[CheckResult], module: str) -> str:
    lines = []
    for r in results:
        icon = {"PASS": "✅", "FAIL": "❌", "WARNING": "⚠️", "ERROR": "🚫"}.get(r.status.value, "?")
        lines.append(f"{icon} [{r.check_id}] ({module}) {r.title}: {r.status.value}")
        if r.status != Status.PASS:
            if r.evidence:
                lines.append(f"   Evidence: {r.evidence}")
            if r.affected_resources:
                lines.append(f"   Affected: {', '.join(r.affected_resources[:5])}")
            if r.recommendation:
                lines.append(f"   Recommendation: {r.recommendation}")
        lines.append("")
    return "\n".join(lines)


CHECKLIST_MAP = {
    "resilience": run_resilience_checklist,
    "security": run_security_checklist,
    "saas": run_saas_checklist,
}


def run_assessment(
    modules: list[str] | None = None,
    model_id: str = "us.anthropic.claude-sonnet-4-20250514",
    region: str = "us-east-1",
    account_id: str | None = None,
    context_dir: str | Path | None = None,
) -> dict:
    """Run the full assessment: deterministic checks + LLM analysis.

    Args:
        modules: List of modules to assess. Default: all.
        model_id: Bedrock model ID for report generation.
        region: AWS region for Bedrock.
        account_id: AWS account ID (auto-detected if None).
        context_dir: Path to customer documentation folder for context-aware recommendations.

    Returns:
        dict with raw results and LLM-generated report JSON.
    """
    if modules is None:
        modules = ["security", "resilience", "saas"]

    # Auto-detect account
    if not account_id:
        try:
            account_id = boto3.client("sts").get_caller_identity()["Account"]
        except Exception:
            account_id = "Unknown"

    # Phase 1: Run all checks
    all_results: list[CheckResult] = []
    results_text_parts = []

    for mod in modules:
        runner = CHECKLIST_MAP.get(mod)
        if not runner:
            continue
        print(f"🔍 Running {mod} checklist...")
        mod_results = runner()
        all_results.extend(mod_results)
        results_text_parts.append(_format_results(mod_results, mod))

        passed = sum(1 for r in mod_results if r.status == Status.PASS)
        failed = sum(1 for r in mod_results if r.status == Status.FAIL)
        warnings = sum(1 for r in mod_results if r.status == Status.WARNING)
        print(f"   ✅ {passed} | ❌ {failed} | ⚠️ {warnings}")

    print(f"\n📊 Total: {len(all_results)} checks across {len(modules)} module(s)")

    # Phase 2: Load context
    wa_context = _load_wa_context(modules)
    customer_context = _load_customer_context(context_dir)

    customer_context_section = ""
    if customer_context:
        print(f"📄 Customer context loaded ({len(customer_context)} chars)")
        customer_context_section = f"## Customer Architecture Context (provided by customer)\n\n{customer_context}\n\nUse this context to tailor your recommendations. Compare their stated architecture against actual findings."

    # Phase 3: LLM report generation
    print("\n📝 Generating assessment report...")
    import json
    prompt = _REPORT_PROMPT.format(
        account_id=account_id,
        modules_str=", ".join(modules),
        modules_json=json.dumps(modules),
        results_text="\n".join(results_text_parts),
        wa_context=wa_context[:6000],
        customer_context_section=customer_context_section,
    )

    model = BedrockModel(model_id=model_id, region_name=region)
    agent = Agent(model=model, tools=[], system_prompt="You are a technical report generator. Return only valid JSON.")
    response = agent(prompt)

    return {
        "account_id": account_id,
        "modules": modules,
        "raw_results": [asdict(r) for r in all_results],
        "report": str(response),
        "context_provided": bool(customer_context),
    }
