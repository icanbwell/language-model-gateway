from typing import Dict, Any, List

from openai.types.chat import ChatCompletion


class ChatCompletionWriter:
    """
    Writer class for chat completions endpoints
    """
    def write(self, *, mode: str, content: Dict[str, Any] | List[Dict[str, Any]] | str) -> ChatCompletion:
        chat_response: ChatCompletion = ChatCompletion(
            id=request_id,
            model=model,
            choices=choices,
            usage=total_usage_metadata,
            created=int(time.time()),
            object="chat.completion",
        )


