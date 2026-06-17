"""Model resolution — try the best available Bedrock model, fall back gracefully."""

import boto3

# Ordered from most capable to least capable
MODEL_PREFERENCE = [
    "anthropic.claude-fable-5",
    "anthropic.claude-opus-4-8",
    "anthropic.claude-opus-4-7",
    "anthropic.claude-opus-4-6-v1",
    "anthropic.claude-sonnet-4-6",
    "anthropic.claude-sonnet-4-5-20250929-v1:0",
    "anthropic.claude-sonnet-4-20250514-v1:0",
    "anthropic.claude-haiku-4-5-20251001-v1:0",
    "anthropic.claude-3-5-haiku-20241022-v1:0",
]

MODEL_NAMES = {
    "anthropic.claude-fable-5": "Claude Fable 5 (latest)",
    "anthropic.claude-opus-4-8": "Claude Opus 4.8",
    "anthropic.claude-opus-4-7": "Claude Opus 4.7",
    "anthropic.claude-opus-4-6-v1": "Claude Opus 4.6",
    "anthropic.claude-sonnet-4-6": "Claude Sonnet 4.6",
    "anthropic.claude-sonnet-4-5-20250929-v1:0": "Claude Sonnet 4.5",
    "anthropic.claude-sonnet-4-20250514-v1:0": "Claude Sonnet 4",
    "anthropic.claude-haiku-4-5-20251001-v1:0": "Claude Haiku 4.5",
    "anthropic.claude-3-5-haiku-20241022-v1:0": "Claude 3.5 Haiku",
}


def _model_name(model_id: str) -> str:
    return MODEL_NAMES.get(model_id, model_id)


def _test_model(bedrock, model_id: str) -> bool:
    """Test if a model is accessible with a minimal call."""
    try:
        bedrock.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": "hi"}]}],
            inferenceConfig={"maxTokens": 1},
        )
        return True
    except Exception:
        return False


def resolve_model(region: str = "us-east-1", preferred: str | None = None) -> tuple[str, str]:
    """Find the best available Bedrock model. Never fails — always returns something.

    Args:
        region: AWS region for Bedrock.
        preferred: Optional preferred model to try first.

    Returns:
        Tuple of (model_id, message describing what was selected and why).
    """
    candidates = list(MODEL_PREFERENCE)
    if preferred:
        if preferred in candidates:
            candidates.remove(preferred)
        candidates.insert(0, preferred)

    bedrock = boto3.client("bedrock-runtime", region_name=region)
    best_name = _model_name(candidates[0])

    for i, model_id in enumerate(candidates):
        if _test_model(bedrock, model_id):
            name = _model_name(model_id)
            if i == 0:
                return model_id, f"Using {name} ✓"
            # Fallback — recommend the best
            return model_id, (
                f"Using {name} (available)\n"
                f"         💡 For best results, enable {best_name} in Bedrock Model Access"
            )

    # Nothing worked at all
    return candidates[0], (
        f"⚠️  No models accessible — report generation may fail.\n"
        f"         Enable model access: AWS Console → Bedrock → Model access → {region}"
    )
