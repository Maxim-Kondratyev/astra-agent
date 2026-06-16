"""CLI entrypoint: python -m astra"""

import argparse

from astra.assessment import run_assessment
from astra.report.generator import generate_html_report

VALID_MODULES = ("security", "resilience", "saas", "all")


def main():
    parser = argparse.ArgumentParser(
        prog="astra",
        description="ASTRA — Autonomous Security, Tenancy & Resilience Assessor",
    )
    parser.add_argument("--model", default="us.anthropic.claude-sonnet-4-20250514", help="Bedrock model ID")
    parser.add_argument("--region", default="us-east-1", help="AWS region for Bedrock")
    parser.add_argument("--module", "-m", choices=VALID_MODULES, action="append", help="Module(s) to assess (can specify multiple: -m security -m resilience)")
    parser.add_argument("--output", "-o", help="Save raw JSON report to file")
    parser.add_argument("--html", help="Save HTML report to file")
    parser.add_argument("--account-id", default=None, help="AWS account ID (auto-detected if omitted)")
    parser.add_argument("--context-dir", "-c", help="Path to folder with customer architecture docs (.md, .txt, .yaml) for context-aware recommendations")
    args = parser.parse_args()

    # Determine modules
    if not args.module or "all" in args.module:
        modules = ["security", "resilience", "saas"]
    else:
        modules = list(dict.fromkeys(args.module))  # dedupe preserving order

    print("=" * 60)
    print("  ASTRA — Autonomous Security, Tenancy & Resilience Assessor")
    print("=" * 60)
    print(f"  Modules : {', '.join(modules)}")
    print(f"  Model   : {args.model}")
    if args.context_dir:
        print(f"  Context : {args.context_dir}")
    print("=" * 60 + "\n")

    result = run_assessment(
        modules=modules,
        model_id=args.model,
        region=args.region,
        account_id=args.account_id,
        context_dir=args.context_dir,
    )

    report_json = result["report"]

    if args.output:
        with open(args.output, "w") as f:
            f.write(report_json)
        print(f"\n✅ JSON report saved to {args.output}")

    if args.html:
        html = generate_html_report(report_json, account_id=result["account_id"])
        with open(args.html, "w") as f:
            f.write(html)
        print(f"✅ HTML report saved to {args.html}")

    if not args.output and not args.html:
        print("\n" + report_json)

    print(f"\n🏁 Assessment complete — {len(result['raw_results'])} checks run across {len(modules)} module(s).")
    if result["context_provided"]:
        print("📄 Customer context was used to tailor recommendations.")


if __name__ == "__main__":
    main()
