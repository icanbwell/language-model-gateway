import argparse
import json
import logging
from typing import Dict, Any, List, cast

import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_openai_config(base_url: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """Fetch the current OpenAI connection config from Open WebUI."""
    url = f"{base_url}/openai/config"
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return cast(Dict[str, Any], response.json())


def update_openai_config(
    base_url: str,
    headers: Dict[str, str],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Update the OpenAI connection config in Open WebUI."""
    url = f"{base_url}/openai/config/update"
    response = requests.post(url, headers=headers, json=config, timeout=30)
    response.raise_for_status()
    return cast(Dict[str, Any], response.json())


def configure_connection(
    base_url: str,
    api_key: str,
    connection_url: str,
    auth_type: str = "system_oauth",
    connection_key: str = "",
    prefix_id: str = "",
    replace: bool = False,
) -> Dict[str, Any]:
    """
    Add or replace an OpenAI-compatible connection in Open WebUI
    configured to forward the user's OAuth token as a Bearer token.

    Args:
        base_url: Open WebUI base URL (e.g. http://localhost:8080)
        api_key: Admin API key for Open WebUI
        connection_url: The OpenAI-compatible API base URL to connect to
        auth_type: Authentication type (system_oauth, bearer, session, none)
        connection_key: Static API key (only used when auth_type is bearer)
        prefix_id: Optional prefix to add to model IDs from this connection
        replace: If True, replace all existing connections; if False, append

    Returns:
        dict: Updated config response
    """
    if not base_url:
        raise ValueError("Base URL must be provided")
    if not api_key:
        raise ValueError("API key must be provided for authentication")
    if not connection_url:
        raise ValueError("Connection URL must be provided")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Normalize URLs
    base_url = base_url.rstrip("/")
    connection_url = connection_url.rstrip("/")

    if replace:
        urls: List[str] = [connection_url]
        keys: List[str] = [connection_key]
        configs: Dict[str, Any] = {}
    else:
        current = get_openai_config(base_url, headers)
        urls = current.get("OPENAI_API_BASE_URLS", [])
        keys = current.get("OPENAI_API_KEYS", [])
        configs = current.get("OPENAI_API_CONFIGS", {})

        # Check if this URL already exists
        if connection_url in urls:
            idx = urls.index(connection_url)
            keys[idx] = connection_key
            logger.info(
                "Connection URL already exists at index %d, updating config", idx
            )
        else:
            urls.append(connection_url)
            keys.append(connection_key)

    # Build the config entry for this connection
    idx = urls.index(connection_url)
    connection_config: Dict[str, Any] = {
        "auth_type": auth_type,
        "enable": True,
    }
    if prefix_id:
        connection_config["prefix_id"] = prefix_id

    configs[str(idx)] = connection_config

    payload = {
        "ENABLE_OPENAI_API": True,
        "OPENAI_API_BASE_URLS": urls,
        "OPENAI_API_KEYS": keys,
        "OPENAI_API_CONFIGS": configs,
    }

    logger.info(
        "Configuring connection to %s with auth_type=%s", connection_url, auth_type
    )
    logger.debug("Payload: %s", json.dumps(payload, indent=2))

    result = update_openai_config(base_url, headers, payload)

    logger.info("Successfully configured OpenAI connection")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Configure an OpenAI-compatible connection in Open WebUI. "
            "By default, sets auth_type to system_oauth so the user's "
            "OAuth access token is forwarded as a Bearer token to the LLM API."
        )
    )

    parser.add_argument(
        "-u",
        "--url",
        required=True,
        help="Open WebUI base URL (e.g. http://localhost:8080)",
    )
    parser.add_argument(
        "-k", "--api-key", required=True, help="Open WebUI admin API key"
    )
    parser.add_argument(
        "-c",
        "--connection-url",
        required=True,
        help="OpenAI-compatible API base URL to connect to (e.g. https://my-llm-api.example.com/v1)",
    )
    parser.add_argument(
        "-a",
        "--auth-type",
        default="system_oauth",
        choices=[
            "system_oauth",
            "bearer",
            "session",
            "none",
            "azure_ad",
            "microsoft_entra_id",
        ],
        help="Authentication type (default: system_oauth)",
    )
    parser.add_argument(
        "--connection-key",
        default="",
        help="Static API key for the connection (only needed for auth_type=bearer)",
    )
    parser.add_argument(
        "--prefix-id",
        default="",
        help="Optional prefix to add to model IDs from this connection",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace all existing connections instead of appending",
    )

    args = parser.parse_args()

    result = configure_connection(
        base_url=args.url,
        api_key=args.api_key,
        connection_url=args.connection_url,
        auth_type=args.auth_type,
        connection_key=args.connection_key,
        prefix_id=args.prefix_id,
        replace=args.replace,
    )

    logger.debug("Updated config:\n%s", json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
