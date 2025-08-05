from typing import override, cast

from botocore.client import BaseClient

from language_model_gateway.gateway.aws.aws_client_factory import AwsClientFactory
from types_boto3_bedrock_runtime.client import BedrockRuntimeClient
from types_boto3_s3.client import S3Client


class MockAwsClientFactory(AwsClientFactory):
    def __init__(self, *, aws_client: BaseClient) -> None:
        self.aws_client = aws_client
        assert self.aws_client is not None

    @override
    def create_bedrock_client(self) -> BedrockRuntimeClient:
        return cast(BedrockRuntimeClient, self.aws_client)

    @override
    def create_s3_client(self) -> S3Client:
        return cast(S3Client, self.aws_client)
