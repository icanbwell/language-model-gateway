import logging
import os
from typing import cast

from language_model_gateway.configs.config_reader.config_reader import ConfigReader
from language_model_gateway.container.simple_container import SimpleContainer
from language_model_gateway.gateway.auth.auth_manager import AuthManager
from language_model_gateway.gateway.auth.config.auth_config_reader import (
    AuthConfigReader,
)
from language_model_gateway.gateway.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from language_model_gateway.gateway.aws.aws_client_factory import AwsClientFactory
from language_model_gateway.gateway.converters.langgraph_to_openai_converter import (
    LangGraphToOpenAIConverter,
)
from language_model_gateway.gateway.file_managers.file_manager_factory import (
    FileManagerFactory,
)
from language_model_gateway.gateway.http.http_client_factory import HttpClientFactory
from language_model_gateway.gateway.image_generation.image_generator_factory import (
    ImageGeneratorFactory,
)
from language_model_gateway.gateway.managers.chat_completion_manager import (
    ChatCompletionManager,
)
from language_model_gateway.gateway.managers.image_generation_manager import (
    ImageGenerationManager,
)
from language_model_gateway.gateway.managers.model_manager import ModelManager
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.ocr.ocr_extractor_factory import OCRExtractorFactory
from language_model_gateway.gateway.providers.image_generation_provider import (
    ImageGenerationProvider,
)
from language_model_gateway.gateway.providers.langchain_chat_completions_provider import (
    LangChainCompletionsProvider,
)
from language_model_gateway.gateway.providers.openai_chat_completions_provider import (
    OpenAiChatCompletionsProvider,
)
from language_model_gateway.gateway.tools.mcp_tool_provider import MCPToolProvider
from language_model_gateway.gateway.tools.tool_provider import ToolProvider
from language_model_gateway.gateway.auth.token_reader import TokenReader
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from language_model_gateway.gateway.utilities.cache.mcp_tools_expiring_cache import (
    McpToolsMetadataExpiringCache,
)
from language_model_gateway.gateway.utilities.confluence.confluence_helper import (
    ConfluenceHelper,
)
from language_model_gateway.gateway.utilities.databricks.databricks_helper import (
    DatabricksHelper,
)
from language_model_gateway.gateway.utilities.environment_variables import (
    EnvironmentVariables,
)
from language_model_gateway.gateway.utilities.github.github_pull_request_helper import (
    GithubPullRequestHelper,
)
from language_model_gateway.gateway.utilities.jira.jira_issues_helper import (
    JiraIssueHelper,
)
from language_model_gateway.gateway.utilities.token_counter.token_counter import (
    TokenReducer,
    TOKEN_REDUCER_STRATEGY,
)

logger = logging.getLogger(__name__)


class ContainerFactory:
    # noinspection PyMethodMayBeStatic
    async def create_container_async(self) -> SimpleContainer:
        logger.info("Initializing DI container")

        container = SimpleContainer()

        # register services here

        # we want only one instance of the cache so we use singleton
        container.singleton(
            ConfigExpiringCache,
            lambda c: ConfigExpiringCache(
                ttl_seconds=(
                    int(os.environ["CONFIG_CACHE_TIMEOUT_SECONDS"])
                    if os.environ.get("CONFIG_CACHE_TIMEOUT_SECONDS")
                    else 60 * 60
                )
            ),
        )
        container.singleton(
            McpToolsMetadataExpiringCache,
            lambda c: McpToolsMetadataExpiringCache(
                ttl_seconds=(
                    int(os.environ["MCP_TOOLS_METADATA_CACHE_TIMEOUT_SECONDS"])
                    if os.environ.get("MCP_TOOLS_METADATA_CACHE_TIMEOUT_SECONDS")
                    else 60 * 60
                ),
                init_value={},
            ),
        )

        container.singleton(
            TokenReader,
            lambda c: TokenReader(
                algorithms=c.resolve(EnvironmentVariables).auth_algorithms,
                auth_config_reader=c.resolve(AuthConfigReader),
            ),
        )

        container.register(HttpClientFactory, lambda c: HttpClientFactory())

        container.register(
            OpenAiChatCompletionsProvider,
            lambda c: OpenAiChatCompletionsProvider(
                http_client_factory=c.resolve(HttpClientFactory)
            ),
        )
        container.register(ModelFactory, lambda c: ModelFactory())

        container.register(
            AwsClientFactory,
            lambda c: AwsClientFactory(),
        )

        container.register(
            ImageGeneratorFactory,
            lambda c: ImageGeneratorFactory(
                aws_client_factory=c.resolve(AwsClientFactory)
            ),
        )
        container.register(
            FileManagerFactory,
            lambda c: FileManagerFactory(
                aws_client_factory=c.resolve(AwsClientFactory),
            ),
        )

        container.register(
            LangGraphToOpenAIConverter, lambda c: LangGraphToOpenAIConverter()
        )

        container.register(
            OCRExtractorFactory,
            lambda c: OCRExtractorFactory(
                aws_client_factory=c.resolve(AwsClientFactory),
                file_manager_factory=c.resolve(FileManagerFactory),
            ),
        )

        container.register(
            EnvironmentVariables,
            lambda c: EnvironmentVariables(),
        )

        container.register(
            GithubPullRequestHelper,
            lambda c: GithubPullRequestHelper(
                org_name=c.resolve(EnvironmentVariables).github_org,
                access_token=c.resolve(EnvironmentVariables).github_token,
                http_client_factory=c.resolve(HttpClientFactory),
            ),
        )

        container.register(
            JiraIssueHelper,
            lambda c: JiraIssueHelper(
                http_client_factory=c.resolve(HttpClientFactory),
                jira_base_url=c.resolve(EnvironmentVariables).jira_base_url,
                access_token=c.resolve(EnvironmentVariables).jira_token,
                username=c.resolve(EnvironmentVariables).jira_username,
            ),
        )

        container.register(
            ConfluenceHelper,
            lambda c: ConfluenceHelper(
                http_client_factory=c.resolve(HttpClientFactory),
                confluence_base_url=c.resolve(EnvironmentVariables).jira_base_url,
                access_token=c.resolve(EnvironmentVariables).jira_token,
                username=c.resolve(EnvironmentVariables).jira_username,
            ),
        )

        container.register(
            DatabricksHelper,
            lambda c: DatabricksHelper(),
        )

        container.register(
            ToolProvider,
            lambda c: ToolProvider(
                image_generator_factory=c.resolve(ImageGeneratorFactory),
                file_manager_factory=c.resolve(FileManagerFactory),
                ocr_extractor_factory=c.resolve(OCRExtractorFactory),
                environment_variables=c.resolve(EnvironmentVariables),
                github_pull_request_helper=c.resolve(GithubPullRequestHelper),
                jira_issues_helper=c.resolve(JiraIssueHelper),
                confluence_helper=c.resolve(ConfluenceHelper),
                databricks_helper=c.resolve(DatabricksHelper),
            ),
        )

        container.register(
            MCPToolProvider,
            lambda c: MCPToolProvider(
                cache=c.resolve(McpToolsMetadataExpiringCache),
                auth_manager=c.resolve(AuthManager),
                environment_variables=c.resolve(EnvironmentVariables),
                token_reducer=c.resolve(TokenReducer),
            ),
        )

        container.register(
            LangChainCompletionsProvider,
            lambda c: LangChainCompletionsProvider(
                model_factory=c.resolve(ModelFactory),
                lang_graph_to_open_ai_converter=c.resolve(LangGraphToOpenAIConverter),
                tool_provider=c.resolve(ToolProvider),
                mcp_tool_provider=c.resolve(MCPToolProvider),
                token_reader=c.resolve(TokenReader),
                auth_manager=c.resolve(AuthManager),
                environment_variables=c.resolve(EnvironmentVariables),
                auth_config_reader=c.resolve(AuthConfigReader),
            ),
        )

        container.register(
            ConfigReader, lambda c: ConfigReader(cache=c.resolve(ConfigExpiringCache))
        )
        container.register(
            ChatCompletionManager,
            lambda c: ChatCompletionManager(
                open_ai_provider=c.resolve(OpenAiChatCompletionsProvider),
                langchain_provider=c.resolve(LangChainCompletionsProvider),
                config_reader=c.resolve(ConfigReader),
            ),
        )

        container.register(
            ImageGenerationProvider,
            lambda c: ImageGenerationProvider(
                image_generator_factory=c.resolve(ImageGeneratorFactory),
                file_manager_factory=c.resolve(FileManagerFactory),
            ),
        )
        container.register(
            ImageGenerationManager,
            lambda c: ImageGenerationManager(
                image_generation_provider=c.resolve(ImageGenerationProvider)
            ),
        )

        container.register(
            ModelManager, lambda c: ModelManager(config_reader=c.resolve(ConfigReader))
        )

        container.register(
            AuthManager,
            lambda c: AuthManager(
                environment_variables=c.resolve(EnvironmentVariables),
                token_exchange_manager=c.resolve(TokenExchangeManager),
                auth_config_reader=c.resolve(AuthConfigReader),
                token_reader=c.resolve(TokenReader),
            ),
        )

        container.register(
            TokenExchangeManager,
            lambda c: TokenExchangeManager(
                environment_variables=c.resolve(EnvironmentVariables),
                token_reader=c.resolve(TokenReader),
                auth_config_reader=c.resolve(AuthConfigReader),
            ),
        )

        container.register(
            AuthConfigReader,
            lambda c: AuthConfigReader(
                environment_variables=c.resolve(EnvironmentVariables)
            ),
        )

        # Validate truncation_strategy to ensure it matches allowed literals
        truncation_strategy_env = os.environ.get("TOKEN_TRUNCATION_STRATEGY", "smart")
        truncation_strategy: TOKEN_REDUCER_STRATEGY = cast(
            TOKEN_REDUCER_STRATEGY, truncation_strategy_env
        )
        container.register(
            TokenReducer,
            lambda c: TokenReducer(
                model=os.environ.get("DEFAULT_LLM_MODEL", "gpt-3.5-turbo"),
                truncation_strategy=truncation_strategy,
            ),
        )

        logger.info("DI container initialized")
        return container
