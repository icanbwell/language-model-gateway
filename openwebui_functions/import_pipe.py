import argparse
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, cast, List

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def create_function(
    base_url: str,
    api_key: str,
    contents_file_path: Optional[str] = None,
    json_config_file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a function using API key authentication

    Args:
        base_url (str): Base URL of the service
        api_key (str): API key for authentication
        contents_file_path (Optional[str]): Path to function contents file
        json_config_file_path (Optional[str]): Path to JSON config file

    Returns:
        dict: Function creation response
    """
    # Function creation endpoint
    function_create_url = f"{base_url}/api/v1/functions/create"
    toggle_function_url = (
        f"{base_url}/api/v1/functions/id/language_model_gateway/toggle"
    )

    # Prepare headers with API key
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    if not api_key:
        raise ValueError("API key must be provided for authentication")

    if not base_url:
        raise ValueError("Base URL must be provided")

    if not contents_file_path:
        raise ValueError("Contents file path must be provided")

    if not json_config_file_path:
        raise ValueError("JSON config file path must be provided")

    # first read the config json file
    with Path(json_config_file_path).open("r", encoding="utf-8") as f:
        json_config: List[Dict[str, Any]] = json.load(f)
        if not isinstance(json_config, list):
            raise ValueError("JSON config file must contain a list of configurations")
        if len(json_config) == 0:
            raise ValueError("JSON config file must contain at least one configuration")

    with Path(contents_file_path).open("r", encoding="utf-8") as f:
        py_content: str = f.read()

    first_json_config: Dict[str, Any] = json_config[0]
    if not isinstance(first_json_config, dict):
        raise ValueError(
            "Each configuration in the JSON config file must be a dictionary"
        )

    first_json_config["content"] = py_content

    payload: Dict[str, Any] = first_json_config

    # logger.info the request headers and payload for debugging
    logger.debug("url:", function_create_url)
    logger.debug("==== Headers ====")
    # Remove or redact API key before logging
    sanitized_headers = dict(headers)
    if "Authorization" in sanitized_headers:
        sanitized_headers["Authorization"] = "Bearer ***REDACTED***"
    logger.debug(json.dumps(sanitized_headers))
    logger.debug("==== Payload ====")
    logger.debug(json.dumps(payload))
    logger.debug("==== End of Payload ====")

    # Create function
    response = requests.post(
        function_create_url, headers=headers, json=payload, timeout=30
    )

    response.raise_for_status()

    # now call the toggle function
    if not toggle_function_url.startswith(('https://', 'http://')):
        raise ValueError("Invalid URL scheme. Only http:// or https:// are allowed.")
    response2 = requests.post(toggle_function_url, headers=headers, timeout=30)

    response2.raise_for_status()

    logger.info("Finished importing pipe into OpenWebUI")

    return cast(Dict[str, Any], response.json())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create function with API key authentication"
    )

    parser.add_argument("-u", "--url", required=True, help="Base URL")
    parser.add_argument(
        "-k", "--api-key", required=True, help="API Key for authentication"
    )
    parser.add_argument(
        "-f", "--file", help="Path to Python file containing the code", required=True
    )
    parser.add_argument("-j", "--json", help="Path to json config file", required=True)

    args = parser.parse_args()

    # Create function
    result = create_function(
        base_url=args.url,
        api_key=args.api_key,
        contents_file_path=args.file,
        json_config_file_path=args.json,
    )

    logger.debug("Function created successfully:")
    logger.debug(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
