import logging
import os
from typing import cast

from oidcauthlib.auth.auth_manager import AuthManager
from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.fastapi_auth_manager import FastAPIAuthManager
from oidcauthlib.auth.token_reader import TokenReader
from oidcauthlib.auth.well_known_configuration.well_known_configuration_manager import (
    WellKnownConfigurationManager,
)
from oidcauthlib.container.simple_container import SimpleContainer
from oidcauthlib.utilities.environment.oidc_environment_variables import (
    OidcEnvironmentVariables,
)

from language_model_gateway.configs.config_reader.config_reader import ConfigReader
from language_model_gateway.gateway.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from language_model_gateway.gateway.auth.token_storage_auth_manager import (
    TokenStorageAuthManager,
)
from language_model_gateway.gateway.auth.tools.tool_auth_manager import ToolAuthManager
from language_model_gateway.gateway.aws.aws_client_factory import AwsClientFactory
from language_model_gateway.gateway.converters.langgraph_to_openai_converter import (
    LangGraphToOpenAIConverter,
)
from language_model_gateway.gateway.converters.streaming_manager import (
    LangGraphStreamingManager,
)
from language_model_gateway.gateway.file_managers.file_manager_factory import (
    FileManagerFactory,
)
from language_model_gateway.gateway.http.http_client_factory import HttpClientFactory
from language_model_gateway.gateway.image_generation.image_generator_factory import (
    ImageGeneratorFactory,
)
from language_model_gateway.gateway.managers.app_login_manager import AppLoginManager
from language_model_gateway.gateway.managers.chat_completion_manager import (
    ChatCompletionManager,
)
from language_model_gateway.gateway.managers.image_generation_manager import (
    ImageGenerationManager,
)
from language_model_gateway.gateway.managers.model_manager import ModelManager
from language_model_gateway.gateway.managers.system_command_manager import (
    SystemCommandManager,
)
from language_model_gateway.gateway.managers.token_submission_manager import (
    TokenSubmissionManager,
)
from language_model_gateway.gateway.mcp.interceptors.tracing import (
    TracingMcpCallInterceptor,
)
from language_model_gateway.gateway.mcp.interceptors.truncation import (
    TruncationMcpCallInterceptor,
)
from language_model_gateway.gateway.models.model_factory import ModelFactory
from language_model_gateway.gateway.ocr.ocr_extractor_factory import OCRExtractorFactory
from language_model_gateway.gateway.persistence.persistence_factory import (
    PersistenceFactory,
)
from language_model_gateway.gateway.providers.image_generation_provider import (
    ImageGenerationProvider,
)
from language_model_gateway.gateway.providers.langchain_chat_completions_provider import (
    LangChainCompletionsProvider,
)
from language_model_gateway.gateway.providers.openai_chat_completions_provider import (
    OpenAiChatCompletionsProvider,
)
from language_model_gateway.gateway.mcp.mcp_tool_provider import MCPToolProvider
from language_model_gateway.gateway.providers.pass_through_chat_completions_provider import (
    PassThroughChatCompletionsProvider,
)
from language_model_gateway.gateway.providers.pass_through_token_manager import (
    PassThroughTokenManager,
)
from language_model_gateway.gateway.tools.tool_provider import ToolProvider
from language_model_gateway.gateway.utilities.cache.config_expiring_cache import (
    ConfigExpiringCache,
)
from language_model_gateway.gateway.utilities.confluence.confluence_helper import (
    ConfluenceHelper,
)
from language_model_gateway.gateway.utilities.databricks.databricks_helper import (
    DatabricksHelper,
)
from language_model_gateway.gateway.utilities.language_model_gateway_environment_variables import (
    LanguageModelGatewayEnvironmentVariables,
)
from language_model_gateway.gateway.utilities.github.github_pull_request_helper import (
    GithubPullRequestHelper,
)
from language_model_gateway.gateway.utilities.jira.jira_issues_helper import (
    JiraIssueHelper,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS
from language_model_gateway.gateway.utilities.token_reducer.token_reducer import (
    TokenReducer,
    TOKEN_REDUCER_STRATEGY,
)
from oidcauthlib.container.oidc_authlib_container_factory import (
    OidcAuthLibContainerFactory,
)

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["INITIALIZATION"])


class LanguageModelGatewayContainerFactory:
    @classmethod
    def create_container(cls, *, source: str) -> SimpleContainer:
        logger.info("Initializing DI container")

        container = SimpleContainer(source=source)

        container = OidcAuthLibContainerFactory().register_services_in_container(
            container=container
        )

        # Register our own FastAPIManager so we can save the token
        # Must be done AFTER the OidcContainerFactory to override the registration
        container.singleton(
            FastAPIAuthManager,
            lambda c: TokenStorageAuthManager(
                environment_variables=c.resolve(OidcEnvironmentVariables),
                auth_config_reader=c.resolve(AuthConfigReader),
                token_reader=c.resolve(TokenReader),
                token_exchange_manager=c.resolve(TokenExchangeManager),
                well_known_configuration_manager=c.resolve(
                    WellKnownConfigurationManager
                ),
            ),
        )

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

        container.singleton(HttpClientFactory, lambda c: HttpClientFactory())

        container.singleton(
            OpenAiChatCompletionsProvider,
            lambda c: OpenAiChatCompletionsProvider(
                http_client_factory=c.resolve(HttpClientFactory)
            ),
        )
        container.singleton(ModelFactory, lambda c: ModelFactory())

        container.singleton(
            AwsClientFactory,
            lambda c: AwsClientFactory(),
        )

        container.singleton(
            ImageGeneratorFactory,
            lambda c: ImageGeneratorFactory(
                aws_client_factory=c.resolve(AwsClientFactory)
            ),
        )
        container.singleton(
            FileManagerFactory,
            lambda c: FileManagerFactory(
                aws_client_factory=c.resolve(AwsClientFactory),
            ),
        )

        container.singleton(
            LangGraphStreamingManager,
            lambda c: LangGraphStreamingManager(
                token_reducer=c.resolve(TokenReducer),
                file_manager_factory=c.resolve(FileManagerFactory),
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ),
            ),
        )

        container.singleton(
            LangGraphToOpenAIConverter,
            lambda c: LangGraphToOpenAIConverter(
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ),
                token_reducer=c.resolve(TokenReducer),
                streaming_manager=c.resolve(LangGraphStreamingManager),
            ),
        )

        container.singleton(
            OCRExtractorFactory,
            lambda c: OCRExtractorFactory(
                aws_client_factory=c.resolve(AwsClientFactory),
                file_manager_factory=c.resolve(FileManagerFactory),
            ),
        )

        container.singleton(
            LanguageModelGatewayEnvironmentVariables,
            lambda c: LanguageModelGatewayEnvironmentVariables(),
        )

        container.singleton(
            GithubPullRequestHelper,
            lambda c: GithubPullRequestHelper(
                org_name=c.resolve(LanguageModelGatewayEnvironmentVariables).github_org,
                access_token=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ).github_token,
                http_client_factory=c.resolve(HttpClientFactory),
            ),
        )

        container.singleton(
            JiraIssueHelper,
            lambda c: JiraIssueHelper(
                http_client_factory=c.resolve(HttpClientFactory),
                jira_base_url=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ).jira_base_url,
                access_token=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ).jira_token,
                username=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ).jira_username,
            ),
        )

        container.singleton(
            ConfluenceHelper,
            lambda c: ConfluenceHelper(
                http_client_factory=c.resolve(HttpClientFactory),
                confluence_base_url=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ).jira_base_url,
                access_token=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ).jira_token,
                username=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ).jira_username,
            ),
        )

        container.singleton(
            DatabricksHelper,
            lambda c: DatabricksHelper(),
        )

        container.singleton(
            ToolProvider,
            lambda c: ToolProvider(
                image_generator_factory=c.resolve(ImageGeneratorFactory),
                file_manager_factory=c.resolve(FileManagerFactory),
                ocr_extractor_factory=c.resolve(OCRExtractorFactory),
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ),
                github_pull_request_helper=c.resolve(GithubPullRequestHelper),
                jira_issues_helper=c.resolve(JiraIssueHelper),
                confluence_helper=c.resolve(ConfluenceHelper),
                databricks_helper=c.resolve(DatabricksHelper),
            ),
        )

        container.singleton(
            ToolAuthManager,
            lambda c: ToolAuthManager(
                auth_manager=c.resolve(AuthManager),
                token_exchange_manager=c.resolve(TokenExchangeManager),
                auth_config_reader=c.resolve(AuthConfigReader),
            ),
        )

        container.singleton(
            PassThroughTokenManager,
            lambda c: PassThroughTokenManager(
                auth_manager=c.resolve(AuthManager),
                auth_config_reader=c.resolve(AuthConfigReader),
                tool_auth_manager=c.resolve(ToolAuthManager),
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ),
            ),
        )

        container.singleton(
            TruncationMcpCallInterceptor,
            lambda c: TruncationMcpCallInterceptor(
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ),
                token_reducer=c.resolve(TokenReducer),
            ),
        )

        container.singleton(
            TracingMcpCallInterceptor,
            lambda c: TracingMcpCallInterceptor(
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ),
            ),
        )

        container.singleton(
            MCPToolProvider,
            lambda c: MCPToolProvider(
                tool_auth_manager=c.resolve(ToolAuthManager),
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ),
                token_reducer=c.resolve(TokenReducer),
                tracing_interceptor=c.resolve(TracingMcpCallInterceptor),
                truncation_interceptor=c.resolve(TruncationMcpCallInterceptor),
            ),
        )

        container.singleton(
            LangChainCompletionsProvider,
            lambda c: LangChainCompletionsProvider(
                model_factory=c.resolve(ModelFactory),
                lang_graph_to_open_ai_converter=c.resolve(LangGraphToOpenAIConverter),
                tool_provider=c.resolve(ToolProvider),
                mcp_tool_provider=c.resolve(MCPToolProvider),
                token_reader=c.resolve(TokenReader),
                pass_through_token_manager=c.resolve(PassThroughTokenManager),
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ),
                persistence_factory=c.resolve(PersistenceFactory),
            ),
        )

        container.singleton(
            ConfigReader, lambda c: ConfigReader(cache=c.resolve(ConfigExpiringCache))
        )

        container.singleton(
            SystemCommandManager,
            lambda c: SystemCommandManager(
                token_exchange_manager=c.resolve(TokenExchangeManager),
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ),
            ),
        )
        container.singleton(
            ChatCompletionManager,
            lambda c: ChatCompletionManager(
                open_ai_provider=c.resolve(OpenAiChatCompletionsProvider),
                langchain_provider=c.resolve(LangChainCompletionsProvider),
                pass_through_provider=c.resolve(PassThroughChatCompletionsProvider),
                config_reader=c.resolve(ConfigReader),
                system_command_manager=c.resolve(SystemCommandManager),
            ),
        )
        container.singleton(
            AppLoginManager,
            lambda c: AppLoginManager(
                http_client_factory=c.resolve(HttpClientFactory),
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ),
                auth_config_reader=c.resolve(AuthConfigReader),
                token_exchange_manager=c.resolve(TokenExchangeManager),
            ),
        )
        container.singleton(
            TokenSubmissionManager,
            lambda c: TokenSubmissionManager(
                token_reader=c.resolve(TokenReader),
                token_exchange_manager=c.resolve(TokenExchangeManager),
                auth_config_reader=c.resolve(AuthConfigReader),
            ),
        )

        container.singleton(
            ImageGenerationProvider,
            lambda c: ImageGenerationProvider(
                image_generator_factory=c.resolve(ImageGeneratorFactory),
                file_manager_factory=c.resolve(FileManagerFactory),
            ),
        )
        container.singleton(
            ImageGenerationManager,
            lambda c: ImageGenerationManager(
                image_generation_provider=c.resolve(ImageGenerationProvider)
            ),
        )

        container.singleton(
            ModelManager, lambda c: ModelManager(config_reader=c.resolve(ConfigReader))
        )

        container.singleton(
            TokenExchangeManager,
            lambda c: TokenExchangeManager(
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                ),
                token_reader=c.resolve(TokenReader),
                auth_config_reader=c.resolve(AuthConfigReader),
            ),
        )

        # Validate truncation_strategy to ensure it matches allowed literals
        truncation_strategy_env = os.environ.get("TOKEN_TRUNCATION_STRATEGY", "smart")
        truncation_strategy: TOKEN_REDUCER_STRATEGY = cast(
            TOKEN_REDUCER_STRATEGY, truncation_strategy_env
        )
        container.singleton(
            TokenReducer,
            lambda c: TokenReducer(
                model=os.environ.get("DEFAULT_LLM_MODEL", "gpt-3.5-turbo"),
                truncation_strategy=truncation_strategy,
            ),
        )

        container.singleton(
            PersistenceFactory,
            lambda c: PersistenceFactory(
                environment_variables=c.resolve(
                    LanguageModelGatewayEnvironmentVariables
                )
            ),
        )

        container.singleton(
            PassThroughChatCompletionsProvider,
            lambda c: PassThroughChatCompletionsProvider(
                pass_through_token_manager=c.resolve(PassThroughTokenManager),
            ),
        )

        logger.info("DI container initialized")
        return container
