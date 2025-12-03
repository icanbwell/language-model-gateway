from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field


class PromptConfig(BaseModel):
    """Prompt configuration"""

    role: str = Field("system", description="The role of the prompt")
    content: str | None = Field(default=None, description="The content of the prompt")
    hub_id: str | None = Field(default=None, description="The hub id of the prompt")
    cache: bool | None = Field(default=None, description="Whether to cache the prompt")


class ModelParameterConfig(BaseModel):
    """Model parameter configuration"""

    key: str = Field(..., description="The key of the parameter")
    value: float | str | int | bool = Field(
        ..., description="The value of the parameter"
    )


class FewShotExampleConfig(BaseModel):
    """Few shot example configuration"""

    input: str = Field(..., description="The input")
    output: str = Field(..., description="The output")


class HeaderConfig(BaseModel):
    """Header configuration"""

    key: str = Field(..., description="The key of the header")
    value: str = Field(..., description="The value of the header")


class AgentParameterConfig(BaseModel):
    """Tool parameter configuration"""

    key: str = Field(..., description="The key of the parameter")
    value: str = Field(..., description="The value of the parameter")


class AgentConfig(BaseModel):
    """Tool configuration"""

    name: str = Field(..., description="The name of the tool")
    parameters: List[AgentParameterConfig] | None = Field(
        default=None, description="The parameters for the tool"
    )
    url: str | None = Field(
        default=None,
        description="The MCP (Model Context Protocol) URL to access the tool",
    )
    headers: Dict[str, str] | None = Field(
        default=None, description="The headers to pass to the MCP tool"
    )
    tools: str | None = Field(
        default=None,
        description="The names of the tool to use in the MCP call.  If none is provided then all tools at the URL will be used. Separate multiple tool names with commas.",
    )
    auth: Literal["None", "jwt_token", "oauth", "headers"] | None = Field(
        default=None,
        description="The authentication method to use when calling the tool",
    )
    auth_optional: bool | None = Field(
        default=None,
        description="Whether authentication is optional when calling the tool.  Default is None.",
    )
    auth_providers: List[str] | None = Field(
        default=None,
        description="The auth providers for the authentication. If multiple are provided then the tool accepts ANY of those auth providers.  If auth is needed, we will use the first auth provider.",
    )
    issuers: List[str] | None = Field(
        default=None,
        description="The issuers for the authentication. If multiple are provided then the tool accepts ANY of those issuers. If auth is needed, we will use the first issuer. If none is provided then we use the default issuer from the OIDC provider.",
    )


class ModelConfig(BaseModel):
    """Model configuration"""

    provider: str = Field(..., description="The provider of the model")
    model: Optional[str] = Field(default=None, description="The model to use")


class ChatModelConfig(BaseModel):
    """Model configuration for chat models"""

    id: str = Field(..., description="The unique identifier for the model")
    name: str = Field(..., description="The name of the model")
    description: str = Field(..., description="A description of the model")
    type: str = Field(default="langchain", description="The type of model")
    owner: Optional[str] = Field(default=None, description="The owner of the model")
    url: str | None = Field(default=None, description="The URL to access the model")
    disabled: bool | None = Field(
        default=None, description="Whether the model is disabled"
    )
    model: ModelConfig | None = Field(
        default=None, description="The model configuration"
    )
    system_prompts: List[PromptConfig] | None = Field(
        default=None, description="The system prompts for the model"
    )
    model_parameters: List[ModelParameterConfig] | None = Field(
        default=None, description="The model parameters"
    )
    headers: List[HeaderConfig] | None = Field(
        default=None, description="The headers to pass to url when calling the model"
    )
    tools: List[AgentConfig] | None = Field(
        default=None, description="The tools to use with the model"
    )
    agents: List[AgentConfig] | None = Field(
        default=None, description="The tools to use with the model"
    )
    example_prompts: List[PromptConfig] | None = Field(
        default=None, description="Example prompts for the model"
    )

    def get_agents(self) -> List[AgentConfig]:
        """Get the agents for the model"""
        return self.agents or self.tools or []
