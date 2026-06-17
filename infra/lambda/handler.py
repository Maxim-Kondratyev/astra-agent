"""Lambda handler for ASTRA automated assessments."""

import json
import os
from datetime import datetime, timezone

import boto3


def handler(event, context):
    """Run ASTRA assessment and save report to S3."""
    from astra.assessment import run_assessment
    from astra.report.generator import generate_html_report

    model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-fable-5")
    region = os.environ.get("BEDROCK_REGION", "us-east-1")
    bucket = os.environ["REPORTS_BUCKET"]
    modules = event.get("modules", ["security", "resilience", "saas"])

    # Run assessment
    result = run_assessment(modules=modules, model_id=model_id, region=region)

    # Generate HTML
    html = generate_html_report(result["report"], account_id=result["account_id"])
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")

    # Save to S3
    s3 = boto3.client("s3")
    prefix = f"assessments/{timestamp}"
    s3.put_object(Bucket=bucket, Key=f"{prefix}/report.html", Body=html.encode(), ContentType="text/html")
    s3.put_object(Bucket=bucket, Key=f"{prefix}/report.json", Body=result["report"].encode(), ContentType="application/json")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Assessment complete",
            "report_key": f"{prefix}/report.html",
            "account_id": result["account_id"],
            "modules": modules,
            "checks_run": len(result["raw_results"]),
            "elapsed_seconds": result.get("elapsed_seconds"),
        }),
    }
