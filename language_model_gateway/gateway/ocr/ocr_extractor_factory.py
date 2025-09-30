from language_model_gateway.gateway.aws.aws_client_factory import AwsClientFactory
from language_model_gateway.gateway.file_managers.file_manager_factory import (
    FileManagerFactory,
)
from language_model_gateway.gateway.ocr.aws_ocr_extractor import AwsOCRExtractor
from language_model_gateway.gateway.ocr.ocr_extractor import OCRExtractor


class OCRExtractorFactory:
    def __init__(
        self,
        *,
        aws_client_factory: AwsClientFactory,
        file_manager_factory: FileManagerFactory,
    ) -> None:
        self.aws_client_factory: AwsClientFactory = aws_client_factory
        if self.aws_client_factory is None:
            raise ValueError("aws_client_factory must not be None")
        if not isinstance(self.aws_client_factory, AwsClientFactory):
            raise TypeError(
                "aws_client_factory must be an instance of AwsClientFactory"
            )
        self.file_manager_factory: FileManagerFactory = file_manager_factory
        if self.file_manager_factory is None:
            raise ValueError("file_manager_factory must not be None")
        if not isinstance(self.file_manager_factory, FileManagerFactory):
            raise TypeError(
                "file_manager_factory must be an instance of FileManagerFactory"
            )

    # noinspection PyMethodMayBeStatic
    def get(self, *, name: str) -> OCRExtractor:
        match name:
            case "aws":
                return AwsOCRExtractor(
                    aws_client_factory=self.aws_client_factory,
                    file_manager_factory=self.file_manager_factory,
                )
            case _:
                raise ValueError(f"Unknown OCR extractor: {name}")
