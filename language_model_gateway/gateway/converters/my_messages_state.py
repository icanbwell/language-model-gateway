from typing import Optional

from langchain_core.messages.ai import UsageMetadata
from langgraph.prebuilt.chat_agent_executor import AgentStatePydantic


class MyMessagesState(AgentStatePydantic):
    usage_metadata: Optional[UsageMetadata]
    """ Metadata about the usage of the agent, if available."""

    auth_token: Optional[str]
    """ The authentication token associated with the request, if available."""

    # https://langchain-ai.github.io/langgraph/how-tos/memory/add-memory/#read-short-term
    user_id: Optional[str]
    """ The user ID associated with the request, if available."""

    conversation_thread_id: Optional[str]
    """ The conversation thread identifier for the request, if applicable."""
