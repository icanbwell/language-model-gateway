import asyncio
import json
import logging
import os
import tempfile
import zipfile
from typing import List, Optional

import httpx

from language_model_gateway.configs.config_schema import ChatModelConfig

logger = logging.getLogger(__name__)


class GitHubConfigZipDownloader:
    def __init__(
        self,
        github_token: Optional[str] = None,
        max_retries: int = 3,
        base_delay: int = 1,
    ) -> None:
        """
        Initialize GitHub configuration downloader

        Args:
            github_token: Optional GitHub API token
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff
        """
        self.github_token: Optional[str] = github_token or os.environ.get(
            "GITHUB_TOKEN"
        )
        self.max_retries: int = max_retries
        self.base_delay: int = base_delay
        self.timeout: int = int(os.environ.get("GITHUB_TIMEOUT", 3600))

    async def download_zip(
        self, zip_url: str, target_path: Optional[str] = None
    ) -> str:
        """
        Download ZIP file from given URL

        Args:
            zip_url: Full URL to the ZIP file
            target_path: Optional target directory for extraction

        Returns:
            Path to the extracted repository
        """
        # Create a temporary directory if no target path is provided
        if target_path is None:
            target_path = tempfile.mkdtemp(prefix="github_config_")

        # Ensure target path exists
        os.makedirs(target_path, exist_ok=True)

        async def download_with_retry(url: str) -> bytes:
            """
            Download with exponential backoff and retry logic

            Args:
                url: Download URL

            Returns:
                Downloaded content as bytes
            """
            headers = {}
            if self.github_token:
                headers["Authorization"] = f"Bearer {self.github_token}"

            headers["X-GitHub-Api-Version"] = "2022-11-28"
            headers["Accept"] = "application/vnd.github+json"

            for attempt in range(self.max_retries):
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(
                            url,
                            headers=headers,
                            follow_redirects=True,
                            timeout=httpx.Timeout(self.timeout),
                        )
                        response.raise_for_status()
                        return response.content
                except Exception as e1:
                    logger.error(
                        f"Download attempt {attempt + 1} failed URL: {url}, token: {self.github_token} {type(e1)}: {str(e1)},",
                        exc_info=True,
                    )

                    # Exponential backoff
                    await asyncio.sleep(self.base_delay * (2**attempt))

            raise RuntimeError(
                f"Failed to download ZIP after {self.max_retries} attempts URL: {url}, token: {self.github_token}"
            )

        try:
            # Download ZIP archive
            logger.info(f"Downloading ZIP from: {zip_url}")
            zip_content = await download_with_retry(zip_url)
            logger.info(f"Downloaded ZIP from {zip_url}")

            # Create a temporary file to save the ZIP
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_zip:
                temp_zip.write(zip_content)
                temp_zip_path = temp_zip.name

            # Extract ZIP archive
            logger.info(f"Extracting ZIP to: {target_path}")
            with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
                # List all contents to find the root directory
                all_contents = zip_ref.namelist()
                root_dir = all_contents[0].split("/")[0] if all_contents else None

                if not root_dir:
                    raise ValueError("Could not find root directory in ZIP archive")

                # Extract all contents
                zip_ref.extractall(path=target_path)

            # Remove temporary ZIP file
            os.unlink(temp_zip_path)

            # Return the full path to the extracted repository
            extracted_path = os.path.join(target_path, root_dir)
            return extracted_path

        except Exception as e:
            logger.error(f"Error downloading ZIP: {str(e)}")
            raise

    @staticmethod
    def _find_json_configs(
        repo_path: str, config_dir: Optional[str] = None
    ) -> List[ChatModelConfig]:
        """
        Find and parse JSON configuration files in the repository

        Args:
            repo_path: Path to the extracted repository
            config_dir: Optional subdirectory to search for configs

        Returns:
            List of parsed JSON configurations
        """
        configs: List[ChatModelConfig] = []

        # Determine search path
        search_path = os.path.join(repo_path, config_dir) if config_dir else repo_path

        # Walk through directory
        for root, _, files in os.walk(search_path):
            for file in files:
                if file.endswith(".json"):
                    try:
                        file_path = os.path.join(root, file)
                        with open(file_path, "r", encoding="utf-8") as f:
                            config = json.load(f)
                            configs.append(ChatModelConfig(**config))
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing JSON from {file}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Unexpected error processing {file}: {str(e)}")

        # sort the configs by name
        configs.sort(key=lambda x: x.name)

        return configs

    async def read_model_configs(
        self,
        *,
        github_url: str,
        models_official_path: str,
        models_testing_path: Optional[str],
    ) -> List[ChatModelConfig]:
        """
        Comprehensive method to download ZIP and extract configs


        Returns:
            List of model configurations
        """
        try:
            # Download and extract ZIP
            repo_path: str = await self.download_zip(zip_url=github_url)

            # Find and parse JSON configs
            configs: List[ChatModelConfig] = self._find_json_configs(
                repo_path=repo_path, config_dir=models_official_path
            )

            if models_testing_path:
                test_configs: List[ChatModelConfig] = self._find_json_configs(
                    repo_path=repo_path, config_dir="configs/chat_completions/testing"
                )

                if test_configs and len(test_configs) > 0:
                    configs.append(
                        ChatModelConfig(
                            id="testing",
                            name="----- Models in Testing -----",
                            description="",
                        )
                    )
                    configs.extend(test_configs)

            return configs

        except Exception as e:
            logger.error(f"Error retrieving model configs: {str(e)}")
            return []
