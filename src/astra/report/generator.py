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


def generate_html_report(agent_output: str, account_id: str = "Unknown") -> str:
    """Generate a styled HTML report from the agent's JSON assessment output."""
    data = extract_json_from_output(agent_output)
    if not data:
        return f"<html><body><h1>Error</h1><p>Could not parse assessment output.</p><pre>{agent_output[:3000]}</pre></body></html>"

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

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ASTRA Assessment — {account_id}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#f8fafc; color:#1e293b; line-height:1.6; }}
.container {{ max-width:1000px; margin:0 auto; padding:2rem; }}
header {{ background:linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%); color:white; padding:2.5rem; border-radius:16px; margin-bottom:2rem; }}
header h1 {{ font-size:2rem; margin-bottom:0.3rem; }}
header .subtitle {{ opacity:0.7; font-size:0.85rem; }}
.score-section {{ display:flex; gap:2rem; align-items:center; background:white; border-radius:16px; padding:2rem; margin-bottom:2rem; box-shadow:0 1px 4px rgba(0,0,0,0.08); }}
.score-circle {{ width:120px; height:120px; border-radius:50%; display:flex; flex-direction:column; align-items:center; justify-content:center; color:white; font-weight:700; flex-shrink:0; }}
.score-circle .number {{ font-size:2.5rem; line-height:1; }}
.score-circle .label {{ font-size:0.7rem; text-transform:uppercase; opacity:0.9; }}
.score-info {{ flex:1; }}
.score-info h2 {{ font-size:1.2rem; margin-bottom:0.5rem; }}
.score-info .summary {{ color:#475569; font-size:0.9rem; }}
.severity-bar {{ margin-top:0.8rem; font-size:0.8rem; }}
.modules-grid {{ display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:1.5rem; margin-bottom:2rem; }}
.module-card {{ background:white; border-radius:12px; padding:1.5rem; box-shadow:0 1px 4px rgba(0,0,0,0.08); }}
.module-header {{ display:flex; align-items:center; gap:0.5rem; margin-bottom:1rem; padding-bottom:0.8rem; border-bottom:1px solid #e2e8f0; }}
.module-icon {{ font-size:1.3rem; }}
.module-name {{ flex:1; font-weight:600; }}
.module-score {{ font-size:1.3rem; font-weight:700; }}
.cat-row {{ display:flex; align-items:center; gap:0.6rem; margin-bottom:0.5rem; }}
.cat-label {{ width:140px; font-size:0.75rem; color:#64748b; }}
.bar-bg {{ flex:1; height:8px; background:#e2e8f0; border-radius:4px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:4px; }}
.cat-score {{ width:24px; text-align:right; font-weight:600; font-size:0.75rem; }}
.findings-section h2 {{ font-size:1.2rem; margin-bottom:1rem; }}
.finding {{ background:white; border-radius:10px; padding:1.2rem 1.5rem; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.06); }}
.finding-header {{ display:flex; gap:0.5rem; align-items:center; margin-bottom:0.5rem; flex-wrap:wrap; }}
.severity {{ color:white; padding:2px 8px; border-radius:4px; font-size:0.65rem; font-weight:700; text-transform:uppercase; letter-spacing:0.03em; }}
.category {{ font-size:0.7rem; color:#64748b; background:#f1f5f9; padding:2px 8px; border-radius:4px; }}
.module-badge {{ font-size:0.7rem; color:#64748b; background:#f1f5f9; padding:2px 8px; border-radius:4px; }}
.finding h3 {{ font-size:0.9rem; margin-bottom:0.4rem; color:#1e293b; }}
.finding p {{ font-size:0.82rem; color:#475569; margin-bottom:0.5rem; }}
.resources {{ font-size:0.75rem; margin-bottom:0.3rem; color:#334155; }}
.resources code {{ font-size:0.7rem; background:#f1f5f9; padding:1px 4px; border-radius:3px; word-break:break-all; }}
.recommendation {{ font-size:0.8rem; margin-bottom:0.3rem; color:#1e40af; background:#eff6ff; padding:0.5rem 0.7rem; border-radius:6px; margin-top:0.5rem; }}
.reference {{ font-size:0.7rem; color:#94a3b8; margin-top:0.3rem; }}
footer {{ text-align:center; font-size:0.75rem; color:#94a3b8; padding:2rem 1rem 1rem; }}
footer .guarantee {{ background:#f0fdf4; border:1px solid #bbf7d0; border-radius:8px; padding:0.7rem 1rem; margin-bottom:1rem; color:#166534; font-size:0.8rem; }}
</style>
</head>
<body>
<div class="container">
<header>
    <h1>ASTRA Assessment Report</h1>
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

<div class="findings-section">
    <h2>Findings ({len(findings)})</h2>
    {findings_html}
</div>

<footer>
    <div class="guarantee">🔒 This assessment was performed using <strong>read-only access</strong>. No resources were created, modified, or deleted.</div>
    Generated by ASTRA — Autonomous Security, Tenancy & Resilience Assessor · Powered by Claude Opus 4.8
</footer>
</div>
</body>
</html>"""
