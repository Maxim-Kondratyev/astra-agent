"""CLI entrypoint: python -m astra"""

import argparse

from astra.agent import create_agent
from astra.report.generator import generate_html_report


def main():
    parser = argparse.ArgumentParser(prog="astra", description="ASTRA — AWS Security Assessment Agent")
    parser.add_argument("--model", default="us.anthropic.claude-sonnet-4-6", help="Bedrock model/inference profile ID")
    parser.add_argument("--region", default="us-east-1", help="AWS region for Bedrock")
    parser.add_argument("--output", "-o", help="Output file path (raw text)")
    parser.add_argument("--html", help="Output HTML report file path")
    parser.add_argument("--account-id", default="Unknown", help="AWS account ID for report header")
    parser.add_argument("--prompt", default="Assess the security posture of this AWS account. Call all available tools and produce a complete assessment.", help="Assessment prompt")
    args = parser.parse_args()

    print("🔍 ASTRA — Starting security assessment...\n")
    agent = create_agent(model_id=args.model, region=args.region)
    result = agent(args.prompt)
    output = str(result)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"\n✅ Assessment saved to {args.output}")

    if args.html:
        html = generate_html_report(output, account_id=args.account_id)
        with open(args.html, "w") as f:
            f.write(html)
        print(f"✅ HTML report saved to {args.html}")

    if not args.output and not args.html:
        print("\n" + output)


if __name__ == "__main__":
    main()
