from typing import Optional

from langchain_core.messages.ai import UsageMetadata
from langgraph.prebuilt.chat_agent_executor import AgentStatePydantic


class MyMessagesState(AgentStatePydantic):
    usage_metadata: Optional[UsageMetadata]
    auth_token: Optional[str]
