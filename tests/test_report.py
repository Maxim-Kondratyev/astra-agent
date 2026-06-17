"""Tests for report generator."""

import json

from astra.report.generator import extract_json_from_output, generate_html_report


def _make_report(**overrides):
    """Helper to create a valid report JSON string."""
    data = {
        "account_id": "123456789012",
        "overall_score": 72,
        "risk_level": "MEDIUM",
        "executive_summary": "The account has moderate risk.",
        "modules_assessed": ["security", "resilience"],
        "scores_by_module": {
            "security": {"score": 85, "summary": "Good"},
            "resilience": {"score": 60, "summary": "Needs work"},
        },
        "checks": [
            {"check_id": "SEC-01", "module": "security", "title": "Security Hub", "status": "PASS",
             "wa_reference": "SEC 4", "finding": "Compliant", "recommendation": "None", "priority": "LOW", "affected_resources": []},
            {"check_id": "REL-01", "module": "resilience", "title": "RDS Multi-AZ", "status": "FAIL",
             "wa_reference": "REL 10", "finding": "2 instances single-AZ", "recommendation": "Enable Multi-AZ",
             "priority": "HIGH", "affected_resources": ["mydb-1", "mydb-2"]},
        ],
        "top_recommendations": ["Enable Multi-AZ for RDS", "Add backup plans"],
    }
    data.update(overrides)
    return json.dumps(data)


class TestExtractJSON:
    def test_raw_json(self):
        raw = '{"overall_score": 72, "risk_level": "HIGH"}'
        result = extract_json_from_output(raw)
        assert result["overall_score"] == 72

    def test_json_in_markdown(self):
        raw = 'Here is the report:\n```json\n{"overall_score": 90}\n```\nDone.'
        result = extract_json_from_output(raw)
        assert result["overall_score"] == 90

    def test_invalid_json_returns_none(self):
        result = extract_json_from_output("this is not json at all")
        assert result is None


class TestHTMLReport:
    def test_generates_valid_html(self):
        html = generate_html_report(_make_report(), account_id="123456789012")
        assert "<!DOCTYPE html>" in html
        assert "ASTRA Assessment" in html
        assert "123456789012" in html

    def test_contains_score(self):
        html = generate_html_report(_make_report(overall_score=85), account_id="test")
        assert "85" in html

    def test_contains_findings(self):
        html = generate_html_report(_make_report(), account_id="test")
        assert "RDS Multi-AZ" in html
        assert "Enable Multi-AZ" in html

    def test_contains_checklist_table(self):
        html = generate_html_report(_make_report(), account_id="test")
        assert "Checklist Summary" in html
        assert "✅" in html
        assert "❌" in html

    def test_contains_top_recommendations(self):
        html = generate_html_report(_make_report(), account_id="test")
        assert "Top Recommendations" in html
        assert "Enable Multi-AZ for RDS" in html

    def test_contains_module_scores(self):
        html = generate_html_report(_make_report(), account_id="test")
        assert "Security" in html or "security" in html
        assert "Resilience" in html or "resilience" in html

    def test_error_on_bad_input(self):
        html = generate_html_report("not valid json", account_id="test")
        assert "Error" in html

    def test_pass_only_report(self):
        report = _make_report(checks=[
            {"check_id": "SEC-01", "module": "security", "title": "Security Hub", "status": "PASS",
             "wa_reference": "SEC 4", "finding": "Compliant", "recommendation": "None", "priority": "LOW", "affected_resources": []},
        ], top_recommendations=[])
        html = generate_html_report(report, account_id="test")
        assert "<!DOCTYPE html>" in html
