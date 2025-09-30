from typing import Dict, List, Any, Generator

import boto3
import pytest
from botocore.client import BaseClient
from moto import mock_aws
from starlette.responses import Response, StreamingResponse
from boto3 import Session

from language_model_gateway.gateway.aws.aws_client_factory import AwsClientFactory
from language_model_gateway.gateway.file_managers.aws_s3_file_manager import (
    AwsS3FileManager,
)
from language_model_gateway.gateway.utilities.s3_url import S3Url
from tests.gateway.mocks.mock_aws_client_factory import MockAwsClientFactory
from types_boto3_s3.client import S3Client


@pytest.fixture
def mock_s3() -> Generator[S3Client, Any, None]:
    """Create a mock S3 client using moto."""
    with mock_aws():
        session: Session = boto3.Session()
        s3_client: S3Client = session.client(
            service_name="s3",
            region_name="us-east-1",
        )
        yield s3_client


@pytest.fixture
def aws_client_factory(mock_s3: BaseClient) -> AwsClientFactory:
    """Create a mock AWS client factory."""
    return MockAwsClientFactory(aws_client=mock_s3)


@pytest.fixture
def aws_s3_file_manager(aws_client_factory: AwsClientFactory) -> AwsS3FileManager:
    """Create an instance of AwsS3FileManager for testing."""
    return AwsS3FileManager(aws_client_factory=aws_client_factory)


def test_aws_s3_file_manager_initialization(
    aws_client_factory: AwsClientFactory,
) -> None:
    """
    Test the initialization of AwsS3FileManager.

    Verifies:
    - Correct client factory assignment
    - Type checking
    """
    file_manager = AwsS3FileManager(aws_client_factory=aws_client_factory)

    assert file_manager.aws_client_factory == aws_client_factory
    assert isinstance(file_manager.aws_client_factory, AwsClientFactory)


def test_get_full_path(aws_s3_file_manager: AwsS3FileManager) -> None:
    """
    Test the get_full_path method.

    Verifies:
    - Correct S3 URL construction
    - Proper path combination
    - Error handling for empty inputs
    """
    # Test valid inputs
    result = aws_s3_file_manager.get_full_path(
        folder="my-bucket", filename="images/test.png"
    )
    assert result == "s3://my-bucket/images/test.png"

    # Test with root-level file
    result = aws_s3_file_manager.get_full_path(folder="my-bucket", filename="test.png")
    assert result == "s3://my-bucket/test.png"


def test_get_bucket(aws_s3_file_manager: AwsS3FileManager) -> None:
    """
    Test the get_bucket method.

    Verifies:
    - Correct bucket and prefix extraction
    - Handling of different S3 path formats
    - Error handling
    """
    # Test standard S3 path
    s3_url = aws_s3_file_manager.get_bucket(
        filename="test.png", folder="s3://my-bucket/images"
    )
    assert s3_url.bucket == "my-bucket"
    assert s3_url.key == "images/test.png"

    # Test root-level file
    s3_url = aws_s3_file_manager.get_bucket(
        filename="test.png", folder="s3://my-bucket"
    )
    assert s3_url.bucket == "my-bucket"
    assert s3_url.key == "test.png"


@pytest.mark.asyncio
async def test_save_file_async_success(
    aws_s3_file_manager: AwsS3FileManager, mock_s3: S3Client
) -> None:
    """
    Comprehensive test for save_file_async method.

    Verifies:
    - Successful file upload
    - Correct S3 path returned
    - File contents match
    - Different file types and sizes
    """
    # Create S3 bucket
    bucket_name = "test-bucket"
    mock_s3.create_bucket(Bucket=bucket_name)

    # Test cases with different file contents and paths
    test_cases: List[Dict[str, Any]] = [
        {
            "image_data": b"small image content",
            "folder": f"s3://{bucket_name}/images",
            "filename": "small.jpg",
            "content_type": "image/jpeg",
        },
        {
            "image_data": b"x" * 1024 * 1024,  # 1MB file
            "folder": f"s3://{bucket_name}/large",
            "filename": "large.png",
            "content_type": "image/png",
        },
    ]

    for case in test_cases:
        # Save file
        filename_ = case["filename"]
        result = await aws_s3_file_manager.save_file_async(
            file_data=case["image_data"],
            folder=case["folder"],
            filename=filename_,
        )

        # Assertions
        expected_path = (
            f"s3://{bucket_name}/{filename_}"
            if case["folder"] == f"s3://{bucket_name}"
            else result
        )
        assert result == expected_path
        assert expected_path
        s3_url: S3Url = S3Url(expected_path)

        # Verify file was saved correctly
        response = mock_s3.get_object(Bucket=s3_url.bucket, Key=s3_url.key)
        saved_content = response["Body"].read()
        assert saved_content == case["image_data"]


@pytest.mark.asyncio
async def test_save_file_async_edge_cases(
    aws_s3_file_manager: AwsS3FileManager,
) -> None:
    """
    Test edge cases for save_file_async.

    Verifies:
    - Empty file handling
    - Invalid input validation
    """
    # Test empty file
    result = await aws_s3_file_manager.save_file_async(
        file_data=b"", folder="s3://test-bucket/images", filename="empty.jpg"
    )
    assert result is None

    # Test invalid folder (missing s3://)
    with pytest.raises(ValueError, match="folder should contain s3://"):
        await aws_s3_file_manager.save_file_async(
            file_data=b"test", folder="invalid-bucket", filename="test.jpg"
        )

    # Test invalid filename (contains s3://)
    with pytest.raises(ValueError, match="filename should not contain s3://"):
        await aws_s3_file_manager.save_file_async(
            file_data=b"test", folder="s3://test-bucket", filename="s3://test.jpg"
        )


@pytest.mark.asyncio
async def test_read_file_async_success(
    aws_s3_file_manager: AwsS3FileManager, mock_s3: S3Client
) -> None:
    """
    Comprehensive test for read_file_async method.

    Verifies:
    - Successful file reading
    - Correct response type
    - Streaming content
    - Different file types and sizes
    """
    # Create S3 bucket
    bucket_name = "test-bucket"
    mock_s3.create_bucket(Bucket=bucket_name)

    # Test cases with different file contents and types
    test_cases: List[Dict[str, Any]] = [
        {
            "content": b"small image content",
            "filename": "small.jpg",
            "content_type": "image/jpeg",
        },
        {
            "content": b"x" * 1024 * 1024,  # 1MB file
            "filename": "large.png",
            "content_type": "image/png",
        },
    ]

    for case in test_cases:
        # Upload test file
        mock_s3.put_object(
            Bucket=bucket_name,
            Key=case["filename"],
            Body=case["content"],
            ContentType=case["content_type"],
        )

        # Read file
        response = await aws_s3_file_manager.read_file_async(
            folder=bucket_name, file_path=case["filename"]
        )

        # Assertions
        assert isinstance(response, StreamingResponse)
        assert response.status_code == 200

        # Read streaming response content
        content = b""
        async for chunk in response.body_iterator:
            assert isinstance(chunk, bytes)
            content += chunk

        assert content == case["content"]


@pytest.mark.asyncio
async def test_read_file_async_error_cases(
    aws_s3_file_manager: AwsS3FileManager, mock_s3: S3Client
) -> None:
    """
    Test error cases for read_file_async.

    Verifies:
    - File not found handling
    - Bucket not found handling
    - Invalid input validation
    """
    # Create S3 bucket
    bucket_name = "test-bucket"
    mock_s3.create_bucket(Bucket=bucket_name)

    # Test file not found
    response = await aws_s3_file_manager.read_file_async(
        folder=bucket_name, file_path="nonexistent.jpg"
    )
    assert isinstance(response, Response)
    assert response.status_code == 404
    assert b"File not found" in response.body

    # Test invalid folder input
    with pytest.raises(ValueError, match="folder should not contain s3://"):
        await aws_s3_file_manager.read_file_async(
            folder="s3://test-bucket", file_path="test.jpg"
        )

    # Test invalid file path input
    with pytest.raises(ValueError, match="file_path should not contain s3://"):
        await aws_s3_file_manager.read_file_async(
            folder=bucket_name, file_path="s3://test.jpg"
        )


class MyModel:
    def __init__(self, name: str, value: Any) -> None:
        self.name = name
        self.value = value

    def save(self) -> None:
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.put_object(Bucket="mybucket", Key=self.name, Body=self.value)


@pytest.mark.asyncio
async def test_mock_aws() -> None:
    with mock_aws():
        conn = boto3.resource("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="mybucket")

        model_instance = MyModel("steve", "is awesome")
        model_instance.save()

        body = conn.Object("mybucket", "steve").get()["Body"].read().decode("utf-8")

        assert body == "is awesome"
