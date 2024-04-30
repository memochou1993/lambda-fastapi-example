import os

from aws_cdk import BundlingOptions, Duration, Size, Stack, aws_apigateway, aws_ec2, aws_iam, aws_lambda, aws_logs
from constructs import Construct


class LambdaFastapiExampleStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = self.create_vpc()
        self.lambda_function = self.create_lambda_function()
        self.api_gateway = self.create_api_gateway()

    def create_vpc(self):
        vpc = aws_ec2.Vpc.from_lookup(
            self,
            "SelectedVpc",
            vpc_id=os.environ.get("AWS_VPC_ID"),
        )

        return vpc

    def create_lambda_function(self):
        lambda_role = aws_iam.Role(
            self,
            "LambdaFastapiExampleLambdaRole",
            description="Lambda FastAPI Example Lambda Role",
            assumed_by=aws_iam.CompositePrincipal(
                aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            ),
        )
        lambda_role.add_managed_policy(
            aws_iam.ManagedPolicy.from_managed_policy_arn(
                self,
                "LambdaFastapiExampleAWSLambdaBasicExecutionRolePolicy",
                "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            )
        )
        lambda_role.add_managed_policy(
            aws_iam.ManagedPolicy.from_managed_policy_arn(
                self,
                "LambdaFastapiExampleAWSLambdaVPCAccessExecutionRolePolicy",
                "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",
            )
        )

        layer = aws_lambda.LayerVersion(
            self,
            "LambdaFastapiExampleLambdaLayer",
            description="Lambda FastAPI Example Lambda Layer",
            code=aws_lambda.Code.from_asset(
                "deployment/layer",
                bundling=BundlingOptions(
                    image=aws_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash",
                        "-c",
                        "pip install --no-cache -r requirements.txt -t /asset-output/python && cp -au . /asset-output/python",
                    ],
                ),
            ),
            compatible_architectures=[
                aws_lambda.Architecture.ARM_64,
            ],
            compatible_runtimes=[
                aws_lambda.Runtime.PYTHON_3_12,
            ],
        )

        lambda_function = aws_lambda.Function(
            self,
            "LambdaFastapiExampleLambdaFunction",
            description="Lambda FastAPI Example Lambda Function",
            runtime=aws_lambda.Runtime.PYTHON_3_12,
            code=aws_lambda.Code.from_asset("app"),
            handler="main.handler",
            architecture=aws_lambda.Architecture.ARM_64,
            memory_size=512,
            timeout=Duration.seconds(30),
            vpc=self.vpc,
            vpc_subnets=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_EGRESS, one_per_az=True),
            role=lambda_role,
            layers=[
                layer,
            ],
            environment={},
        )

        return lambda_function

    def create_api_gateway(self):
        log_group = aws_logs.LogGroup(
            self,
            "LambdaFastapiExampleLogGroup",
            retention=aws_logs.RetentionDays.ONE_MONTH,
        )

        api_gateway = aws_apigateway.RestApi(
            self,
            "LambdaFastapiExampleApiGateway",
            description="Lambda FastAPI Example Api Gateway",
            min_compression_size=Size.kibibytes(1),
            endpoint_types=[
                aws_apigateway.EndpointType.REGIONAL,
            ],
            cloud_watch_role=True,
            deploy_options=aws_apigateway.StageOptions(
                stage_name="production",
                metrics_enabled=True,
                access_log_destination=aws_apigateway.LogGroupLogDestination(log_group),
                access_log_format=aws_apigateway.AccessLogFormat.json_with_standard_fields(
                    caller=True,
                    http_method=True,
                    ip=True,
                    protocol=True,
                    request_time=True,
                    resource_path=True,
                    response_length=True,
                    status=True,
                    user=True,
                ),
            ),
        )

        usage_plan = api_gateway.add_usage_plan(
            "LambdaFastapiExampleUsagePlan",
            description="Lambda FastAPI Example Usage Plan",
            throttle=aws_apigateway.ThrottleSettings(
                burst_limit=50,
                rate_limit=100,
            ),
        )

        api_key = aws_apigateway.ApiKey(
            self,
            "LambdaFastapiExampleApiKey",
            description="Lambda FastAPI Example Api Key",
        )

        usage_plan.add_api_key(api_key)

        lambda_integration = aws_apigateway.LambdaIntegration(self.lambda_function)

        api_gateway.root.add_method("GET", lambda_integration)

        proxy_resource = api_gateway.root.add_resource("{proxy+}")
        proxy_resource.add_cors_preflight(
            allow_origins=aws_apigateway.Cors.ALL_ORIGINS,
            allow_methods=aws_apigateway.Cors.ALL_METHODS,
            max_age=Duration.hours(1),
        )
        proxy_method = proxy_resource.add_method("ANY", lambda_integration, api_key_required=True)

        usage_plan.add_api_stage(
            stage=api_gateway.deployment_stage,
            throttle=[
                aws_apigateway.ThrottlingPerMethod(
                    method=proxy_method,
                    throttle=aws_apigateway.ThrottleSettings(
                        burst_limit=50,
                        rate_limit=100,
                    ),
                ),
            ],
        )

        return api_gateway
