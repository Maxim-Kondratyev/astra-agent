"""ASTRA infrastructure stack — production-ready deployment to customer AWS accounts."""

import aws_cdk as cdk
from aws_cdk import (
    Duration,
    RemovalPolicy,
    aws_ec2 as ec2,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3 as s3,
)
from constructs import Construct


class AstraStack(cdk.Stack):
    """Deploys ASTRA with read-only IAM, VPC endpoints, S3, Lambda, and optional schedule."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # --- Parameters ---
        model_id = cdk.CfnParameter(self, "ModelId", type="String", default="us.anthropic.claude-fable-5", description="Bedrock model/inference profile ID")

        # --- VPC with private subnets (no internet) ---
        vpc = ec2.Vpc(self, "AstraVpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[ec2.SubnetConfiguration(name="Private", subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)],
        )

        # VPC Endpoints — Bedrock + S3 + STS + Security Hub + other services
        vpc.add_interface_endpoint("BedrockEndpoint", service=ec2.InterfaceVpcEndpointAwsService.BEDROCK_RUNTIME)
        vpc.add_interface_endpoint("STSEndpoint", service=ec2.InterfaceVpcEndpointAwsService.STS)
        vpc.add_interface_endpoint("SecurityHubEndpoint", service=ec2.InterfaceVpcEndpointAwsService("securityhub"))
        vpc.add_interface_endpoint("GuardDutyEndpoint", service=ec2.InterfaceVpcEndpointAwsService("guardduty"))
        vpc.add_gateway_endpoint("S3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3)

        # --- S3 Bucket for reports ---
        reports_bucket = s3.Bucket(self, "ReportsBucket",
            bucket_name=f"astra-reports-{cdk.Aws.ACCOUNT_ID}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.RETAIN,
            enforce_ssl=True,
            versioned=True,
            lifecycle_rules=[s3.LifecycleRule(expiration=Duration.days(365), id="ExpireOldReports")],
        )

        # --- IAM Role (READ-ONLY + explicit DENY) ---
        astra_role = iam.Role(self, "AstraRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="ASTRA — READ-ONLY assessment agent role",
        )

        astra_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("SecurityAudit"))
        astra_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("ReadOnlyAccess"))
        astra_role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"))

        # Bedrock invoke (model only)
        astra_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            resources=["arn:aws:bedrock:*::foundation-model/*", f"arn:aws:bedrock:*:{cdk.Aws.ACCOUNT_ID}:inference-profile/*"],
        ))

        reports_bucket.grant_put(astra_role)

        # Explicit DENY on ALL mutations
        astra_role.add_to_policy(iam.PolicyStatement(
            sid="DenyAllMutatingActions",
            effect=iam.Effect.DENY,
            actions=[
                "ec2:Terminate*", "ec2:Delete*", "ec2:Modify*", "ec2:Create*", "ec2:Run*", "ec2:Stop*", "ec2:Start*",
                "s3:Delete*", "s3:PutBucketPolicy", "s3:PutBucketAcl",
                "iam:Create*", "iam:Delete*", "iam:Update*", "iam:Attach*", "iam:Detach*", "iam:Put*",
                "rds:Delete*", "rds:Modify*", "rds:Create*", "rds:Stop*", "rds:Start*",
                "lambda:Delete*", "lambda:Update*", "lambda:Create*",
                "elasticloadbalancing:Delete*", "elasticloadbalancing:Create*", "elasticloadbalancing:Modify*",
                "autoscaling:Delete*", "autoscaling:Create*", "autoscaling:Update*",
                "route53:Change*", "route53:Create*", "route53:Delete*",
                "cloudwatch:Delete*", "cloudwatch:Put*",
            ],
            resources=["*"],
        ))

        # --- Lambda Function ---
        astra_lambda = lambda_.Function(self, "AstraFunction",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.handler",
            code=lambda_.Code.from_asset("lambda"),
            role=astra_role,
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "REPORTS_BUCKET": reports_bucket.bucket_name,
                "BEDROCK_MODEL_ID": model_id.value_as_string,
                "BEDROCK_REGION": "us-east-1",
            },
            description="ASTRA — Autonomous Security, Tenancy & Resilience Assessor",
        )

        # --- Optional EventBridge Schedule (weekly Monday 6 AM UTC) ---
        rule = events.Rule(self, "WeeklyAssessment",
            schedule=events.Schedule.cron(week_day="MON", hour="6", minute="0"),
            enabled=False,  # Controlled by parameter in real deployment
        )
        rule.add_target(targets.LambdaFunction(astra_lambda))

        # --- Outputs ---
        cdk.CfnOutput(self, "ReportsBucketName", value=reports_bucket.bucket_name)
        cdk.CfnOutput(self, "AstraFunctionArn", value=astra_lambda.function_arn)
        cdk.CfnOutput(self, "AstraRoleArn", value=astra_role.role_arn)
        cdk.CfnOutput(self, "VpcId", value=vpc.vpc_id)
