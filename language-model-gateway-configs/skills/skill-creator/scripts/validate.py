# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "skills_ref>=0.1.1",
# ]
# ///

from __future__ import annotations

import sys

from skills_ref.errors import ParseError
from skills_ref.parser import parse_frontmatter
from skills_ref.validator import validate_metadata


def main() -> int:
    if sys.stdin.isatty():
        print("Expected SKILL.md content on stdin.")
        return 1

    skill_content = sys.stdin.read()
    if not skill_content.strip():
        print("No content received on stdin.")
        return 1

    try:
        metadata, _ = parse_frontmatter(skill_content)
    except ParseError as exc:
        print(str(exc))
        print("skills validation failed (1 skills-ref error(s)).")
        return 1

    validation_errors = validate_metadata(metadata)
    if validation_errors:
        for error in validation_errors:
            print(error)
        print(f"skills validation failed ({len(validation_errors)} skills-ref error(s)).")
        return 1

    print("Validated 1 skill from stdin with skills-ref validator.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
