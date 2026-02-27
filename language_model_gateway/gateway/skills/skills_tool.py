from __future__ import annotations

from typing import Type

from langchain_core.callbacks import (
    AsyncCallbackManagerForToolRun,
    CallbackManagerForToolRun,
)
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field

from baileyai.skills.skill_loader import (
    SkillLoaderProtocol,
    SkillNotFoundError,
)


class LoadSkillInput(BaseModel):
    """Input schema for the load_skill tool."""

    model_config = ConfigDict(extra="forbid")

    skill_name: str = Field(
        description="Name of the skill to load (e.g., 'sales_analytics').",
        default="",
    )


class LoadSkillTool(BaseTool):
    """LangChain tool that loads full skill definitions for the agent."""

    name: str = "load_skill"
    description: str = (
        "Load the full content of a skill into the agent's context for detailed"
        " handling instructions, policies, and guidelines."
    )
    args_schema: Type[BaseModel] = LoadSkillInput
    skill_loader: SkillLoaderProtocol

    def _run(
        self,
        skill_name: str,
        run_manager: CallbackManagerForToolRun | None = None,
    ) -> str:
        return self._load_skill(skill_name)

    async def _arun(
        self,
        skill_name: str,
        run_manager: AsyncCallbackManagerForToolRun | None = None,
    ) -> str:
        return self._load_skill(skill_name)

    def _load_skill(self, skill_name: str) -> str:
        normalized_name = skill_name.strip()
        if not normalized_name:
            return self._format_availability_message(self.skill_loader, normalized_name)

        try:
            skill = self.skill_loader.get_skill_details(normalized_name)
        except SkillNotFoundError:
            return self._format_availability_message(self.skill_loader, normalized_name)

        return f"Loaded skill: {skill.name}\n\n{skill.content}"

    @staticmethod
    def _format_availability_message(
        loader: SkillLoaderProtocol, normalized_name: str
    ) -> str:
        available = ", ".join(summary.name for summary in loader.list_skill_summaries())
        availability_message = (
            f"Skill '{normalized_name}' not found."
            if normalized_name
            else "No skill name provided."
        )
        return (
            f"{availability_message} Available skills: {available or 'None configured'}"
        )
