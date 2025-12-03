import logging
import os
from typing import cast

from oidcauthlib.auth.config.auth_config_reader import AuthConfigReader
from oidcauthlib.auth.fastapi_auth_manager import FastAPIAuthManager
from oidcauthlib.auth.token_reader import TokenReader
from oidcauthlib.auth.well_known_configuration.well_known_configuration_manager import (
    WellKnownConfigurationManager,
)
from oidcauthlib.container.simple_container import SimpleContainer
from oidcauthlib.utilities.environment.environment_variables import EnvironmentVariables

from language_model_gateway.configs.config_reader.config_reader import ConfigReader
from language_model_gateway.gateway.auth.token_exchange.token_exchange_manager import (
    TokenExchangeManager,
)
from language_model_gateway.gateway.auth.token_storage_auth_manager import (
    TokenStorageAuthManager,
)
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
from language_model_gateway.gateway.managers.chat_completion_manager import (
    ChatCompletionManager,
)
from language_model_gateway.gateway.managers.image_generation_manager import (
    ImageGenerationManager,
)
from language_model_gateway.gateway.managers.model_manager import ModelManager
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
from language_model_gateway.gateway.tools.google_search_tool import GoogleSearchTool
from language_model_gateway.gateway.tools.pdf_extraction_tool import PDFExtractionTool
from language_model_gateway.gateway.tools.tool_provider import ToolProvider
from language_model_gateway.gateway.tools.url_to_markdown_tool import URLToMarkdownTool
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

from language_model_gateway.gateway.tools.current_time_tool import CurrentTimeTool
from language_model_gateway.gateway.tools.calculator_average_tool import (
    CalculatorAverageTool,
)
from language_model_gateway.gateway.tools.calculator_stddev_tool import (
    CalculatorStddevTool,
)
from language_model_gateway.gateway.tools.calculator_sum_tool import CalculatorSumTool
from language_model_gateway.gateway.tools.calculator_length_tool import (
    CalculatorLengthTool,
)
from langchain_community.tools import DuckDuckGoSearchRun, ArxivQueryRun
from langchain_community.tools.pubmed.tool import PubmedQueryRun
from language_model_gateway.gateway.tools.health_summary_generator_tool import (
    HealthSummaryGeneratorTool,
)
from language_model_gateway.gateway.tools.image_generator_tool import ImageGeneratorTool
from language_model_gateway.gateway.tools.graph_viz_diagram_generator_tool import (
    GraphVizDiagramGeneratorTool,
)
from language_model_gateway.gateway.tools.sequence_diagram_generator_tool import (
    SequenceDiagramGeneratorTool,
)
from language_model_gateway.gateway.tools.flow_chart_generator_tool import (
    FlowChartGeneratorTool,
)
from language_model_gateway.gateway.tools.er_diagram_generator_tool import (
    ERDiagramGeneratorTool,
)
from language_model_gateway.gateway.tools.network_topology_diagram_tool import (
    NetworkTopologyGeneratorTool,
)
from language_model_gateway.gateway.tools.scraping_bee_web_scraper_tool import (
    ScrapingBeeWebScraperTool,
)
from language_model_gateway.gateway.tools.provider_search_tool import ProviderSearchTool
from language_model_gateway.gateway.tools.github_pull_request_analyzer_tool import (
    GitHubPullRequestAnalyzerTool,
)
from language_model_gateway.gateway.tools.github_pull_request_diff_tool import (
    GitHubPullRequestDiffTool,
)
from language_model_gateway.gateway.tools.jira_issues_analyzer_tool import (
    JiraIssuesAnalyzerTool,
)
from language_model_gateway.gateway.tools.databricks_sql_tool import DatabricksSQLTool
from language_model_gateway.gateway.tools.fhir_graphql_schema_provider import (
    GraphqlSchemaProviderTool,
)
from language_model_gateway.gateway.tools.jira_issue_retriever import JiraIssueRetriever
from language_model_gateway.gateway.tools.github_pull_request_retriever_tool import (
    GitHubPullRequestRetriever,
)
from language_model_gateway.gateway.tools.confluence_search_tool import (
    ConfluenceSearchTool,
)
from language_model_gateway.gateway.tools.confluence_page_retriever import (
    ConfluencePageRetriever,
)
from language_model_gateway.gateway.tools.user_profile.get_user_profile_tool import (
    GetUserProfileTool,
)
from language_model_gateway.gateway.tools.user_profile.store_user_profile_tool import (
    StoreUserProfileTool,
)
from language_model_gateway.gateway.tools.memories.memory_write_tool import (
    MemoryWriteTool,
)
from language_model_gateway.gateway.tools.memories.memory_read_tool import (
    MemoryReadTool,
)
from language_model_gateway.gateway.tools.python_repl_tool import PythonReplTool

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
                environment_variables=c.resolve(EnvironmentVariables),
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

        # Register all ToolProvider tool dependencies as singletons (with required dependencies)
        # ==================== BEGIN TOOL SINGLETONS ====================
        # All singletons for ToolProvider tool dependencies are registered below.
        container.singleton(CurrentTimeTool, lambda c: CurrentTimeTool())
        container.singleton(CalculatorAverageTool, lambda c: CalculatorAverageTool())
        container.singleton(CalculatorStddevTool, lambda c: CalculatorStddevTool())
        container.singleton(CalculatorSumTool, lambda c: CalculatorSumTool())
        container.singleton(CalculatorLengthTool, lambda c: CalculatorLengthTool())
        container.singleton(DuckDuckGoSearchRun, lambda c: DuckDuckGoSearchRun())
        container.singleton(PubmedQueryRun, lambda c: PubmedQueryRun())
        container.singleton(ArxivQueryRun, lambda c: ArxivQueryRun())
        container.singleton(
            HealthSummaryGeneratorTool,
            lambda c: HealthSummaryGeneratorTool(
                file_manager_factory=c.resolve(FileManagerFactory)
            ),
        )
        # For image_generator_tool_aws and image_generator_tool_openai, you may want to distinguish by config or use two factories
        container.singleton(
            ImageGeneratorTool,
            lambda c: ImageGeneratorTool(
                image_generator_factory=c.resolve(ImageGeneratorFactory),
                file_manager_factory=c.resolve(FileManagerFactory),
                model_provider="aws",
            ),
        )
        container.singleton(
            GraphVizDiagramGeneratorTool,
            lambda c: GraphVizDiagramGeneratorTool(
                file_manager_factory=c.resolve(FileManagerFactory)
            ),
        )
        container.singleton(
            SequenceDiagramGeneratorTool,
            lambda c: SequenceDiagramGeneratorTool(
                file_manager_factory=c.resolve(FileManagerFactory)
            ),
        )
        container.singleton(
            FlowChartGeneratorTool,
            lambda c: FlowChartGeneratorTool(
                file_manager_factory=c.resolve(FileManagerFactory)
            ),
        )
        container.singleton(
            ERDiagramGeneratorTool,
            lambda c: ERDiagramGeneratorTool(
                file_manager_factory=c.resolve(FileManagerFactory)
            ),
        )
        container.singleton(
            NetworkTopologyGeneratorTool,
            lambda c: NetworkTopologyGeneratorTool(
                file_manager_factory=c.resolve(FileManagerFactory)
            ),
        )
        container.singleton(
            ScrapingBeeWebScraperTool,
            lambda c: ScrapingBeeWebScraperTool(
                api_key=os.environ.get("SCRAPING_BEE_API_KEY", "")
            ),
        )
        container.singleton(ProviderSearchTool, lambda c: ProviderSearchTool())
        container.singleton(
            GitHubPullRequestAnalyzerTool,
            lambda c: GitHubPullRequestAnalyzerTool(
                github_pull_request_helper=c.resolve(GithubPullRequestHelper)
            ),
        )
        container.singleton(
            GitHubPullRequestDiffTool,
            lambda c: GitHubPullRequestDiffTool(
                github_pull_request_helper=c.resolve(GithubPullRequestHelper)
            ),
        )
        container.singleton(
            JiraIssuesAnalyzerTool,
            lambda c: JiraIssuesAnalyzerTool(
                jira_issues_helper=c.resolve(JiraIssueHelper)
            ),
        )
        container.singleton(
            DatabricksSQLTool,
            lambda c: DatabricksSQLTool(databricks_helper=c.resolve(DatabricksHelper)),
        )
        container.singleton(
            GraphqlSchemaProviderTool, lambda c: GraphqlSchemaProviderTool()
        )
        container.singleton(
            JiraIssueRetriever,
            lambda c: JiraIssueRetriever(jira_issues_helper=c.resolve(JiraIssueHelper)),
        )
        container.singleton(
            GitHubPullRequestRetriever,
            lambda c: GitHubPullRequestRetriever(
                github_pull_request_helper=c.resolve(GithubPullRequestHelper)
            ),
        )
        container.singleton(
            ConfluenceSearchTool,
            lambda c: ConfluenceSearchTool(
                confluence_helper=c.resolve(ConfluenceHelper)
            ),
        )
        container.singleton(
            ConfluencePageRetriever,
            lambda c: ConfluencePageRetriever(
                confluence_helper=c.resolve(ConfluenceHelper)
            ),
        )
        container.singleton(GetUserProfileTool, lambda c: GetUserProfileTool())
        container.singleton(StoreUserProfileTool, lambda c: StoreUserProfileTool())
        container.singleton(MemoryWriteTool, lambda c: MemoryWriteTool())
        container.singleton(MemoryReadTool, lambda c: MemoryReadTool())
        container.singleton(PythonReplTool, lambda c: PythonReplTool())
        container.singleton(GoogleSearchTool, lambda c: GoogleSearchTool())
        container.singleton(URLToMarkdownTool, lambda c: URLToMarkdownTool())
        container.singleton(
            PDFExtractionTool,
            lambda c: PDFExtractionTool(
                ocr_extractor_factory=c.resolve(OCRExtractorFactory),
            ),
        )
        # ==================== END TOOL SINGLETONS ====================

        # Update ToolProvider registration to inject all dependencies
        container.singleton(
            ToolProvider,
            lambda c: ToolProvider(
                pdf_text_extractor=c.resolve(PDFExtractionTool),
                google_search_tool=c.resolve(GoogleSearchTool),
                url_to_markdown_tool=c.resolve(URLToMarkdownTool),
                current_time_tool=c.resolve(CurrentTimeTool),
                calculator_average_tool=c.resolve(CalculatorAverageTool),
                calculator_stddev_tool=c.resolve(CalculatorStddevTool),
                calculator_sum_tool=c.resolve(CalculatorSumTool),
                calculator_length_tool=c.resolve(CalculatorLengthTool),
                duckduckgo_search_tool=c.resolve(DuckDuckGoSearchRun),
                pubmed_query_tool=c.resolve(PubmedQueryRun),
                arxiv_query_tool=c.resolve(ArxivQueryRun),
                health_summary_generator_tool=c.resolve(HealthSummaryGeneratorTool),
                image_generator_tool_aws=c.resolve(ImageGeneratorTool),
                image_generator_tool_openai=c.resolve(ImageGeneratorTool),
                graph_viz_diagram_generator_tool=c.resolve(
                    GraphVizDiagramGeneratorTool
                ),
                sequence_diagram_generator_tool=c.resolve(SequenceDiagramGeneratorTool),
                flow_chart_generator_tool=c.resolve(FlowChartGeneratorTool),
                er_diagram_generator_tool=c.resolve(ERDiagramGeneratorTool),
                network_topology_generator_tool=c.resolve(NetworkTopologyGeneratorTool),
                scraping_bee_web_scraper_tool=c.resolve(ScrapingBeeWebScraperTool),
                provider_search_tool=c.resolve(ProviderSearchTool),
                github_pull_request_analyzer_tool=c.resolve(
                    GitHubPullRequestAnalyzerTool
                ),
                github_pull_request_diff_tool=c.resolve(GitHubPullRequestDiffTool),
                jira_issues_analyzer_tool=c.resolve(JiraIssuesAnalyzerTool),
                databricks_query_validator_tool=c.resolve(DatabricksSQLTool),
                fhir_graphql_schema_provider_tool=c.resolve(GraphqlSchemaProviderTool),
                jira_issue_retriever_tool=c.resolve(JiraIssueRetriever),
                github_pull_request_retriever_tool=c.resolve(
                    GitHubPullRequestRetriever
                ),
                confluence_search_tool=c.resolve(ConfluenceSearchTool),
                confluence_page_retriever_tool=c.resolve(ConfluencePageRetriever),
                get_user_profile_tool=c.resolve(GetUserProfileTool),
                store_user_profile_tool=c.resolve(StoreUserProfileTool),
                memory_writer_tool=c.resolve(MemoryWriteTool),
                memory_reader_tool=c.resolve(MemoryReadTool),
                python_repl_tool=c.resolve(PythonReplTool),
            ),
        )

        container.singleton(
            ConfigReader, lambda c: ConfigReader(cache=c.resolve(ConfigExpiringCache))
        )
        container.singleton(
            ChatCompletionManager,
            lambda c: ChatCompletionManager(
                open_ai_provider=c.resolve(OpenAiChatCompletionsProvider),
                langchain_provider=c.resolve(LangChainCompletionsProvider),
                config_reader=c.resolve(ConfigReader),
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

        logger.info("DI container initialized")
        return container
