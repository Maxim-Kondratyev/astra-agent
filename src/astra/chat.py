"""Interactive chat — discuss findings with the ASTRA agent after assessment."""

from strands import Agent
from strands.models.bedrock import BedrockModel

_CHAT_SYSTEM_PROMPT = """\
You are ASTRA — an AWS assessment expert. The customer has just received their assessment report and wants to discuss the findings.

## Assessment Results

{report_context}

## Your Role

- Answer questions about specific findings (why they matter, blast radius, urgency)
- Explain remediation steps in detail (CLI commands, console steps, IaC snippets)
- Help prioritise fixes based on risk and effort
- Provide cost estimates for remediation where possible
- Generate action items, Jira tickets, or runbooks on request
- Compare findings against the customer's architecture context if provided

## Rules

- Be concise but thorough when explaining technical fixes
- Always reference the specific check ID (e.g., REL-01, SEC-05) when discussing findings
- If asked about something outside the assessment scope, say so clearly
- Provide AWS CLI commands or CDK/CloudFormation snippets when giving remediation guidance
- Never suggest actions that would require write access — ASTRA is read-only
"""


def start_chat(report: str, model_id: str = "us.anthropic.claude-sonnet-4-20250514", region: str = "us-east-1"):
    """Start an interactive chat session about assessment findings.

    Args:
        report: The JSON assessment report (provides context for the conversation).
        model_id: Bedrock model ID.
        region: AWS region for Bedrock.
    """
    model = BedrockModel(model_id=model_id, region_name=region)
    system_prompt = _CHAT_SYSTEM_PROMPT.format(report_context=report[:15000])
    agent = Agent(model=model, tools=[], system_prompt=system_prompt)

    print("\n" + "=" * 60)
    print("  💬 ASTRA Chat — Ask about your assessment findings")
    print("=" * 60)
    print("  Examples:")
    print('    "Why did REL-01 fail?"')
    print('    "How do I fix the security groups issue?"')
    print('    "What should I prioritize first?"')
    print('    "Give me a remediation plan for the top 3 findings"')
    print('    "Generate a CloudFormation snippet to enable Multi-AZ"')
    print("  Type 'exit' or 'quit' to end the session.")
    print("=" * 60 + "\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Session ended.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q", "bye"):
            print("\n👋 Session ended. Good luck with the remediation!")
            break

        response = agent(user_input)
        print(f"\nASTRA: {response}\n")
