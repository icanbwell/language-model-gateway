# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "skills_ref>=0.1.1",
# ]
# ///

from __future__ import annotations

import sys
from collections.abc import Sequence

from skills_ref.errors import ParseError
from skills_ref.parser import parse_frontmatter
from skills_ref.validator import validate_metadata


HELP_TEXT = (
    "Usage: validate.py [OPTIONS]\n\n"
    "Validate SKILL.md content provided on stdin using skills_ref.\n\n"
    "Options:\n"
    "  -help, --help      Show this help message and exit\n\n"
    "Examples:\n"
    "  cat SKILL.md | validate.py\n"
)


def _help_requested(argv: Sequence[str]) -> bool:
    if len(argv) == 1:
        return False
    if len(argv) == 2 and argv[1] in {"-help", "--help"}:
        return True
    raise ValueError("unsupported arguments; use -help")


def main() -> int:
    try:
        if _help_requested(sys.argv):
            sys.stdout.write(HELP_TEXT)
            return 0

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
            print(
                f"skills validation failed ({len(validation_errors)} skills-ref error(s))."
            )
            return 1

        print("Validated 1 skill from stdin with skills-ref validator.")
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
