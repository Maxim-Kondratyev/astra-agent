"""ASTRA infrastructure stack — deployable to any customer AWS account."""

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
)
from constructs import Construct


class AstraStack(cdk.Stack):
    """Deploys ASTRA with read-only IAM role, S3 bucket for reports, and Lambda for execution."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- S3 Bucket for reports ---
        reports_bucket = s3.Bucket(
            self, "ReportsBucket",
            bucket_name=f"astra-reports-{cdk.Aws.ACCOUNT_ID}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            enforce_ssl=True,
        )

        # --- IAM Role for ASTRA (READ-ONLY) ---
        astra_role = iam.Role(
            self, "AstraRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="ASTRA assessment agent — READ-ONLY access to AWS resources",
        )

        # Read-only access to assess the account
        astra_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("SecurityAudit"))
        astra_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("ReadOnlyAccess"))

        # Bedrock invoke access (model only, no write)
        astra_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            resources=["arn:aws:bedrock:*::foundation-model/*", f"arn:aws:bedrock:*:{cdk.Aws.ACCOUNT_ID}:inference-profile/*"],
        ))

        # Write reports to S3
        reports_bucket.grant_put(astra_role)

        # CloudWatch Logs for Lambda
        astra_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"))

        # --- Explicit DENY on any mutating actions ---
        astra_role.add_to_policy(iam.PolicyStatement(
            sid="DenyAllMutatingActions",
            effect=iam.Effect.DENY,
            actions=[
                "ec2:Terminate*", "ec2:Delete*", "ec2:Modify*", "ec2:Create*",
                "s3:Delete*", "s3:PutBucketPolicy",
                "iam:Create*", "iam:Delete*", "iam:Update*", "iam:Attach*", "iam:Detach*", "iam:Put*",
                "rds:Delete*", "rds:Modify*",
                "lambda:Delete*", "lambda:Update*", "lambda:Create*",
            ],
            resources=["*"],
        ))

        # --- Lambda Function ---
        astra_lambda = lambda_.Function(
            self, "AstraFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambda"),
            role=astra_role,
            timeout=Duration.minutes(15),
            memory_size=512,
            environment={
                "REPORTS_BUCKET": reports_bucket.bucket_name,
                "BEDROCK_MODEL_ID": "us.anthropic.claude-sonnet-4-6",
                "BEDROCK_REGION": "us-east-1",
            },
            description="ASTRA — Autonomous Security Assessment Agent",
        )

        # --- Outputs ---
        cdk.CfnOutput(self, "ReportsBucketName", value=reports_bucket.bucket_name, description="S3 bucket for assessment reports")
        cdk.CfnOutput(self, "AstraFunctionArn", value=astra_lambda.function_arn, description="Lambda function ARN — invoke to trigger assessment")
        cdk.CfnOutput(self, "AstraRoleArn", value=astra_role.role_arn, description="IAM role ARN (read-only + explicit deny on mutations)")
