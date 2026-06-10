#!/usr/bin/env python3
"""ASTRA CDK app entrypoint."""

import aws_cdk as cdk

from stacks.astra_stack import AstraStack

app = cdk.App()
AstraStack(app, "AstraStack", env=cdk.Environment(region="eu-west-1"))
app.synth()
