from language_model_gateway.gateway.aws.aws_client_factory import AwsClientFactory
from language_model_gateway.gateway.file_managers.aws_s3_file_manager import (
    AwsS3FileManager,
)
from language_model_gateway.gateway.file_managers.file_manager import FileManager
from language_model_gateway.gateway.file_managers.local_file_manager import (
    LocalFileManager,
)


class FileManagerFactory:
    def __init__(self, *, aws_client_factory: AwsClientFactory) -> None:
        self.aws_client_factory = aws_client_factory
        if self.aws_client_factory is None:
            raise ValueError("aws_client_factory must not be None")
        if not isinstance(self.aws_client_factory, AwsClientFactory):
            raise TypeError(
                f"aws_client_factory must be AwsClientFactory, got {type(self.aws_client_factory)}"
            )

    def get_file_manager(self, *, folder: str) -> FileManager:
        if folder.startswith("s3"):
            return AwsS3FileManager(aws_client_factory=self.aws_client_factory)
        else:
            return LocalFileManager()
