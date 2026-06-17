"""Preflight checks — verify ASTRA has everything it needs before running."""

import boto3


class PreflightError:
    def __init__(self, check: str, message: str, fix: str):
        self.check = check
        self.message = message
        self.fix = fix


def run_preflight(region: str = "us-east-1", model_id: str = "anthropic.claude-fable-5", checks_only: bool = False) -> list[PreflightError]:
    """Run preflight checks. Returns empty list if all good, or list of errors.

    Args:
        region: AWS region for Bedrock.
        model_id: Bedrock model to validate access for.
        checks_only: If True, skip Bedrock validation (not needed for checks-only mode).
    """
    errors: list[PreflightError] = []

    # 1. AWS credentials exist and work
    try:
        sts = boto3.client("sts")
        sts.get_caller_identity()
    except Exception as e:
        errors.append(PreflightError(
            "AWS Credentials",
            f"Cannot authenticate to AWS: {e}",
            "Configure credentials:\n"
            "  • aws configure              (IAM user)\n"
            "  • aws sso login              (SSO)\n"
            "  • export AWS_ACCESS_KEY_ID=… (environment variables)",
        ))
        return errors  # Can't continue without creds

    # 2. Read permissions — try a lightweight read call
    try:
        ec2 = boto3.client("ec2", region_name=region)
        ec2.describe_regions(RegionNames=[region])
    except ec2.exceptions.ClientError as e:
        if "UnauthorizedOperation" in str(e) or "AccessDenied" in str(e):
            errors.append(PreflightError(
                "Read Permissions",
                "Your credentials lack read access to EC2.",
                "Attach these managed policies to your IAM user/role:\n"
                "  • arn:aws:iam::aws:policy/SecurityAudit\n"
                "  • arn:aws:iam::aws:policy/ReadOnlyAccess",
            ))
    except Exception:
        pass  # Network issues etc — don't block on this

    # 3. Security Hub access (most common check — tests service-level perms)
    try:
        sh = boto3.client("securityhub", region_name=region)
        sh.describe_hub()
    except sh.exceptions.InvalidAccessException:
        pass  # Security Hub not enabled — that's fine (check will report FAIL)
    except sh.exceptions.ClientError as e:
        if "AccessDenied" in str(e):
            errors.append(PreflightError(
                "Security Service Access",
                "Access denied to Security Hub. Your role may be missing SecurityAudit policy.",
                "Attach: arn:aws:iam::aws:policy/SecurityAudit",
            ))
    except Exception:
        pass

    # 4. Bedrock model access (skip if checks-only)
    if not checks_only:
        try:
            bedrock = boto3.client("bedrock-runtime", region_name=region)
            # Minimal invocation to test access — will fail fast if SCP blocks
            bedrock.invoke_model(
                modelId=model_id,
                body=b'{"anthropic_version":"bedrock-2023-05-31","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}',
            )
        except Exception as e:
            error_str = str(e)
            if "AccessDeniedException" in error_str:
                if "service control policy" in error_str.lower() or "scp" in error_str.lower():
                    errors.append(PreflightError(
                        "Bedrock Access (SCP Blocked)",
                        "Amazon Bedrock is blocked by a Service Control Policy (SCP) in your organization.",
                        "Contact your AWS administrator to allow bedrock:InvokeModel in the SCP.\n"
                        "Alternatively, run with --checks-only to skip AI analysis (free, no Bedrock needed).",
                    ))
                else:
                    errors.append(PreflightError(
                        "Bedrock Model Access",
                        f"Cannot invoke Bedrock model: {model_id}",
                        "Fix options:\n"
                        f"  1. Enable model access: AWS Console → Bedrock → Model access → Enable {model_id.split('.')[-1]}\n"
                        f"  2. Check region: model must be available in {region}\n"
                        "  3. Check IAM: your role needs bedrock:InvokeModel permission\n"
                        "  4. Use --checks-only to skip AI analysis (no Bedrock required)",
                    ))
            elif "ResourceNotFoundException" in error_str or "ValidationException" in error_str:
                errors.append(PreflightError(
                    "Bedrock Model Not Available",
                    f"Model {model_id} is not available in region {region}.",
                    f"Fix options:\n"
                    f"  1. Enable the model: AWS Console → Bedrock → Model access → {region}\n"
                    "  2. Try a different region: --region us-east-1\n"
                    "  3. Use --checks-only to skip AI analysis",
                ))
            # Other errors (throttling, etc.) — don't block, might work on retry

    return errors


def print_preflight_results(errors: list[PreflightError]) -> bool:
    """Print preflight results. Returns True if all checks passed."""
    if not errors:
        print("  ✅ Preflight checks passed\n")
        return True

    print("  ❌ Preflight checks found issues:\n")
    for i, err in enumerate(errors, 1):
        print(f"  ── Problem {i}: {err.check} ──")
        print(f"  {err.message}")
        print()
        print("  How to fix:")
        for line in err.fix.split("\n"):
            print(f"  {line}")
        print()

    print("  ─────────────────────────────────────────────")
    print("  Fix the issue(s) above and try again.")
    if not any("Bedrock" in e.check for e in errors):
        print("  (Or use --checks-only to run without AI analysis)")
    print()
    return False
