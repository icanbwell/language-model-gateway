from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class SkillSummary:
    """Lightweight metadata describing an Agent Skill."""

    name: str
    description: str
    source_path: Path
    license: str | None = None
    compatibility: str | None = None
    metadata: Mapping[str, str] = field(default_factory=dict)
    allowed_tools: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SkillDetails:
    """Full Agent Skill definition including resolved content."""

    summary: SkillSummary
    content: str
    source_path: Path

    @property
    def name(self) -> str:
        return self.summary.name

    @property
    def description(self) -> str:
        return self.summary.description
