import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any, cast

import requests


def create_function(
    base_url: str, api_key: str, contents_file_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a function using API key authentication

    Args:
        base_url (str): Base URL of the service
        api_key (str): API key for authentication
        contents_file_path (Optional[str]): Path to function contents file

    Returns:
        dict: Function creation response
    """
    # Function creation endpoint
    function_create_url = f"{base_url}/api/v1/functions/create"

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

    with Path(contents_file_path).open("r", encoding="utf-8") as f:
        py_content = f.read()

    # Compose the JSON structure
    json_obj = [
        {
            "id": "language_model_gateway",
            "user_id": "6c03bf27-dbbf-44c1-b980-2c6a4608f712",
            "name": "language_model_gateway",
            "type": "pipe",
            "content": py_content,
            "meta": {
                "description": "Talks to Language Model Gateway and passes the OAuth ID token in the request cookies as Bearer Authorization header.",
                "manifest": {
                    "title": "Language Model Gateway Pipe",
                    "author": "Imran Qureshi @ b.well Connected Health (mailto:imran.qureshi@bwell.com)",
                    "author_url": "https://github.com/imranq2",
                    "version": "0.1.0",
                },
            },
            "is_active": True,
            "is_global": True,
            "updated_at": 1745989387,
            "created_at": 1745989309,
        }
    ]

    payload = json_obj[0]

    # print the request headers and payload for debugging
    print("url:", function_create_url)
    print("==== Headers ====")
    print(json.dumps(headers))
    print("==== Payload ====")
    print(json.dumps(payload))
    print("==== End of Payload ====")

    # Create function
    response = requests.post(
        function_create_url, headers=headers, json=payload, timeout=30
    )

    response.raise_for_status()
    return cast(Dict[str, Any], response.json())


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create function with API key authentication"
    )

    parser.add_argument("-u", "--url", required=True, help="Base URL")
    parser.add_argument(
        "-k", "--api-key", required=True, help="API Key for authentication"
    )
    parser.add_argument("-f", "--file", help="Path to function contents file")

    args = parser.parse_args()

    # Create function
    result = create_function(
        base_url=args.url, api_key=args.api_key, contents_file_path=args.file
    )

    print("Function created successfully:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
