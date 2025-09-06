import json
import logging
import re
from typing import Dict, Any, List, cast


logger = logging.getLogger(__name__)


class JsonExtractor:
    @staticmethod
    def extract_structured_output(
        text: str,
    ) -> Dict[str, Any] | List[Dict[str, Any]] | str:
        # Try to find content between <json> tags
        json_match = re.search(
            r"<json>(.*?)</json>", text, re.DOTALL | re.IGNORECASE | re.MULTILINE
        )

        if json_match:
            try:
                # Extract and parse the JSON content
                json_content1 = json_match.group(1).strip()
                return cast(
                    Dict[str, Any] | List[Dict[str, Any]], json.loads(json_content1)
                )
            except json.JSONDecodeError as e:
                logger.exception(f"JSON Decode Error: {e}")
                return {}

        # Fallback: try to find any JSON-like structure
        json_matches = re.findall(r"\{.*?\}", text, re.DOTALL)

        for match in reversed(json_matches):
            try:
                return cast(Dict[str, Any] | List[Dict[str, Any]], json.loads(match))
            except json.JSONDecodeError:
                continue

        return text
