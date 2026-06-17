"""Model resolution — try the best available Bedrock model, fall back gracefully."""

import boto3

# Ordered from most capable to least capable
MODEL_PREFERENCE = [
    "us.anthropic.claude-fable-5-20250617",
    "us.anthropic.claude-opus-4-0",
    "us.anthropic.claude-sonnet-4-20250514",
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
    "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
]


def resolve_model(region: str = "us-east-1", preferred: str | None = None) -> tuple[str, str]:
    """Find the best available Bedrock model.

    Args:
        region: AWS region for Bedrock.
        preferred: If set, try this model first.

    Returns:
        Tuple of (model_id, message). Message indicates if fallback was used.
    """
    candidates = list(MODEL_PREFERENCE)
    if preferred:
        # Put preferred at the front
        if preferred in candidates:
            candidates.remove(preferred)
        candidates.insert(0, preferred)

    bedrock = boto3.client("bedrock-runtime", region_name=region)

    for model_id in candidates:
        try:
            bedrock.invoke_model(
                modelId=model_id,
                body=b'{"anthropic_version":"bedrock-2023-05-31","max_tokens":1,"messages":[{"role":"user","content":"hi"}]}',
            )
            if model_id == candidates[0]:
                return model_id, f"Using {_model_name(model_id)} (best available)"
            return model_id, f"Using {_model_name(model_id)} (fallback — preferred model not available)"
        except Exception:
            continue

    # Nothing worked — return the preferred and let it fail at report time with a clear error
    return candidates[0], "⚠️ Could not verify model access — will attempt anyway"


def _model_name(model_id: str) -> str:
    """Human-friendly model name."""
    names = {
        "us.anthropic.claude-fable-5-20250617": "Claude Fable 5",
        "us.anthropic.claude-opus-4-0": "Claude Opus 4",
        "us.anthropic.claude-sonnet-4-20250514": "Claude Sonnet 4",
        "us.anthropic.claude-3-5-sonnet-20241022-v2:0": "Claude 3.5 Sonnet v2",
        "us.anthropic.claude-3-5-sonnet-20240620-v1:0": "Claude 3.5 Sonnet",
    }
    return names.get(model_id, model_id)
