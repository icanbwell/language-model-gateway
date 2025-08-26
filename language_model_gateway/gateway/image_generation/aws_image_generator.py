import asyncio
import base64
import json
import logging
import os
from concurrent.futures.thread import ThreadPoolExecutor
from typing import override, Dict, Any, Literal

from types_boto3_bedrock_runtime.client import BedrockRuntimeClient
from types_boto3_bedrock_runtime.type_defs import InvokeModelResponseTypeDef

from language_model_gateway.gateway.aws.aws_client_factory import AwsClientFactory
from language_model_gateway.gateway.image_generation.image_generator import (
    ImageGenerator,
)

logger = logging.getLogger(__name__)

MODEL_ID = "amazon.titan-image-generator-v2:0"


class AwsImageGenerator(ImageGenerator):
    def __init__(self, *, aws_client_factory: AwsClientFactory) -> None:
        self.executor: ThreadPoolExecutor = ThreadPoolExecutor()
        self.aws_client_factory: AwsClientFactory = aws_client_factory
        assert self.aws_client_factory is not None
        assert isinstance(self.aws_client_factory, AwsClientFactory)

    def _invoke_model(self, request_body: Dict[str, Any]) -> InvokeModelResponseTypeDef:
        """Synchronous model invocation"""
        client: BedrockRuntimeClient = self.aws_client_factory.create_bedrock_client()

        if logger.isEnabledFor(logging.DEBUG):
            # Log a safe summary of the request body (avoid full prompt/content)
            debug_summary = {
                "taskType": request_body.get("taskType"),
                "imageGenerationConfig": request_body.get("imageGenerationConfig"),
                "textLength": len(
                    (request_body.get("textToImageParams") or {}).get("text", "")
                ),
            }
            logger.debug(
                "Invoking Bedrock model",
                extra={"model_id": MODEL_ID, "request_summary": debug_summary},
            )

        response: InvokeModelResponseTypeDef = client.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body),
        )
        return response

    @override
    async def generate_image_async(
        self,
        *,
        prompt: str,
        style: Literal["natural", "cinematic", "digital-art", "pop-art"] = "natural",
        image_size: Literal[
            "256x256", "512x512", "1024x1024", "1792x1024", "1024x1792"
        ] = "1024x1024",
    ) -> bytes:
        """Generate an image using Titan Image Generator"""
        if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
            logger.info(f"Generating image for prompt: {prompt}")

        request_body = {
            "textToImageParams": {"text": prompt},
            "taskType": "TEXT_IMAGE",
            "imageGenerationConfig": {
                "cfgScale": 8,
                "seed": 0,
                "width": 1024,
                "height": 1024,
                "numberOfImages": 1,
                "quality": "standard",
            },
        }

        try:
            # Get the current event loop
            loop = asyncio.get_running_loop()

            # Run model invocation in executor
            response: InvokeModelResponseTypeDef = await loop.run_in_executor(
                self.executor, self._invoke_model, request_body
            )

            # Parse the response
            response_body = json.loads(response["body"].read())

            # Get the base64 encoded image
            base64_image = response_body["images"][0]

            # Convert base64 to bytes
            image_data = base64.b64decode(base64_image)

            if os.environ.get("LOG_INPUT_AND_OUTPUT", "0") == "1":
                logger.info(f"Image generated successfully for prompt: {prompt}")
            return image_data

        except Exception as e:
            logger.error(f"Error generating image for prompt {prompt}: {str(e)}")
            logger.exception(e, stack_info=True)
            raise
