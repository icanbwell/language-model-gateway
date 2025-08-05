import logging
import os

from language_model_gateway.configs.config_reader.config_reader import ConfigReader
from language_model_gateway.container.simple_container import SimpleContainer
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
from language_model_gateway.gateway.utilities.auth.token_verifier import TokenVerifier
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
            TokenVerifier,
            lambda c: TokenVerifier(
                jwks_uri=c.resolve(EnvironmentVariables).auth_jwks_uri,
                issuer=c.resolve(EnvironmentVariables).auth_issuer,
                audience=c.resolve(EnvironmentVariables).auth_audience,
                algorithms=c.resolve(EnvironmentVariables).auth_algorithms,
                well_known_uri=c.resolve(EnvironmentVariables).auth_well_known_uri,
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
            ),
        )

        container.register(
            LangChainCompletionsProvider,
            lambda c: LangChainCompletionsProvider(
                model_factory=c.resolve(ModelFactory),
                lang_graph_to_open_ai_converter=c.resolve(LangGraphToOpenAIConverter),
                tool_provider=c.resolve(ToolProvider),
                mcp_tool_provider=c.resolve(MCPToolProvider),
                token_verifier=c.resolve(TokenVerifier),
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
        logger.info("DI container initialized")
        return container
