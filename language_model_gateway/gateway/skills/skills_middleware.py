from html import escape
from langchain.agents.middleware import (
    ModelRequest,
    ModelResponse,
    AgentMiddleware,
    ExtendedModelResponse,
)
from langchain.messages import SystemMessage
from typing import Callable, Any, Awaitable

from langchain_core.messages import AIMessage, AnyMessage

from baileyai.skills.skill_loader import (
    SkillLoaderProtocol,
)
from baileyai.skills.skills_model import SkillSummary


class SkillMiddleware(AgentMiddleware):
    """Middleware that injects skill descriptions into the system prompt."""

    def __init__(self, skill_loader: SkillLoaderProtocol) -> None:
        """Initialize and generate the skills prompt from the configured directory."""

        self._skill_loader = skill_loader
        self.skills_prompt = self._build_skills_prompt()

    def _build_skills_prompt(self) -> str:
        if self._skill_loader is None:
            return "No skills are currently available."
        summaries = self._skill_loader.list_skill_summaries()
        if not summaries:
            return "No skills are currently configured."
        skills_block = " ".join(
            self._format_skill_entry(summary) for summary in summaries
        )
        return f"<available_skills> {skills_block} </available_skills>"

    @staticmethod
    def _format_skill_entry(summary: SkillSummary) -> str:
        escaped_name = escape(summary.name, quote=True)
        escaped_description = escape(summary.description.strip(), quote=True)
        return (
            "<skill>"
            f"<name> {escaped_name} </name> "
            f"<description> {escaped_description} </description> "
            "</skill>"
        )

    async def awrap_model_call(
        self,
        request: ModelRequest[Any],
        handler: Callable[[ModelRequest[Any]], Awaitable[ModelResponse[Any]]],
    ) -> ModelResponse[Any] | AIMessage | ExtendedModelResponse[Any]:
        """Sync: Inject skill descriptions into system prompt."""
        skills_addendum = (
            f"\n\n{self.skills_prompt}\n\n"
            "Use the load_skill tool when you need detailed information "
            "about handling a specific type of request."
        )
        skills_block_text = skills_addendum
        skills_message = SystemMessage(content=skills_block_text)

        if request.system_message is None:
            modified_request = request.override(system_message=skills_message)
            return await handler(modified_request)

        existing_messages: list[AnyMessage] = list(request.messages or ())

        if request.system_message not in existing_messages:
            existing_messages.insert(0, request.system_message)

        insertion_index = len(existing_messages)
        for idx, message in enumerate(existing_messages):
            if isinstance(message, SystemMessage):
                insertion_index = idx + 1
                break

        existing_messages.insert(insertion_index, skills_message)
        modified_request = request.override(messages=list(existing_messages))
        return await handler(modified_request)
