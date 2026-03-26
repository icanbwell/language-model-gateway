# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "skills_ref>=0.1.1",
# ]
# ///

import json
import sys
from collections.abc import Sequence
from typing import Any

from skills_ref.errors import ParseError
from skills_ref.parser import parse_frontmatter
from skills_ref.validator import validate_metadata


HELP_TEXT = (
    "Usage: validate.py [OPTIONS]\n\n"
    "Validate SKILL.md content provided as JSON on stdin using skills_ref.\n\n"
    "Options:\n"
    "  -help, --help      Show this help message and exit\n\n"
    "Examples:\n"
    "  echo '{\"skill_content\": \"---\\nname: demo\\n---\\n# Demo\"}' | validate.py\n\n"
    "Input JSON keys (stdin):\n"
    "  skill_content      string, required\n"
)


def _help_requested(argv: Sequence[str]) -> bool:
    if len(argv) == 1:
        return False
    if len(argv) == 2 and argv[1] in {"-help", "--help"}:
        return True
    raise ValueError("unsupported arguments; use -help")


def _read_json_input() -> dict[str, Any]:
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        raise ValueError("No content received on stdin.")

    try:
        parsed = json.loads(raw_input)
    except json.JSONDecodeError as error:
        raise ValueError("stdin must contain valid JSON") from error

    if not isinstance(parsed, dict):
        raise ValueError("stdin must be a JSON object")

    return parsed


def _read_skill_content(payload: dict[str, Any]) -> str:
    skill_content = payload.get("skill_content")
    if skill_content is None:
        raise ValueError("No skill_content was sent to validate.py")
    if not isinstance(skill_content, str):
        raise ValueError("skill_content must be a string")
    if not skill_content.strip():
        raise ValueError("No skill_content was sent to validate.py")
    return skill_content


def main() -> int:
    try:
        if _help_requested(sys.argv):
            sys.stdout.write(HELP_TEXT)
            return 0

        payload = _read_json_input()
        skill_content = _read_skill_content(payload)

        try:
            metadata, _ = parse_frontmatter(skill_content)
        except ParseError as exc:
            sys.stderr.write(str(exc))
            sys.stderr.write("skills validation failed (1 skills-ref error(s)).")
            return 1

        validation_errors = validate_metadata(metadata)
        if validation_errors:
            for error in validation_errors:
                sys.stderr.write(error)
            sys.stderr.write(
                f"skills validation failed ({len(validation_errors)} skills-ref error(s))."
            )
            return 1

        sys.stdout.write(skill_content)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
