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
    # Try raw JSON parse
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


def generate_html_report(agent_output: str, account_id: str = "Unknown") -> str:
    """Generate a styled HTML report from the agent's JSON assessment output.

    Args:
        agent_output: Raw text output from the ASTRA agent (contains JSON block).
        account_id: AWS account ID for the report header.

    Returns:
        Complete HTML document as a string.
    """
    data = extract_json_from_output(agent_output)
    if not data:
        return f"<html><body><h1>Error</h1><p>Could not parse assessment output.</p><pre>{agent_output[:2000]}</pre></body></html>"

    score = data.get("overall_score", 0)
    risk = data.get("risk_level", "UNKNOWN")
    summary = data.get("summary", "")
    findings = data.get("findings", [])
    categories = data.get("scores_by_category", {})
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    findings_html = ""
    for f in findings:
        sev = f.get("severity", "")
        resources = ", ".join(f.get("affected_resources", []))
        findings_html += f"""
        <div class="finding" style="border-left: 4px solid {severity_color(sev)};">
            <div class="finding-header">
                <span class="severity" style="background:{severity_color(sev)};">{sev}</span>
                <span class="category">{f.get('category', '')}</span>
            </div>
            <h3>{f.get('title', '')}</h3>
            <p>{f.get('description', '')}</p>
            <div class="resources"><strong>Affected:</strong> {resources}</div>
            <div class="recommendation"><strong>Recommendation:</strong> {f.get('recommendation', '')}</div>
            <div class="reference"><em>{f.get('reference', '')}</em></div>
        </div>"""

    category_bars = ""
    for cat, cat_score in categories.items():
        category_bars += f"""
        <div class="cat-row">
            <span class="cat-label">{cat}</span>
            <div class="bar-bg"><div class="bar-fill" style="width:{cat_score}%;background:{score_color(cat_score)};"></div></div>
            <span class="cat-score">{cat_score}</span>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ASTRA Security Assessment — {account_id}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#f8fafc; color:#1e293b; line-height:1.6; }}
.container {{ max-width:900px; margin:0 auto; padding:2rem; }}
header {{ background:linear-gradient(135deg, #1e293b 0%, #334155 100%); color:white; padding:2rem; border-radius:12px; margin-bottom:2rem; }}
header h1 {{ font-size:1.8rem; margin-bottom:0.5rem; }}
header p {{ opacity:0.8; font-size:0.9rem; }}
.score-card {{ display:flex; align-items:center; gap:2rem; background:white; border-radius:12px; padding:1.5rem 2rem; margin-bottom:2rem; box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
.score-circle {{ width:100px; height:100px; border-radius:50%; display:flex; flex-direction:column; align-items:center; justify-content:center; color:white; font-weight:bold; }}
.score-circle .number {{ font-size:2rem; line-height:1; }}
.score-circle .label {{ font-size:0.7rem; text-transform:uppercase; }}
.summary {{ flex:1; }}
.summary h2 {{ font-size:1.1rem; margin-bottom:0.5rem; }}
.categories {{ background:white; border-radius:12px; padding:1.5rem 2rem; margin-bottom:2rem; box-shadow:0 1px 3px rgba(0,0,0,0.1); }}
.categories h2 {{ font-size:1.1rem; margin-bottom:1rem; }}
.cat-row {{ display:flex; align-items:center; gap:1rem; margin-bottom:0.7rem; }}
.cat-label {{ width:180px; font-size:0.85rem; }}
.bar-bg {{ flex:1; height:12px; background:#e2e8f0; border-radius:6px; overflow:hidden; }}
.bar-fill {{ height:100%; border-radius:6px; transition:width 0.5s; }}
.cat-score {{ width:30px; text-align:right; font-weight:600; font-size:0.85rem; }}
.findings {{ margin-bottom:2rem; }}
.findings h2 {{ font-size:1.1rem; margin-bottom:1rem; }}
.finding {{ background:white; border-radius:8px; padding:1.2rem 1.5rem; margin-bottom:1rem; box-shadow:0 1px 3px rgba(0,0,0,0.08); }}
.finding-header {{ display:flex; gap:0.5rem; align-items:center; margin-bottom:0.5rem; }}
.severity {{ color:white; padding:2px 8px; border-radius:4px; font-size:0.7rem; font-weight:600; text-transform:uppercase; }}
.category {{ font-size:0.75rem; color:#64748b; background:#f1f5f9; padding:2px 8px; border-radius:4px; }}
.finding h3 {{ font-size:0.95rem; margin-bottom:0.4rem; }}
.finding p {{ font-size:0.85rem; color:#475569; margin-bottom:0.5rem; }}
.resources, .recommendation {{ font-size:0.8rem; margin-bottom:0.3rem; color:#334155; }}
.reference {{ font-size:0.75rem; color:#64748b; }}
footer {{ text-align:center; font-size:0.75rem; color:#94a3b8; padding:1rem; }}
</style>
</head>
<body>
<div class="container">
<header>
    <h1>🛡️ ASTRA Security Assessment</h1>
    <p>Account: {account_id} | Generated: {timestamp} | Model: Claude Sonnet 4.6</p>
</header>

<div class="score-card">
    <div class="score-circle" style="background:{score_color(score)};">
        <span class="number">{score}</span>
        <span class="label">/ 100</span>
    </div>
    <div class="summary">
        <h2>Risk Level: {risk}</h2>
        <p>{summary}</p>
    </div>
</div>

<div class="categories">
    <h2>Scores by Category</h2>
    {category_bars}
</div>

<div class="findings">
    <h2>Findings ({len(findings)})</h2>
    {findings_html}
</div>

<footer>
    Generated by ASTRA — Autonomous Security, Tenancy & Resilience Assessor<br>
    Read-only assessment. No resources were modified.
</footer>
</div>
</body>
</html>"""
