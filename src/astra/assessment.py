"""Unified assessment runner — concurrent checks + optional LLM analysis."""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

import boto3
from strands import Agent
from strands.models.bedrock import BedrockModel

from astra.checklist import CheckResult, Status
from astra.checklist.resilience import run_resilience_checklist
from astra.checklist.saas import run_saas_checklist
from astra.checklist.security import run_security_checklist

_KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"

CHECKLIST_MAP = {
    "security": run_security_checklist,
    "resilience": run_resilience_checklist,
    "saas": run_saas_checklist,
}

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
    {{
      "action": "<specific remediation step>",
      "why": "<why this matters — risk/business impact if not addressed>",
      "risk_if_ignored": "<concrete consequence — e.g. 'Full account compromise possible within hours of credential leak'>",
      "impact": "<what improves once implemented — e.g. eliminates single point of failure>",
      "score_improvement": "+<estimated points> to <module> score"
    }}
  ]
}}

Rules:
- Score per module: 100 = all PASS. Deduct ~8 per FAIL, ~4 per WARNING.
- Overall score = weighted average of module scores.
- Only include detailed finding/recommendation for non-PASS checks. PASS checks: finding="Compliant", recommendation="None required".
- Priority: FAIL affecting many resources or critical services = CRITICAL/HIGH. Single-service = MEDIUM. WARNING = LOW.
- Be specific — cite resource IDs, counts, and concrete fix steps.
- If customer context was provided, tailor recommendations to their specific architecture.
- Return ONLY valid JSON, no markdown wrapping.
"""


def _load_wa_context(modules: list[str]) -> str:
    sections = []
    for mod in modules:
        kb_dir = _KNOWLEDGE_DIR / mod
        if kb_dir.exists():
            for f in kb_dir.glob("*.md"):
                sections.append(f.read_text()[:3000])
    return "\n---\n".join(sections) if sections else ""


def _load_customer_context(context_dir: str | Path | None) -> str:
    if not context_dir:
        return ""
    context_path = Path(context_dir)
    if not context_path.exists():
        return ""
    docs = []

    # Text-based formats (always supported)
    for ext in ("*.md", "*.txt", "*.yaml", "*.yml", "*.json", "*.csv", "*.toml", "*.ini", "*.cfg"):
        for f in sorted(context_path.glob(ext)):
            docs.append(f"### {f.name}\n{f.read_text(errors='ignore')[:5000]}")

    # PDF support (optional — pip install astra-agent[docs])
    for f in sorted(context_path.glob("*.pdf")):
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(f))
            text = "\n".join(page.extract_text() or "" for page in reader.pages[:20])
            docs.append(f"### {f.name}\n{text[:5000]}")
        except ImportError:
            docs.append(f"### {f.name}\n[PDF detected but pypdf not installed. Run: pip install 'astra-agent[docs]']")
        except Exception:
            docs.append(f"### {f.name}\n[Could not read PDF]")

    # DOCX support (optional — pip install astra-agent[docs])
    for f in sorted(context_path.glob("*.docx")):
        try:
            from docx import Document
            doc = Document(str(f))
            text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
            docs.append(f"### {f.name}\n{text[:5000]}")
        except ImportError:
            docs.append(f"### {f.name}\n[DOCX detected but python-docx not installed. Run: pip install 'astra-agent[docs]']")
        except Exception:
            docs.append(f"### {f.name}\n[Could not read DOCX]")
    return "\n\n".join(docs[:10])


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
                lines.append(f"   Rec: {r.recommendation}")
        lines.append("")
    return "\n".join(lines)


def run_checks(modules: list[str]) -> dict[str, list[CheckResult]]:
    """Run all checks concurrently across modules. Returns {module: [results]}."""
    results: dict[str, list[CheckResult]] = {}

    def _run_module(mod: str) -> tuple[str, list[CheckResult]]:
        runner = CHECKLIST_MAP[mod]
        return mod, runner()

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(_run_module, mod): mod for mod in modules if mod in CHECKLIST_MAP}
        for future in as_completed(futures):
            mod, mod_results = future.result()
            results[mod] = mod_results

    return results


def run_assessment(
    modules: list[str] | None = None,
    model_id: str = "us.anthropic.claude-opus-4-8",
    region: str = "us-east-1",
    account_id: str | None = None,
    context_dir: str | Path | None = None,
    checks_only: bool = False,
) -> dict:
    """Run assessment: concurrent checks + optional LLM analysis.

    Args:
        modules: Modules to assess. Default: all.
        model_id: Bedrock model ID.
        region: AWS region for Bedrock.
        account_id: AWS account ID (auto-detected if None).
        context_dir: Customer docs folder for context-aware recommendations.
        checks_only: If True, skip LLM — return raw check results only (fast, free).
    """
    if modules is None:
        modules = ["security", "resilience", "saas"]

    if not account_id:
        try:
            account_id = boto3.client("sts").get_caller_identity()["Account"]
        except Exception:
            account_id = "Unknown"

    # Phase 1: Run checks concurrently
    t0 = time.time()
    print(f"🔍 Running {sum(len(CHECKLIST_MAP[m].__module__.split('.')) and 1 for m in modules if m in CHECKLIST_MAP) or len(modules)} module(s) concurrently...")
    module_results = run_checks(modules)
    checks_time = time.time() - t0

    # Infrastructure discovery (concurrent with above via same thread pool)
    print("🗺️  Discovering infrastructure...")
    from astra.discovery import discover_infrastructure
    infra = discover_infrastructure()

    # Print summary
    all_results: list[CheckResult] = []
    results_text_parts = []
    for mod in modules:
        mod_results = module_results.get(mod, [])
        all_results.extend(mod_results)
        results_text_parts.append(_format_results(mod_results, mod))
        p = sum(1 for r in mod_results if r.status == Status.PASS)
        f = sum(1 for r in mod_results if r.status == Status.FAIL)
        w = sum(1 for r in mod_results if r.status == Status.WARNING)
        print(f"   {mod:12s}: ✅ {p} | ❌ {f} | ⚠️ {w}")

    print(f"\n📊 {len(all_results)} checks completed in {checks_time:.1f}s")

    # Checks-only mode: return raw results as JSON, no LLM call
    if checks_only:
        from astra.diagram import generate_html_diagram

        # Tag each check with its module based on prefix
        prefix_to_module = {"SEC": "security", "REL": "resilience", "SAA": "saas"}
        checks_with_module = []
        for r in all_results:
            d = asdict(r)
            d["module"] = prefix_to_module.get(r.check_id[:3], "security")
            checks_with_module.append(d)

        return {
            "account_id": account_id,
            "modules": modules,
            "raw_results": checks_with_module,
            "report": json.dumps({
                "account_id": account_id,
                "modules_assessed": modules,
                "checks": checks_with_module,
                "total_checks": len(all_results),
                "passed": sum(1 for r in all_results if r.status == Status.PASS),
                "failed": sum(1 for r in all_results if r.status == Status.FAIL),
                "warnings": sum(1 for r in all_results if r.status == Status.WARNING),
            }, indent=2, default=str),
            "context_provided": False,
            "elapsed_seconds": checks_time,
            "mermaid_diagram": generate_html_diagram(infra, all_results),
        }

    # Phase 2: Load context
    wa_context = _load_wa_context(modules)
    customer_context = _load_customer_context(context_dir)
    customer_context_section = ""
    if customer_context:
        print(f"📄 Customer context loaded ({len(customer_context)} chars)")
        customer_context_section = f"## Customer Architecture Context\n\n{customer_context}\n\nTailor recommendations to this architecture."

    # Phase 3: LLM report
    t1 = time.time()
    print("📝 Generating report (LLM)...")
    from astra.diagram import generate_html_diagram
    prompt = _REPORT_PROMPT.format(
        account_id=account_id,
        modules_str=", ".join(modules),
        modules_json=json.dumps(modules),
        results_text="\n".join(results_text_parts),
        wa_context=wa_context[:6000],
        customer_context_section=customer_context_section,
    )

    model = BedrockModel(model_id=model_id, region_name=region, max_tokens=16000)
    agent = Agent(model=model, tools=[], system_prompt="You are a technical report generator. Return only valid JSON.")
    response = agent(prompt)
    llm_time = time.time() - t1

    total_time = time.time() - t0
    print(f"⏱️  Checks: {checks_time:.1f}s | Report: {llm_time:.1f}s | Total: {total_time:.1f}s")

    return {
        "account_id": account_id,
        "modules": modules,
        "raw_results": [asdict(r) for r in all_results],
        "report": str(response),
        "context_provided": bool(customer_context),
        "elapsed_seconds": total_time,
        "mermaid_diagram": generate_html_diagram(infra, all_results),
    }
