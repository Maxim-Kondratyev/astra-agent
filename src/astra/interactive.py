"""Interactive guided flow — user-friendly onboarding for non-technical users."""

import os
import sys
from pathlib import Path

import boto3


def _print_header():
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  ASTRA — Autonomous Security, Tenancy & Resilience Assessor ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()
    print("  I assess your AWS environment against Well-Architected best")
    print("  practices and produce a report with scores and recommendations.")
    print("  All access is READ-ONLY — I never modify your resources.")
    print()


def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        answer = input(f"{prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n\n👋 Cancelled.")
        sys.exit(0)
    return answer or default


def _choose_modules() -> list[str]:
    print("━" * 60)
    print("📋 What would you like to assess?")
    print("━" * 60)
    print()
    print("  1. 🔍 Full assessment (Security + Resilience + SaaS)")
    print("  2. 🛡️  Security only")
    print("  3. 🏗️  Resilience only")
    print("  4. 🏢 SaaS / Tenancy only")
    print()
    choice = _ask("Choose [1-4]", "1")
    module_map = {
        "1": ["security", "resilience", "saas"],
        "2": ["security"],
        "3": ["resilience"],
        "4": ["saas"],
    }
    return module_map.get(choice, ["security", "resilience", "saas"])


def _show_credential_help():
    """Show step-by-step credential setup guide when no credentials are found."""
    print()
    print("  ┌────────────────────────────────────────────────────────┐")
    print("  │  📖 How to set up AWS credentials for ASTRA            │")
    print("  └────────────────────────────────────────────────────────┘")
    print()
    print("  ASTRA needs READ-ONLY access. Choose one method:")
    print()
    print("  ── Option 1: AWS SSO (recommended if your org uses SSO) ──")
    print()
    print("     aws configure sso")
    print("     # Follow the prompts (SSO URL, region, role)")
    print("     aws sso login --profile your-profile")
    print("     export AWS_PROFILE=your-profile")
    print()
    print("  ── Option 2: IAM User with access keys ──")
    print()
    print("     1. Go to AWS Console → IAM → Users → Your user")
    print("     2. Security credentials → Create access key")
    print("     3. Run:")
    print()
    print("        aws configure")
    print("        # Enter: Access Key ID, Secret Access Key, region (e.g. us-east-1)")
    print()
    print("  ── Option 3: Temporary credentials (from your admin) ──")
    print()
    print("     export AWS_ACCESS_KEY_ID=AKIA...")
    print("     export AWS_SECRET_ACCESS_KEY=...")
    print("     export AWS_SESSION_TOKEN=...  (if using temp creds)")
    print("     export AWS_DEFAULT_REGION=us-east-1")
    print()
    print("  ── Required IAM permissions ──")
    print()
    print("     Attach these AWS managed policies to your user/role:")
    print("     • arn:aws:iam::aws:policy/SecurityAudit")
    print("     • arn:aws:iam::aws:policy/ReadOnlyAccess")
    print()
    print("     Or create a role with these policies and use option (b)")
    print("     in the menu below to assume it.")
    print()
    print("  ─────────────────────────────────────────────────────────")
    print()
    _ask("  Press Enter when ready")


def _configure_aws() -> dict:
    """Configure AWS access. Returns dict with account_id and region."""
    print()
    print("━" * 60)
    print("🔐 AWS Access")
    print("━" * 60)
    print()
    print("  ASTRA needs read-only access to your AWS account.")
    print("  Required policies: SecurityAudit + ReadOnlyAccess")
    print()

    # First, check if credentials already exist
    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        account_id = identity["Account"]
        region = boto3.session.Session().region_name or "us-east-1"
        print(f"  ✅ Credentials detected — account {account_id} (region: {region})")
        print()
        use_existing = _ask("  Use these credentials? [Y/n]", "Y")
        if use_existing.lower() not in ("n", "no"):
            return {"account_id": account_id, "region": region}
    except Exception:
        print("  ⚠️  No AWS credentials found.")
        print()
        help_choice = _ask("  Would you like setup instructions? [Y/n]", "Y")
        if help_choice.lower() not in ("n", "no"):
            _show_credential_help()

    # Offer options
    print("  a) Use my current AWS credentials")
    print("     (from ~/.aws/credentials, env vars, or instance profile)")
    print()
    print("  b) Assume a cross-account role")
    print("     (you provide a role ARN — standard for external assessments)")
    print()
    choice = _ask("  Choose [a/b]", "a")

    config = {}

    if choice.lower() == "b":
        print()
        print("  ── Cross-account role assumption ──")
        print("  Your admin should create a role with:")
        print("    • SecurityAudit + ReadOnlyAccess policies")
        print("    • Trust policy allowing your account to assume it")
        print()
        role_arn = _ask("  Role ARN (arn:aws:iam::ACCOUNT:role/NAME)")
        external_id = _ask("  External ID (optional, press Enter to skip)")
        config["role_arn"] = role_arn
        if external_id:
            config["external_id"] = external_id

        print()
        print("  Assuming role...")
        try:
            sts = boto3.client("sts")
            params = {"RoleArn": role_arn, "RoleSessionName": "astra-assessment"}
            if external_id:
                params["ExternalId"] = external_id
            creds = sts.assume_role(**params)["Credentials"]
            os.environ["AWS_ACCESS_KEY_ID"] = creds["AccessKeyId"]
            os.environ["AWS_SECRET_ACCESS_KEY"] = creds["SecretAccessKey"]
            os.environ["AWS_SESSION_TOKEN"] = creds["SessionToken"]
            print("  ✅ Role assumed successfully")
        except Exception as e:
            print(f"  ❌ Failed to assume role: {e}")
            print()
            print("  Common fixes:")
            print("  • Check the role ARN is correct")
            print("  • Ensure the role's trust policy allows your account")
            print("  • If using External ID, confirm it matches")
            sys.exit(1)

    # Verify access
    print()
    try:
        sts = boto3.client("sts")
        identity = sts.get_caller_identity()
        account_id = identity["Account"]
        region = boto3.session.Session().region_name or "us-east-1"
        print(f"  ✅ Connected to account {account_id} (region: {region})")
        config["account_id"] = account_id
        config["region"] = region
    except Exception as e:
        print(f"  ❌ Cannot connect to AWS: {e}")
        print()
        print("  Troubleshooting:")
        print("  • Run: aws sts get-caller-identity")
        print("  • If that fails, your credentials are not configured")
        print("  • Run: aws configure")
        sys.exit(1)

    return config


def _configure_context() -> str | None:
    """Ask for optional customer documentation."""
    print()
    print("━" * 60)
    print("📄 Architecture Context (optional)")
    print("━" * 60)
    print()
    print("  Upload your architecture docs for tailored recommendations:")
    print("  • Architecture diagrams or design documents (.md, .txt)")
    print("  • RTO/RPO requirements, SLA definitions")
    print("  • Security policies, network topology (.yaml)")
    print()
    path = _ask("Path to docs folder (Enter to skip)")
    if path and Path(path).exists():
        files = list(Path(path).glob("*.*"))
        relevant = [f for f in files if f.suffix in (".md", ".txt", ".yaml", ".yml", ".json")]
        if relevant:
            print(f"  ✅ Found {len(relevant)} document(s): {', '.join(f.name for f in relevant[:5])}")
            return path
        print("  ⚠️  No supported files found (.md, .txt, .yaml, .yml, .json)")
    elif path:
        print(f"  ⚠️  Path not found: {path}")
    return None


def _confirm_and_run(modules: list[str], aws_config: dict, context_dir: str | None) -> dict:
    """Show summary and confirm before running."""
    print()
    print("━" * 60)
    print("✅ Ready to assess")
    print("━" * 60)
    print()
    print(f"  Account  : {aws_config['account_id']}")
    print(f"  Region   : {aws_config['region']}")
    module_names = {"security": "🛡️ Security", "resilience": "🏗️ Resilience", "saas": "🏢 SaaS"}
    print(f"  Modules  : {', '.join(module_names.get(m, m) for m in modules)}")
    checks_count = sum(12 if m in ("security", "resilience") else 10 for m in modules)
    print(f"  Checks   : {checks_count} checks will run")
    if context_dir:
        print(f"  Context  : {context_dir}")
    print("  Output   : HTML report + interactive chat")
    print()
    confirm = _ask("Start assessment? [Y/n]", "Y")
    if confirm.lower() in ("n", "no"):
        print("\n👋 Cancelled.")
        sys.exit(0)

    return {"modules": modules, "context_dir": context_dir, "account_id": aws_config["account_id"]}


def run_interactive():
    """Run the full interactive guided flow."""
    _print_header()
    modules = _choose_modules()
    aws_config = _configure_aws()
    context_dir = _configure_context()
    config = _confirm_and_run(modules, aws_config, context_dir)

    # Run assessment
    print()
    from astra.assessment import run_assessment
    result = run_assessment(
        modules=config["modules"],
        account_id=config["account_id"],
        context_dir=config["context_dir"],
    )

    # Save report
    report_file = f"astra-report-{config['account_id']}.html"
    from astra.report.generator import generate_html_report
    html = generate_html_report(result["report"], account_id=config["account_id"], mermaid_diagram=result.get("mermaid_diagram"))
    with open(report_file, "w") as f:
        f.write(html)
    print(f"\n✅ Report saved → {report_file}")

    # Offer chat
    print()
    chat_choice = _ask("💬 Would you like to discuss the findings? [Y/n]", "Y")
    if chat_choice.lower() not in ("n", "no"):
        from astra.chat import start_chat
        start_chat(report=result["report"])
