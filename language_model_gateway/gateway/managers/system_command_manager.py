import logging

from langchain_core.messages import AIMessage
from starlette.responses import StreamingResponse, JSONResponse

from langchain_ai_skills_framework.loaders.skill_loader_protocol import (
    SkillLoaderProtocol,
)
from langchain_ai_skills_framework.loaders.skill_sync import SkillSync
from langchain_ai_skills_framework.startup import reload_plugins
from languagemodelcommon.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from languagemodelcommon.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])


class SystemCommandManager:
    def __init__(
        self,
        *,
        token_exchange_manager: TokenExchangeManager,
        environment_variables: LanguageModelGatewayEnvironmentVariables,
        skill_loader: SkillLoaderProtocol,
        skill_sync: SkillSync,
    ) -> None:
        self.token_exchange_manager = token_exchange_manager
        if self.token_exchange_manager is None:
            raise ValueError("token_exchange_manager must not be None")
        if not isinstance(self.token_exchange_manager, TokenExchangeManager):
            raise TypeError(
                "token_exchange_manager must be an instance of TokenExchangeManager"
            )

        self.environment_variables = environment_variables
        if self.environment_variables is None:
            raise ValueError("environment_variables must not be None")
        if not isinstance(
            self.environment_variables, LanguageModelGatewayEnvironmentVariables
        ):
            raise TypeError(
                "environment_variables must be an instance of LanguageModelGatewayEnvironmentVariables"
            )

        self._skill_loader = skill_loader
        self._skill_sync = skill_sync

    async def run_system_commands(
        self,
        *,
        request_id: str,
        chat_request_wrapper: ChatRequestWrapper,
        referring_subject: str,
        auth_provider: str | None,
    ) -> StreamingResponse | JSONResponse | None:
        raw_content = chat_request_wrapper.messages[-1].content
        last_message_content: str | None = (
            raw_content if isinstance(raw_content, str) else None
        )

        if last_message_content is not None:
            system_commands: list[str] = self.environment_variables.system_commands
            if last_message_content.lower() in system_commands:
                response_text: str = (
                    f"System command '{last_message_content}' received and processed."
                )
                match last_message_content.lower():
                    case "clear tokens":
                        # delete any existing tokens with same referring_subject and auth_provider
                        await self.token_exchange_manager.delete_all_tokens_async(
                            referring_subject=referring_subject,
                        )
                    case "reload_plugins":
                        summary = await reload_plugins(
                            skill_loader=self._skill_loader,
                            skill_sync=self._skill_sync,
                        )
                        response_text = f"Plugins reloaded from GitHub and synced to MongoDB. {summary}"
                    case _:
                        raise ValueError(
                            f"Unrecognized system command: {last_message_content}"
                        )

                logger.info(f"System command received: {last_message_content}")
                return chat_request_wrapper.write_response(
                    request_id=request_id,
                    response_messages=[AIMessage(content=response_text)],
                )
        return None
