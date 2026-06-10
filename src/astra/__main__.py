"""CLI entrypoint: python -m astra"""

import argparse

from astra.agent import create_agent
from astra.report.generator import generate_html_report

VALID_MODULES = ("security", "resilience", "saas", "all")


def main():
    parser = argparse.ArgumentParser(
        prog="astra",
        description="ASTRA — Autonomous Security, Tenancy & Resilience Assessor",
    )
    parser.add_argument("--model", default="us.anthropic.claude-opus-4-8", help="Bedrock model/inference profile ID (default: Opus 4.8)")
    parser.add_argument("--region", default="us-east-1", help="AWS region for Bedrock")
    parser.add_argument("--module", "-m", choices=VALID_MODULES, default="all", help="Module to assess: security, resilience, saas, or all")
    parser.add_argument("--output", "-o", help="Save raw output to file")
    parser.add_argument("--html", help="Save HTML report to file")
    parser.add_argument("--account-id", default=None, help="AWS account ID (auto-detected if omitted)")
    args = parser.parse_args()

    modules = ["security", "resilience", "saas"] if args.module == "all" else [args.module]
    module_str = ", ".join(modules)

    print(f"🔍 ASTRA — Starting assessment [{module_str}]")
    print(f"   Model: {args.model}")
    print(f"   Region: {args.region}\n")

    agent = create_agent(model_id=args.model, region=args.region, modules=modules)

    prompt = f"Assess this AWS account for the following modules: {module_str}. Call ALL available tools and produce a complete assessment."
    result = agent(prompt)
    output = str(result)

    # Auto-detect account ID
    account_id = args.account_id
    if not account_id:
        try:
            import boto3
            account_id = boto3.client("sts").get_caller_identity()["Account"]
        except Exception:
            account_id = "Unknown"

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"\n✅ Raw output saved to {args.output}")

    if args.html:
        html = generate_html_report(output, account_id=account_id)
        with open(args.html, "w") as f:
            f.write(html)
        print(f"✅ HTML report saved to {args.html}")

    if not args.output and not args.html:
        print("\n" + output)


if __name__ == "__main__":
    main()
