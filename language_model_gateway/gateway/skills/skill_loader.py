from __future__ import annotations

import re
import sys
from pathlib import Path
from threading import RLock
from types import MappingProxyType
from typing import Mapping, MutableMapping, Protocol, Sequence, cast, runtime_checkable
from uuid import UUID, uuid4

import yaml

from baileyai.skills.skills_model import SkillDetails, SkillSummary
from baileyai.utilities.cache.skill_cache import SkillCache, SkillCacheSnapshot
from baileyai.utilities.environment.baileyai_environment_variables import (
    BaileyAIEnvironmentVariables,
)
from baileyai.utilities.logger.log_levels import (
    SRC_LOG_LEVELS,
    logger,
)

logger.add(sys.stderr, level=SRC_LOG_LEVELS["CONFIG"])


class SkillLoaderError(RuntimeError):
    """Base exception for skill loading failures."""


class SkillValidationError(SkillLoaderError):
    """Raised when a skill definition violates the Agent Skills specification."""


class SkillNotFoundError(SkillLoaderError):
    """Raised when a requested skill cannot be found."""


@runtime_checkable
class SkillLoaderProtocol(Protocol):
    def list_skill_summaries(self) -> Sequence[SkillSummary]: ...

    def get_skill_details(self, skill_name: str) -> SkillDetails: ...

    def refresh(self) -> None: ...


class SkillDirectoryLoader(SkillLoaderProtocol):
    """Loads Agent Skills from a directory following the AgentSkills specification."""

    _skill_name_pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    def __init__(
        self,
        environment_variables: BaileyAIEnvironmentVariables,
        *,
        cache: SkillCache,
    ) -> None:
        self._identifier: UUID = uuid4()
        if cache is None:
            raise ValueError("cache must not be None")
        configured_directory = environment_variables.skills_directory
        if not configured_directory:
            raise SkillValidationError("SKILLS_DIRECTORY is not configured")
        self._skills_directory = Path(configured_directory).expanduser()
        self._lock = RLock()
        self._cache = cache
        self._snapshot: SkillCacheSnapshot | None = None
        logger.info(
            "SkillDirectoryLoader %s initialized for %s",
            self._identifier,
            self._skills_directory,
        )

    def list_skill_summaries(self) -> Sequence[SkillSummary]:
        snapshot = self._get_snapshot()
        logger.debug(
            "SkillDirectoryLoader %s returning %d summaries",
            self._identifier,
            len(snapshot.ordered_summaries),
        )
        return snapshot.ordered_summaries

    def get_skill_details(self, skill_name: str) -> SkillDetails:
        normalized = self._normalize_skill_name(skill_name)
        snapshot = self._get_snapshot()
        try:
            return snapshot.details_by_name[normalized]
        except KeyError as exc:
            logger.warning(
                "SkillDirectoryLoader %s could not find skill '%s'",
                self._identifier,
                skill_name,
            )
            raise SkillNotFoundError(f"Skill '{skill_name}' not found") from exc

    def refresh(self) -> None:
        with self._lock:
            logger.info("SkillDirectoryLoader %s refreshing cache", self._identifier)
            self._cache.clear()
            self._snapshot = None
            snapshot = self._build_snapshot()
            self._cache.set(snapshot)
            self._snapshot = snapshot

    def _get_snapshot(self) -> SkillCacheSnapshot:
        if self._snapshot is not None:
            logger.debug(
                "SkillDirectoryLoader %s using instance snapshot",
                self._identifier,
            )
            return self._snapshot

        cached_snapshot = self._cache.get()
        if cached_snapshot is not None:
            logger.debug(
                "SkillDirectoryLoader %s using shared cached snapshot",
                self._identifier,
            )
            self._snapshot = cached_snapshot
            return cached_snapshot

        with self._lock:
            if self._snapshot is not None:
                return self._snapshot
            cached_snapshot = self._cache.get()
            if cached_snapshot is not None:
                logger.debug(
                    "SkillDirectoryLoader %s observed cache fill while waiting",
                    self._identifier,
                )
                self._snapshot = cached_snapshot
                return cached_snapshot

            logger.info(
                "SkillDirectoryLoader %s cache miss; loading skills",
                self._identifier,
            )
            snapshot = self._build_snapshot()
            self._cache.set(snapshot)
            self._snapshot = snapshot
            return snapshot

    def _build_snapshot(self) -> SkillCacheSnapshot:
        logger.info(
            "SkillDirectoryLoader %s scanning directory %s",
            self._identifier,
            self._skills_directory,
        )
        if not self._skills_directory.exists():
            logger.warning(
                "Skills directory %s does not exist. No skills will be available.",
                self._skills_directory,
            )
            return SkillCacheSnapshot(
                details_by_name=MappingProxyType({}), ordered_summaries=()
            )

        if not self._skills_directory.is_dir():
            raise SkillValidationError(
                f"Configured skills path '{self._skills_directory}' is not a directory"
            )

        new_details: dict[str, SkillDetails] = {}
        new_summaries: list[SkillSummary] = []
        for entry in sorted(self._skills_directory.iterdir()):
            if not entry.is_dir():
                continue
            skill_file = entry / "SKILL.md"
            if not skill_file.is_file():
                logger.warning(
                    "Skipping skill directory %s because SKILL.md is missing",
                    entry,
                )
                continue
            definition = self._parse_skill(entry.name, skill_file)
            if definition.name in new_details:
                raise SkillValidationError(
                    f"Duplicate skill name '{definition.name}' detected"
                )
            new_details[definition.name] = definition
            new_summaries.append(definition.summary)
        ordered_summaries = tuple(
            sorted(new_summaries, key=lambda summary: summary.name)
        )
        snapshot = SkillCacheSnapshot(
            details_by_name=MappingProxyType(new_details),
            ordered_summaries=ordered_summaries,
        )
        logger.info(
            "Loaded %d Agent Skills from %s",
            len(ordered_summaries),
            self._skills_directory,
        )
        return snapshot

    def _parse_skill(self, directory_name: str, skill_file: Path) -> SkillDetails:
        raw_content = skill_file.read_text(encoding="utf-8")
        normalized = raw_content.replace("\r\n", "\n")
        if not normalized.startswith("---\n"):
            raise SkillValidationError(
                f"Skill {directory_name} missing YAML frontmatter header"
            )
        closing_index = normalized.find("\n---", 4)
        if closing_index == -1:
            raise SkillValidationError(
                f"Skill {directory_name} missing YAML frontmatter terminator"
            )
        frontmatter_text = normalized[4:closing_index]
        body = normalized[closing_index + len("\n---") :].lstrip("\n")
        data = self._load_frontmatter(frontmatter_text)
        skill_name: str | None = cast(str | None, data.get("name"))
        description: str | None = cast(str | None, data.get("description"))
        license_value = data.get("license")
        compatibility_value = data.get("compatibility")
        metadata_value = data.get("metadata", {})
        allowed_tools_value = data.get("allowed-tools")
        if not isinstance(skill_name, str):
            raise SkillValidationError(
                f"Skill {directory_name} is missing the required 'name' field"
            )
        normalized_name = self._normalize_skill_name(skill_name)
        if skill_name != normalized_name:
            raise SkillValidationError(
                "Skill names must be lowercase and use hyphens only"
            )
        if normalized_name != self._normalize_skill_name(directory_name):
            raise SkillValidationError(
                f"Skill skill_name '{skill_name}' must match directory '{directory_name}'"
            )
        if len(skill_name) > 64:
            raise SkillValidationError(
                f"Skill skill_name '{skill_name}' exceeds 64 characters"
            )
        if not self._skill_name_pattern.fullmatch(normalized_name):
            raise SkillValidationError(
                f"Skill skill_name '{skill_name}' contains invalid characters"
            )
        if not isinstance(description, str) or not description.strip():
            raise SkillValidationError(
                f"Skill {skill_name} must include a non-empty description"
            )
        if len(description) > 1024:
            raise SkillValidationError(
                f"Skill {skill_name} description exceeds 1024 characters"
            )
        if compatibility_value is not None:
            if (
                not isinstance(compatibility_value, str)
                or not compatibility_value.strip()
            ):
                raise SkillValidationError(
                    f"Skill {skill_name} compatibility must be a non-empty string when provided"
                )
            if len(compatibility_value) > 500:
                raise SkillValidationError(
                    f"Skill {skill_name} compatibility exceeds 500 characters"
                )
        if license_value is not None and not isinstance(license_value, str):
            raise SkillValidationError(
                f"Skill {skill_name} license must be a string when provided"
            )
        metadata: MutableMapping[str, str] = {}
        if metadata_value is not None:
            if not isinstance(metadata_value, Mapping):
                raise SkillValidationError(
                    f"Skill {skill_name} metadata must be a mapping of string keys to string values"
                )
            for key, value in metadata_value.items():
                if not isinstance(key, str):
                    raise SkillValidationError(
                        f"Skill {skill_name} metadata entries must be strings: {type(key)}, {type(value)}"
                    )
                metadata[key] = str(value)
        allowed_tools: tuple[str, ...] = ()
        if isinstance(allowed_tools_value, str):
            allowed_tools = tuple(tool for tool in allowed_tools_value.split() if tool)
        elif allowed_tools_value is not None:
            raise SkillValidationError(
                f"Skill {skill_name} allowed-tools must be a space-delimited string"
            )
        summary = SkillSummary(
            name=normalized_name,
            description=description.strip(),
            source_path=skill_file,
            license=license_value.strip() if isinstance(license_value, str) else None,
            compatibility=(
                compatibility_value.strip()
                if isinstance(compatibility_value, str)
                else None
            ),
            metadata=dict(metadata),
            allowed_tools=allowed_tools,
        )
        if not body.strip():
            logger.warning("Skill %s has empty body content", normalized_name)
        return SkillDetails(summary=summary, content=body, source_path=skill_file)

    @staticmethod
    def _load_frontmatter(frontmatter_text: str) -> MutableMapping[str, object]:
        try:
            loaded = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError as exc:
            raise SkillValidationError("Invalid YAML frontmatter") from exc
        if not isinstance(loaded, MutableMapping):
            raise SkillValidationError("Frontmatter must be a mapping")
        return loaded

    @staticmethod
    def _normalize_skill_name(value: str) -> str:
        normalized = value.strip().lower().replace("_", "-")
        normalized = re.sub(r"-+", "-", normalized)
        return normalized.strip("-")
