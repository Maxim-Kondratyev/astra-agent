"""CLI entrypoint: python -m astra"""

import argparse
import sys

from astra.assessment import run_assessment
from astra.report.generator import generate_html_report

VALID_MODULES = ("security", "resilience", "saas", "all")


def main():
    # If no arguments provided, launch interactive guided flow
    if len(sys.argv) == 1:
        from astra.interactive import run_interactive
        run_interactive()
        return

    parser = argparse.ArgumentParser(
        prog="astra",
        description="ASTRA — Autonomous Security, Tenancy & Resilience Assessor",
    )
    parser.add_argument("--model", default=None, help="Bedrock model ID (default: auto-detect best available)")
    parser.add_argument("--region", default="us-east-1", help="AWS region for Bedrock")
    parser.add_argument("--module", "-m", choices=VALID_MODULES, action="append", help="Module(s) to assess (repeatable)")
    parser.add_argument("--output", "-o", help="Save JSON report to file")
    parser.add_argument("--html", help="Save HTML report to file")
    parser.add_argument("--account-id", default=None, help="AWS account ID (auto-detected if omitted)")
    parser.add_argument("--context-dir", "-c", help="Customer architecture docs folder")
    parser.add_argument("--checks-only", action="store_true", help="Run checks only — no LLM, no cost (CI/CD)")
    parser.add_argument("--chat", action="store_true", help="Interactive mode — discuss findings after assessment")
    args = parser.parse_args()

    modules = ["security", "resilience", "saas"] if (not args.module or "all" in args.module) else list(dict.fromkeys(args.module))

    print("=" * 60)
    print("  ASTRA — Autonomous Security, Tenancy & Resilience Assessor")
    print("=" * 60)
    print(f"  Modules : {', '.join(modules)}")
    if not args.checks_only:
        print(f"  Model   : {args.model}")
    if args.context_dir:
        print(f"  Context : {args.context_dir}")
    if args.checks_only:
        print("  Mode    : checks-only (no LLM)")
    if args.chat:
        print("  Mode    : assessment → interactive chat")
    print("=" * 60 + "\n")

    # Preflight checks
    from astra.preflight import print_preflight_results, run_preflight
    errors = run_preflight(region=args.region, model_id=args.model or "us.anthropic.claude-fable-5-20250617", checks_only=args.checks_only)
    if not print_preflight_results(errors):
        sys.exit(1)

    # Resolve best available model
    model_id = args.model
    if not args.checks_only:
        if not model_id:
            from astra.models import resolve_model
            model_id, model_msg = resolve_model(region=args.region)
            print(f"  🧠 {model_msg}\n")
    else:
        model_id = model_id or "unused"

    result = run_assessment(
        modules=modules,
        model_id=model_id,
        region=args.region,
        account_id=args.account_id,
        context_dir=args.context_dir,
        checks_only=args.checks_only,
    )

    report = result["report"]

    if args.output:
        with open(args.output, "w") as f:
            f.write(report)
        print(f"\n✅ JSON report → {args.output}")

    if args.html and not args.checks_only:
        html = generate_html_report(report, account_id=result["account_id"], mermaid_diagram=result.get("mermaid_diagram"))
        with open(args.html, "w") as f:
            f.write(html)
        print(f"✅ HTML report → {args.html}")

    if not args.output and not args.html and not args.chat:
        print("\n" + report)

    # Interactive chat mode
    if args.chat and not args.checks_only:
        from astra.chat import start_chat
        start_chat(report=report, model_id=args.model, region=args.region)

    # Exit code for CI/CD
    if args.checks_only:
        failed = sum(1 for r in result["raw_results"] if r.get("status") == "FAIL")
        if failed:
            sys.exit(1)


if __name__ == "__main__":
    main()
