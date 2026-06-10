"""Lambda handler for ASTRA assessment agent."""

import json
import os
from datetime import datetime, timezone

import boto3


def handler(event, context):
    """Trigger an ASTRA security assessment and save the report to S3."""
    # Import here to allow Lambda layer packaging
    from astra.agent import create_agent
    from astra.report.generator import generate_html_report

    model_id = os.environ.get("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")
    region = os.environ.get("BEDROCK_REGION", "us-east-1")
    bucket = os.environ["REPORTS_BUCKET"]

    # Run assessment
    agent = create_agent(model_id=model_id, region=region)
    result = agent("Assess the security posture of this AWS account. Call all available tools and produce a complete assessment.")
    output = str(result)

    # Get account ID
    sts = boto3.client("sts")
    account_id = sts.get_caller_identity()["Account"]

    # Generate reports
    html = generate_html_report(output, account_id=account_id)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")

    # Save to S3
    s3 = boto3.client("s3")
    prefix = f"assessments/{timestamp}"
    s3.put_object(Bucket=bucket, Key=f"{prefix}/report.html", Body=html.encode(), ContentType="text/html")
    s3.put_object(Bucket=bucket, Key=f"{prefix}/raw-output.txt", Body=output.encode(), ContentType="text/plain")

    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Assessment complete",
            "report_key": f"{prefix}/report.html",
            "account_id": account_id,
        }),
    }
