# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "skills_ref>=0.1.1",
# ]
# ///

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from skills_ref.errors import ParseError
from skills_ref.parser import parse_frontmatter


MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500


def validate_frontmatter_lengths(skill_file: Path) -> list[str]:
    errors: list[str] = []

    try:
        content = skill_file.read_text(encoding="utf-8")
        metadata, _ = parse_frontmatter(content)
    except ParseError as exc:
        # skills-ref already reports parser issues; keep this check additive.
        return [str(exc)]

    name = metadata.get("name")
    if isinstance(name, str):
        name_length = len(name.strip())
        if not 1 <= name_length <= MAX_NAME_LENGTH:
            errors.append(
                f"{skill_file}: name length must be 1-{MAX_NAME_LENGTH} characters "
                f"(found {name_length})"
            )

    description = metadata.get("description")
    if isinstance(description, str):
        description_length = len(description.strip())
        if not 1 <= description_length <= MAX_DESCRIPTION_LENGTH:
            errors.append(
                f"{skill_file}: description length must be 1-{MAX_DESCRIPTION_LENGTH} characters "
                f"(found {description_length})"
            )

    if "compatibility" in metadata:
        compatibility = metadata.get("compatibility")
        if isinstance(compatibility, str):
            compatibility_length = len(compatibility.strip())
            if not 1 <= compatibility_length <= MAX_COMPATIBILITY_LENGTH:
                errors.append(
                    f"{skill_file}: compatibility length must be 1-{MAX_COMPATIBILITY_LENGTH} "
                    f"characters when provided (found {compatibility_length})"
                )

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    skills_roots = [
        repo_root / "configs" / "skills",
        repo_root / "bailey" / "skills",
    ]

    existing_roots = [
        skills_root for skills_root in skills_roots if skills_root.exists()
    ]
    if not existing_roots:
        roots_text = ", ".join(str(skills_root) for skills_root in skills_roots)
        print(f"Skills directories not found: {roots_text}")
        return 1

    skill_files = sorted(
        skill_file
        for skills_root in existing_roots
        for skill_file in skills_root.rglob("SKILL.md")
    )
    if not skill_files:
        roots_text = ", ".join(str(skills_root) for skills_root in existing_roots)
        print(f"No skill files found under: {roots_text}")
        return 1

    skills_ref_failures = 0
    extra_errors: list[str] = []
    for skill_file in skill_files:
        skill_dir = skill_file.parent
        command = [sys.executable, "-m", "skills_ref.cli", "validate", str(skill_dir)]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            skills_ref_failures += 1
            print(result.stdout.strip())
            if result.stderr.strip():
                print(result.stderr.strip())

        extra_errors.extend(validate_frontmatter_lengths(skill_file))

    if extra_errors:
        for error in extra_errors:
            print(error)

    if skills_ref_failures or extra_errors:
        print(
            "skills validation failed "
            f"({skills_ref_failures} skills-ref error(s), {len(extra_errors)} length error(s))."
        )
        return 1

    print(
        f"Validated {len(skill_files)} skill(s) with skills-ref across "
        f"{len(existing_roots)} root(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
