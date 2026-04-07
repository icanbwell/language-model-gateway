from abc import abstractmethod, ABCMeta
from typing import Dict

from starlette.responses import StreamingResponse, JSONResponse

from languagemodelcommon.configs.schemas.config_schema import ChatModelConfig
from oidcauthlib.auth.models.auth import AuthInformation
from languagemodelcommon.structures.openai.request.chat_request_wrapper import (
    ChatRequestWrapper,
)


class BaseChatCompletionsProvider(metaclass=ABCMeta):
    @abstractmethod
    async def chat_completions(
        self,
        *,
        model_config: ChatModelConfig,
        headers: Dict[str, str],
        chat_request_wrapper: ChatRequestWrapper,
        auth_information: AuthInformation,
    ) -> StreamingResponse | JSONResponse: ...
