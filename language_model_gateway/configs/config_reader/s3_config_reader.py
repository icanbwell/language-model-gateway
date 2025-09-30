import logging
import boto3
import json
from typing import List
from botocore.exceptions import ClientError
from language_model_gateway.configs.config_schema import ChatModelConfig
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from language_model_gateway.gateway.utilities.url_parser import UrlParser

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["CONFIG"])


class S3ConfigReader:
    # noinspection PyMethodMayBeStatic
    async def read_model_configs(self, *, s3_url: str) -> List[ChatModelConfig]:
        """
        Read model configurations from JSON files stored in an S3 bucket
        """

        # Parse S3 URL
        bucket_name: str
        prefix: str
        bucket_name, prefix = UrlParser.parse_s3_uri(s3_url)
        if not bucket_name:
            raise ValueError("bucket_name must not be empty or None")
        if not prefix:
            raise ValueError("prefix must not be empty or None")

        logger.info(f"Reading model configurations from S3: {bucket_name}/{prefix}")

        configs: List[ChatModelConfig] = []

        # Initialize S3 client
        s3_client = boto3.client("s3")

        try:
            # List all objects in the specified prefix
            paginator = s3_client.get_paginator("list_objects_v2")
            page_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix)

            # Iterate through all objects with .json extension
            for page in page_iterator:
                if "Contents" in page:
                    for obj in page["Contents"]:
                        if obj["Key"].endswith(".json"):
                            try:
                                # Get the JSON file content
                                response = s3_client.get_object(
                                    Bucket=bucket_name, Key=obj["Key"]
                                )

                                # Parse JSON content
                                data = json.loads(
                                    response["Body"].read().decode("utf-8")
                                )
                                configs.append(ChatModelConfig(**data))

                            except ClientError as e:
                                logger.error(
                                    f"Error reading file {obj['Key']}: {str(e)}"
                                )
                            except json.JSONDecodeError as e:
                                logger.error(
                                    f"Error parsing JSON from {obj['Key']}: {str(e)}"
                                )

            # sort the configs by name
            configs.sort(key=lambda x: x.name)
            return configs

        except Exception as e:
            logger.error(f"Error reading configs from S3: {str(e)}")
            raise
