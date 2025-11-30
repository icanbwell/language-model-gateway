from typing import List, Optional, Dict, Literal

from pydantic import BaseModel


class PromptConfig(BaseModel):
    """Prompt configuration"""

    role: str = "system"
    """The role of the prompt"""

    content: str | None = None
    """The content of the prompt"""

    hub_id: str | None = None
    """The hub id of the prompt"""

    cache: bool | None = None
    """Whether to cache the prompt"""


class ModelParameterConfig(BaseModel):
    """Model parameter configuration"""

    key: str
    """The key of the parameter"""

    value: float | str | int | bool
    """The value of the parameter"""


class FewShotExampleConfig(BaseModel):
    """Few shot example configuration"""

    input: str
    """The input"""

    output: str
    """The output"""


class HeaderConfig(BaseModel):
    """Header configuration"""

    key: str
    """The key of the header"""

    value: str
    """The value of the header"""


class AgentParameterConfig(BaseModel):
    """Tool parameter configuration"""

    key: str
    """The key of the parameter"""

    value: str
    """The value of the parameter"""


class AgentConfig(BaseModel):
    """Tool configuration"""

    name: str
    """The name of the tool"""

    parameters: List[AgentParameterConfig] | None = None
    """The parameters for the tool"""

    url: str | None = None
    """The MCP (Model Context Protocol) URL to access the tool"""

    headers: Dict[str, str] | None = None
    """The headers to pass to the MCP tool"""

    tools: str | None = None
    """The names of the tool to use in the MCP call.  If none is provided then all tools at the URL will be used. Separate multiple tool names with commas."""

    auth: Literal["None", "jwt_token", "oauth"] | None = None
    """The authentication method to use when calling the tool"""

    auth_optional: bool | None = None
    """Whether authentication is optional when calling the tool.  Default is None."""

    auth_providers: List[str] | None = None
    """The auth providers for the authentication. If multiple are provided then the tool accepts ANY of those auth providers.  If auth is needed, we will use the first auth provider."""

    issuers: List[str] | None = None
    """
    The issuers for the authentication.
    If multiple are provided then the tool accepts ANY of those issuers.
    If auth is needed, we will use the first issuer.
    If none is provided then we use the default issuer from the OIDC provider.
    """


class ModelConfig(BaseModel):
    """Model configuration"""

    provider: str
    """The provider of the model"""

    model: str
    """The model to use"""


class ChatModelConfig(BaseModel):
    """Model configuration for chat models"""

    id: str
    """The unique identifier for the model"""

    name: str
    """The name of the model"""

    description: str
    """A description of the model"""

    type: str = "langchain"
    """The type of model"""

    owner: Optional[str] = None
    """The owner of the model"""

    url: str | None = None
    """The URL to access the model"""

    disabled: bool | None = None

    model: ModelConfig | None = None
    """The model configuration"""

    system_prompts: List[PromptConfig] | None = None
    """The system prompts for the model"""

    model_parameters: List[ModelParameterConfig] | None = None
    """The model parameters"""

    headers: List[HeaderConfig] | None = None
    """The headers to pass to url when calling the model"""

    tools: List[AgentConfig] | None = None
    """The tools to use with the model"""

    agents: List[AgentConfig] | None = None
    """The tools to use with the model"""

    example_prompts: List[PromptConfig] | None = None
    """Example prompts for the model"""

    def get_agents(self) -> List[AgentConfig]:
        """Get the agents for the model"""
        return self.agents or self.tools or []
