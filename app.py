import os

import aws_cdk
from dotenv import load_dotenv

from deployment.lambda_fastapi_example_stack import LambdaFastapiExampleStack

load_dotenv()

app = aws_cdk.App()

env = aws_cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION"),
)

LambdaFastapiExampleStack(
    app,
    "LambdaFastapiExampleStack",
    env=env,
)

app.synth()
