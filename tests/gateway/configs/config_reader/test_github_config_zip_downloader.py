import os
import pytest
from language_model_gateway.configs.config_reader.github_config_zip_reader import (
    GitHubConfigZipDownloader,
)


@pytest.mark.skipif(
    os.getenv("GITHUB_TOKEN") is None,
    reason="Requires GITHUB_TOKEN",
)
async def test_download_zip_from_github() -> None:
    # Public repo zip URL
    # zip_url = "https://github.com/icanbwell/language-model-gateway-configuration/zipball/main/"
    zip_url = "https://api.github.com/repos/icanbwell/language-model-gateway-configuration/zipball/main"
    downloader = GitHubConfigZipDownloader()
    extracted_path = await downloader.download_zip(zip_url)

    # Check that the extracted path exists and contains expected files
    assert os.path.exists(extracted_path)
    # Check that at least one file exists in the extracted directory
    files = [
        f
        for f in os.listdir(extracted_path)
        if os.path.isfile(os.path.join(extracted_path, f))
    ]
    dirs = [
        d
        for d in os.listdir(extracted_path)
        if os.path.isdir(os.path.join(extracted_path, d))
    ]
    assert files or dirs
    # print the files and directories recursively
    for root, dirs, files in os.walk(extracted_path):
        for name in files:
            print(os.path.join(root, name))
        for name in dirs:
            print(os.path.join(root, name))

    # Clean up
    for root, dirs, files in os.walk(extracted_path, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(extracted_path)
