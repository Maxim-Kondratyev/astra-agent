"""HTML report generator — transforms agent JSON output into a styled HTML report."""

import json
import re
from datetime import datetime, timezone


def extract_json_from_output(agent_output: str) -> dict | None:
    """Extract the JSON assessment from agent output text."""
    match = re.search(r"```json\s*(\{.*?\})\s*```", agent_output, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # Try finding raw JSON (starts with { and has "overall_score")
    match = re.search(r'(\{"overall_score".*\})', agent_output, re.DOTALL)
    if match:
        # Find the matching closing brace
        text = match.group(0)
        depth = 0
        for i, c in enumerate(text):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[:i+1])
                    except json.JSONDecodeError:
                        break
    try:
        return json.loads(agent_output)
    except (json.JSONDecodeError, TypeError):
        return None


def severity_color(severity: str) -> str:
    return {"CRITICAL": "#dc2626", "HIGH": "#ea580c", "MEDIUM": "#ca8a04", "LOW": "#2563eb", "INFORMATIONAL": "#6b7280"}.get(severity, "#6b7280")


def score_color(score: int) -> str:
    if score >= 80:
        return "#16a34a"
    if score >= 60:
        return "#ca8a04"
    if score >= 40:
        return "#ea580c"
    return "#dc2626"


MODULE_ICONS = {"security": "🛡️", "resilience": "🏗️", "saas": "🏢"}
MODULE_NAMES = {"security": "Security", "resilience": "Resilience", "saas": "SaaS / Tenancy"}


def _normalize_checklist_to_findings(data: dict) -> dict:
    """Convert checklist report format to the standard findings format for HTML rendering."""
    if "checks" in data and "findings" not in data:
        findings = []
        for check in data["checks"]:
            if check.get("status") != "PASS":
                findings.append({
                    "module": check.get("module", "resilience"),
                    "severity": check.get("priority", "MEDIUM"),
                    "category": check.get("wa_reference", ""),
                    "title": check.get("title", ""),
                    "description": check.get("finding", ""),
                    "affected_resources": check.get("affected_resources", []),
                    "recommendation": check.get("recommendation", ""),
                    "reference": check.get("wa_reference", ""),
                })
        data["findings"] = findings
        data.setdefault("modules_assessed", data.get("modules_assessed", ["resilience"]))
        data.setdefault("summary", data.get("executive_summary", ""))

        # Build scores_by_module for display
        sbm = data.get("scores_by_module", {})
        if sbm and isinstance(next(iter(sbm.values()), None), dict):
            for mod, mod_data in sbm.items():
                if "categories" not in mod_data:
                    mod_data["categories"] = {mod.title(): mod_data.get("score", 0)}
        data["scores_by_module"] = sbm
    return data


def generate_html_report(agent_output: str, account_id: str = "Unknown", mermaid_diagram: str | None = None) -> str:
    """Generate a styled HTML report from the agent's JSON assessment output."""
    data = extract_json_from_output(agent_output)
    if not data:
        return f"<html><body><h1>Error</h1><p>Could not parse assessment output.</p><pre>{agent_output[:3000]}</pre></body></html>"

    data = _normalize_checklist_to_findings(data)

    score = data.get("overall_score", 0)
    risk = data.get("risk_level", "UNKNOWN")
    summary = data.get("summary", "")
    findings = data.get("findings", [])
    modules_assessed = data.get("modules_assessed", ["security"])
    scores_by_module = data.get("scores_by_module", {})
    # Legacy format support
    if not scores_by_module and "scores_by_category" in data:
        scores_by_module = {"security": {"score": score, "categories": data["scores_by_category"]}}
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Module score cards
    module_cards_html = ""
    for mod in modules_assessed:
        mod_data = scores_by_module.get(mod, {})
        mod_score = mod_data.get("score", 0)
        categories = mod_data.get("categories", {})
        icon = MODULE_ICONS.get(mod, "📊")
        name = MODULE_NAMES.get(mod, mod.title())

        cat_bars = ""
        for cat, cat_score in categories.items():
            cat_bars += f"""<div class="cat-row"><span class="cat-label">{cat}</span><div class="bar-bg"><div class="bar-fill" style="width:{cat_score}%;background:{score_color(cat_score)};"></div></div><span class="cat-score">{cat_score}</span></div>"""

        module_cards_html += f"""
        <div class="module-card">
            <div class="module-header">
                <span class="module-icon">{icon}</span>
                <span class="module-name">{name}</span>
                <span class="module-score" style="color:{score_color(mod_score)};">{mod_score}/100</span>
            </div>
            <div class="module-categories">{cat_bars}</div>
        </div>"""

    # Findings grouped by module
    findings_html = ""
    for f in findings:
        sev = f.get("severity", "")
        mod = f.get("module", "")
        resources = ", ".join(f.get("affected_resources", [])[:3])
        if len(f.get("affected_resources", [])) > 3:
            resources += f" (+{len(f['affected_resources']) - 3} more)"
        findings_html += f"""
        <div class="finding" style="border-left: 4px solid {severity_color(sev)};">
            <div class="finding-header">
                <span class="severity" style="background:{severity_color(sev)};">{sev}</span>
                <span class="category">{f.get('category', '')}</span>
                <span class="module-badge">{MODULE_ICONS.get(mod, '')} {mod}</span>
            </div>
            <h3>{f.get('title', '')}</h3>
            <p>{f.get('description', '')}</p>
            <div class="resources"><strong>Affected:</strong> <code>{resources}</code></div>
            <div class="recommendation"><strong>Fix:</strong> {f.get('recommendation', '')}</div>
            <div class="reference"><em>{f.get('reference', '')}</em></div>
        </div>"""

    severity_counts = {}
    for f in findings:
        s = f.get("severity", "UNKNOWN")
        severity_counts[s] = severity_counts.get(s, 0) + 1

    severity_summary = " · ".join(f'<span style="color:{severity_color(s)};">{c} {s}</span>' for s, c in sorted(severity_counts.items(), key=lambda x: ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"].index(x[0]) if x[0] in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFORMATIONAL"] else 99))

    # Top recommendations (from checklist reports)
    top_recs = data.get("top_recommendations", [])
    if top_recs:
        recs_items = ""
        for i, r in enumerate(top_recs, 1):
            if isinstance(r, dict):
                recs_items += f'''<div style="background:white;border-radius:12px;padding:1.2rem 1.5rem;margin-bottom:1rem;box-shadow:0 2px 8px rgba(0,0,0,0.05);border:1px solid #f1f5f9;">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;"><strong style="font-size:0.95rem;">{i}. {r.get("action","")}</strong><span style="background:#dcfce7;color:#166534;padding:3px 10px;border-radius:6px;font-size:0.75rem;font-weight:600;">{r.get("score_improvement","")}</span></div>
<p style="font-size:0.82rem;color:#475569;margin-bottom:0.4rem;"><strong>Why:</strong> {r.get("why","")}</p>
<p style="font-size:0.82rem;color:#991b1b;background:#fef2f2;padding:0.5rem 0.8rem;border-radius:6px;border:1px solid #fecaca;margin-bottom:0.4rem;"><strong>⚠️ Risk if not addressed:</strong> {r.get("risk_if_ignored","")}</p>
<p style="font-size:0.82rem;color:#1e40af;"><strong>Impact once fixed:</strong> {r.get("impact","")}</p></div>'''
            else:
                recs_items += f"<li style='margin-bottom:0.5rem;'>{r}</li>"
        if isinstance(top_recs[0], dict):
            top_recs_html = f'<div class="findings-section"><h2>🎯 Top Recommendations</h2>{recs_items}</div>'
        else:
            top_recs_html = f'<div class="findings-section"><h2>🎯 Top Recommendations</h2><ol style="background:white;border-radius:12px;padding:1.5rem 1.5rem 1.5rem 2.5rem;box-shadow:0 2px 8px rgba(0,0,0,0.05);font-size:0.9rem;line-height:2;border:1px solid #f1f5f9;">{recs_items}</ol></div>'
    else:
        top_recs_html = ""

    # Checklist summary table
    checks = data.get("checks", [])

    # Architecture diagram (Mermaid)
    if mermaid_diagram:
        diagram_html = f'''<div class="findings-section"><h2>🗺️ Infrastructure Architecture</h2>
<div style="background:white;border-radius:12px;padding:1.5rem;box-shadow:0 1px 4px rgba(0,0,0,0.08);overflow-x:auto;">
<pre class="mermaid">{mermaid_diagram}</pre>
</div>
<p style="font-size:0.7rem;color:#94a3b8;margin-top:0.5rem;">⚠️ indicates a finding from the assessment. Diagram shows resources discovered during read-only scan.</p>
</div>'''
    else:
        diagram_html = ""
    if checks:
        rows = ""
        for c in checks:
            status = c.get("status", "")
            icon = {"PASS": "✅", "FAIL": "❌", "WARNING": "⚠️", "ERROR": "🚫"}.get(status, "?")
            mod = c.get("module", "")
            rows += f'<tr><td>{icon}</td><td><strong>{c.get("check_id", "")}</strong></td><td>{c.get("title", "")}</td><td>{MODULE_ICONS.get(mod, "")} {mod}</td><td>{c.get("finding", "")[:80]}</td></tr>'
        checklist_table_html = f'''<div class="findings-section"><h2>📋 Checklist Summary</h2>
<div style="background:white;border-radius:12px;padding:1rem;box-shadow:0 1px 4px rgba(0,0,0,0.08);overflow-x:auto;">
<table style="width:100%;border-collapse:collapse;font-size:0.8rem;">
<tr style="border-bottom:2px solid #e2e8f0;text-align:left;"><th style="padding:0.5rem;">⠀</th><th style="padding:0.5rem;">ID</th><th style="padding:0.5rem;">Check</th><th style="padding:0.5rem;">Module</th><th style="padding:0.5rem;">Finding</th></tr>
{rows}</table></div></div>'''
    else:
        checklist_table_html = ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ASTRA Report — Account {account_id} — {timestamp}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#f8fafc; color:#1e293b; line-height:1.7; font-size:15px; }}
.container {{ max-width:1040px; margin:0 auto; padding:2.5rem 2rem; }}
header {{ background:linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f4c81 100%); color:white; padding:3rem; border-radius:20px; margin-bottom:2.5rem; box-shadow:0 10px 40px rgba(15,23,42,0.3); }}
header h1 {{ font-size:2.2rem; margin-bottom:0.4rem; font-weight:700; letter-spacing:-0.02em; }}
header .subtitle {{ opacity:0.75; font-size:0.85rem; letter-spacing:0.01em; }}
.score-section {{ display:flex; gap:2.5rem; align-items:center; background:white; border-radius:20px; padding:2.5rem; margin-bottom:2.5rem; box-shadow:0 2px 12px rgba(0,0,0,0.06); border:1px solid #e2e8f0; }}
.score-circle {{ width:130px; height:130px; border-radius:50%; display:flex; flex-direction:column; align-items:center; justify-content:center; color:white; font-weight:700; flex-shrink:0; box-shadow:0 6px 20px rgba(0,0,0,0.15); }}
.score-circle .number {{ font-size:2.8rem; line-height:1; }}
.score-circle .label {{ font-size:0.7rem; text-transform:uppercase; opacity:0.9; margin-top:2px; }}
.score-info {{ flex:1; }}
.score-info h2 {{ font-size:1.3rem; margin-bottom:0.5rem; font-weight:600; }}
.score-info .summary {{ color:#475569; font-size:0.9rem; line-height:1.7; }}
.severity-bar {{ margin-top:1rem; font-size:0.8rem; }}
.modules-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(290px, 1fr)); gap:1.5rem; margin-bottom:2.5rem; }}
.module-card {{ background:white; border-radius:16px; padding:1.8rem; box-shadow:0 2px 12px rgba(0,0,0,0.06); border:1px solid #e2e8f0; transition:transform 0.2s,box-shadow 0.2s; }}
.module-card:hover {{ transform:translateY(-2px); box-shadow:0 8px 25px rgba(0,0,0,0.1); }}
.module-header {{ display:flex; align-items:center; gap:0.6rem; margin-bottom:1.2rem; padding-bottom:1rem; border-bottom:1px solid #f1f5f9; }}
.module-icon {{ font-size:1.4rem; }}
.module-name {{ flex:1; font-weight:600; font-size:1.05rem; }}
.module-score {{ font-size:1.4rem; font-weight:700; }}
.cat-row {{ display:flex; align-items:center; gap:0.6rem; margin-bottom:0.6rem; }}
.cat-label {{ width:140px; font-size:0.75rem; color:#64748b; font-weight:500; }}
.bar-bg {{ flex:1; height:10px; background:#f1f5f9; border-radius:5px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:5px; transition:width 0.6s ease; }}
.cat-score {{ width:28px; text-align:right; font-weight:600; font-size:0.8rem; }}
.findings-section {{ margin-bottom:2.5rem; }}
.findings-section h2 {{ font-size:1.3rem; margin-bottom:1.2rem; font-weight:600; }}
.finding {{ background:white; border-radius:14px; padding:1.5rem 1.8rem; margin-bottom:1.2rem; box-shadow:0 2px 8px rgba(0,0,0,0.05); border:1px solid #f1f5f9; }}
.finding-header {{ display:flex; gap:0.5rem; align-items:center; margin-bottom:0.6rem; flex-wrap:wrap; }}
.severity {{ color:white; padding:3px 10px; border-radius:6px; font-size:0.65rem; font-weight:700; text-transform:uppercase; letter-spacing:0.04em; }}
.category {{ font-size:0.7rem; color:#64748b; background:#f1f5f9; padding:3px 10px; border-radius:6px; }}
.module-badge {{ font-size:0.7rem; color:#64748b; background:#f1f5f9; padding:3px 10px; border-radius:6px; }}
.finding h3 {{ font-size:0.95rem; margin-bottom:0.4rem; color:#1e293b; font-weight:600; }}
.finding p {{ font-size:0.85rem; color:#475569; margin-bottom:0.5rem; }}
.resources {{ font-size:0.78rem; margin-bottom:0.4rem; color:#334155; }}
.resources code {{ font-size:0.72rem; background:#f1f5f9; padding:2px 6px; border-radius:4px; word-break:break-all; font-family:'SF Mono',Menlo,monospace; }}
.recommendation {{ font-size:0.82rem; color:#1e40af; background:linear-gradient(135deg,#eff6ff,#dbeafe); padding:0.7rem 1rem; border-radius:8px; margin-top:0.6rem; border:1px solid #bfdbfe; }}
.reference {{ font-size:0.72rem; color:#94a3b8; margin-top:0.4rem; }}
footer {{ text-align:center; font-size:0.75rem; color:#94a3b8; padding:3rem 1rem 1.5rem; }}
footer .guarantee {{ background:linear-gradient(135deg,#f0fdf4,#dcfce7); border:1px solid #bbf7d0; border-radius:12px; padding:1rem 1.5rem; margin-bottom:1.5rem; color:#166534; font-size:0.82rem; font-weight:500; }}
@media print {{ body {{ background:white; }} .container {{ padding:0; }} .module-card:hover {{ transform:none; }} .finding {{ break-inside:avoid; }} }}
</style>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<script>mermaid.initialize({{startOnLoad:true, theme:'neutral', securityLevel:'loose'}});</script>
</head>
<body>
<div class="container">
<header>
    <h1>ASTRA Assessment Report</h1>
    <div class="subtitle" style="font-size:0.95rem;opacity:0.9;margin-bottom:0.6rem;">Autonomous assessment of your AWS environment against Well-Architected Framework best practices</div>
    <div class="subtitle">Account: {account_id} · {timestamp} · Modules: {', '.join(MODULE_NAMES.get(m, m) for m in modules_assessed)}</div>
</header>

<div class="score-section">
    <div class="score-circle" style="background:{score_color(score)};">
        <span class="number">{score}</span>
        <span class="label">/ 100</span>
    </div>
    <div class="score-info">
        <h2>Overall Risk: {risk}</h2>
        <p class="summary">{summary}</p>
        <div class="severity-bar">{severity_summary}</div>
    </div>
</div>

<div class="modules-grid">
{module_cards_html}
</div>

{top_recs_html}

{diagram_html}

{checklist_table_html}

<div class="findings-section">
    <h2>Findings ({len(findings)})</h2>
    {findings_html}
</div>

<footer>
    <div class="guarantee">🔒 This assessment was performed using <strong>read-only access</strong>. No resources were created, modified, or deleted.</div>
    Generated by ASTRA — Autonomous Security, Tenancy & Resilience Assessor · Powered by Claude<br/>
    <span style="margin-top:0.5rem;display:inline-block;">Made with ❤️ and a mass of caffeine by STAM · Feedback & virtual high-fives → <a href="mailto:maxmax@amazon.de" style="color:#64748b;">maxmax@amazon.de</a></span>
</footer>
</div>
</body>
</html>"""
