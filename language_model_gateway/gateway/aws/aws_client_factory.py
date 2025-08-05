import os

import boto3
from boto3 import Session

from types_boto3_bedrock_runtime.client import BedrockRuntimeClient
from types_boto3_s3.client import S3Client
from types_boto3_textract.client import TextractClient


class AwsClientFactory:
    # noinspection PyMethodMayBeStatic
    def create_bedrock_client(self) -> BedrockRuntimeClient:
        """Create and return a Bedrock client"""
        session: Session = boto3.Session(
            profile_name=os.environ.get("AWS_CREDENTIALS_PROFILE")
        )
        bedrock_client: BedrockRuntimeClient = session.client(
            service_name="bedrock-runtime",
            region_name="us-east-1",
        )
        return bedrock_client

    # noinspection PyMethodMayBeStatic
    def create_s3_client(self) -> S3Client:
        session: Session = boto3.Session(
            profile_name=os.environ.get("AWS_CREDENTIALS_PROFILE")
        )
        s3_client: S3Client = session.client(
            service_name="s3",
            region_name="us-east-1",
        )
        return s3_client

    # noinspection PyMethodMayBeStatic
    def create_textract_client(self) -> TextractClient:
        session: Session = boto3.Session(
            profile_name=os.environ.get("AWS_CREDENTIALS_PROFILE")
        )
        textract_client: TextractClient = session.client(
            service_name="textract",
            region_name="us-east-1",
        )
        return textract_client
