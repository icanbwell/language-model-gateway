import os
from typing import Optional, Any

import boto3
from boto3 import Session

try:
    from types_boto3_bedrock_runtime.client import BedrockRuntimeClient
    from types_boto3_s3.client import S3Client  
    from types_boto3_textract.client import TextractClient
    BOTO3_TYPES_AVAILABLE = True
except ImportError:
    # Fallback types when boto3 stubs are not available
    BedrockRuntimeClient = Any
    S3Client = Any  
    TextractClient = Any
    BOTO3_TYPES_AVAILABLE = False


class AwsClientFactory:
    # noinspection PyMethodMayBeStatic
    def create_bedrock_client(self) -> BedrockRuntimeClient:
        """Create and return a Bedrock client"""
        try:
            session: Session = boto3.Session(
                profile_name=os.environ.get("AWS_CREDENTIALS_PROFILE")
            )
            bedrock_client: BedrockRuntimeClient = session.client(
                service_name="bedrock-runtime",
                region_name="us-east-1",
            )
            return bedrock_client
        except Exception as e:
            raise RuntimeError(f"Failed to create Bedrock client: {e}. Make sure AWS credentials are configured.")

    # noinspection PyMethodMayBeStatic
    def create_s3_client(self) -> S3Client:
        try:
            session: Session = boto3.Session(
                profile_name=os.environ.get("AWS_CREDENTIALS_PROFILE")
            )
            s3_client: S3Client = session.client(
                service_name="s3",
                region_name="us-east-1",
            )
            return s3_client
        except Exception as e:
            raise RuntimeError(f"Failed to create S3 client: {e}. Make sure AWS credentials are configured.")

    # noinspection PyMethodMayBeStatic
    def create_textract_client(self) -> TextractClient:
        try:
            session: Session = boto3.Session(
                profile_name=os.environ.get("AWS_CREDENTIALS_PROFILE")
            )
            textract_client: TextractClient = session.client(
                service_name="textract",
                region_name="us-east-1",
            )
            return textract_client
        except Exception as e:
            raise RuntimeError(f"Failed to create Textract client: {e}. Make sure AWS credentials are configured.")
