import logging
from os import environ
from typing import Dict, List, Optional

from langchain_community.tools import (
    DuckDuckGoSearchRun,
    ArxivQueryRun,
)
from langchain_community.tools.pubmed.tool import PubmedQueryRun
from langchain_core.tools import BaseTool

from language_model_gateway.configs.config_schema import AgentConfig
from language_model_gateway.gateway.tools.calculator_average_tool import (
    CalculatorAverageTool,
)
from language_model_gateway.gateway.tools.calculator_length_tool import (
    CalculatorLengthTool,
)
from language_model_gateway.gateway.tools.calculator_stddev_tool import (
    CalculatorStddevTool,
)
from language_model_gateway.gateway.tools.calculator_sum_tool import CalculatorSumTool
from language_model_gateway.gateway.tools.confluence_page_retriever import (
    ConfluencePageRetriever,
)
from language_model_gateway.gateway.tools.confluence_search_tool import (
    ConfluenceSearchTool,
)
from language_model_gateway.gateway.tools.current_time_tool import CurrentTimeTool
from language_model_gateway.gateway.tools.databricks_sql_tool import DatabricksSQLTool
from language_model_gateway.gateway.tools.er_diagram_generator_tool import (
    ERDiagramGeneratorTool,
)
from language_model_gateway.gateway.tools.fhir_graphql_schema_provider import (
    GraphqlSchemaProviderTool,
)
from language_model_gateway.gateway.tools.flow_chart_generator_tool import (
    FlowChartGeneratorTool,
)
from language_model_gateway.gateway.tools.github_pull_request_analyzer_tool import (
    GitHubPullRequestAnalyzerTool,
)
from language_model_gateway.gateway.tools.github_pull_request_diff_tool import (
    GitHubPullRequestDiffTool,
)
from language_model_gateway.gateway.tools.github_pull_request_retriever_tool import (
    GitHubPullRequestRetriever,
)
from language_model_gateway.gateway.tools.google_search_tool import GoogleSearchTool
from language_model_gateway.gateway.tools.graph_viz_diagram_generator_tool import (
    GraphVizDiagramGeneratorTool,
)
from language_model_gateway.gateway.tools.health_summary_generator_tool import (
    HealthSummaryGeneratorTool,
)
from language_model_gateway.gateway.tools.image_generator_tool import ImageGeneratorTool
from language_model_gateway.gateway.tools.jira_issue_retriever import (
    JiraIssueRetriever,
)
from language_model_gateway.gateway.tools.jira_issues_analyzer_tool import (
    JiraIssuesAnalyzerTool,
)
from language_model_gateway.gateway.tools.memories.memory_read_tool import (
    MemoryReadTool,
)
from language_model_gateway.gateway.tools.memories.memory_write_tool import (
    MemoryWriteTool,
)
from language_model_gateway.gateway.tools.network_topology_diagram_tool import (
    NetworkTopologyGeneratorTool,
)
from language_model_gateway.gateway.tools.pdf_extraction_tool import PDFExtractionTool
from language_model_gateway.gateway.tools.provider_search_tool import ProviderSearchTool
from language_model_gateway.gateway.tools.python_repl_tool import PythonReplTool
from language_model_gateway.gateway.tools.scraping_bee_web_scraper_tool import (
    ScrapingBeeWebScraperTool,
)
from language_model_gateway.gateway.tools.sequence_diagram_generator_tool import (
    SequenceDiagramGeneratorTool,
)
from language_model_gateway.gateway.tools.url_to_markdown_tool import URLToMarkdownTool
from language_model_gateway.gateway.tools.user_profile.get_user_profile_tool import (
    GetUserProfileTool,
)
from language_model_gateway.gateway.tools.user_profile.store_user_profile_tool import (
    StoreUserProfileTool,
)
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["AGENTS"])


class ToolProvider:
    def __init__(
        self,
        *,
        pdf_text_extractor: PDFExtractionTool,
        google_search_tool: GoogleSearchTool,
        url_to_markdown_tool: URLToMarkdownTool,
        current_time_tool: CurrentTimeTool,
        calculator_average_tool: CalculatorAverageTool,
        calculator_stddev_tool: CalculatorStddevTool,
        calculator_sum_tool: CalculatorSumTool,
        calculator_length_tool: CalculatorLengthTool,
        duckduckgo_search_tool: DuckDuckGoSearchRun,
        pubmed_query_tool: PubmedQueryRun,
        arxiv_query_tool: ArxivQueryRun,
        health_summary_generator_tool: HealthSummaryGeneratorTool,
        image_generator_tool_aws: ImageGeneratorTool,
        image_generator_tool_openai: ImageGeneratorTool,
        graph_viz_diagram_generator_tool: GraphVizDiagramGeneratorTool,
        sequence_diagram_generator_tool: SequenceDiagramGeneratorTool,
        flow_chart_generator_tool: FlowChartGeneratorTool,
        er_diagram_generator_tool: ERDiagramGeneratorTool,
        network_topology_generator_tool: NetworkTopologyGeneratorTool,
        scraping_bee_web_scraper_tool: ScrapingBeeWebScraperTool,
        provider_search_tool: ProviderSearchTool,
        github_pull_request_analyzer_tool: GitHubPullRequestAnalyzerTool,
        github_pull_request_diff_tool: GitHubPullRequestDiffTool,
        jira_issues_analyzer_tool: JiraIssuesAnalyzerTool,
        databricks_query_validator_tool: DatabricksSQLTool,
        fhir_graphql_schema_provider_tool: GraphqlSchemaProviderTool,
        jira_issue_retriever_tool: JiraIssueRetriever,
        github_pull_request_retriever_tool: GitHubPullRequestRetriever,
        confluence_search_tool: ConfluenceSearchTool,
        confluence_page_retriever_tool: ConfluencePageRetriever,
        get_user_profile_tool: GetUserProfileTool,
        store_user_profile_tool: StoreUserProfileTool,
        memory_writer_tool: MemoryWriteTool,
        memory_reader_tool: MemoryReadTool,
        python_repl_tool: PythonReplTool,
    ) -> None:
        web_search_tool: Optional[BaseTool] = None
        default_web_search_tool: str = environ.get(
            "DEFAULT_WEB_SEARCH_TOOL", "duckduckgo"
        )
        match default_web_search_tool:
            case "duckduckgo_search":
                web_search_tool = duckduckgo_search_tool
            case "google_search":
                web_search_tool = google_search_tool
            case _:
                raise ValueError(
                    f"Unknown default web search tool: {default_web_search_tool}"
                )

        self.tools: Dict[str, BaseTool] = {
            "current_date": current_time_tool,
            "calculator_average": calculator_average_tool,
            "calculator_stddev": calculator_stddev_tool,
            "calculator_sum": calculator_sum_tool,
            "calculator_length": calculator_length_tool,
            "web_search": web_search_tool,
            "pubmed": pubmed_query_tool,
            "google_search": google_search_tool,
            "duckduckgo_search": duckduckgo_search_tool,
            "python_repl": python_repl_tool,
            "get_web_page": url_to_markdown_tool,
            "arxiv_search": arxiv_query_tool,
            "health_summary_generator": health_summary_generator_tool,
            "image_generator": image_generator_tool_aws,
            "image_generator_openai": image_generator_tool_openai,
            "graph_viz_diagram_generator": graph_viz_diagram_generator_tool,
            "sequence_diagram_generator": sequence_diagram_generator_tool,
            "flow_chart_generator": flow_chart_generator_tool,
            "er_diagram_generator": er_diagram_generator_tool,
            "network_topology_generator": network_topology_generator_tool,
            "scraping_bee_web_scraper": scraping_bee_web_scraper_tool,
            "provider_search": provider_search_tool,
            "pdf_text_extractor": pdf_text_extractor,
            "github_pull_request_analyzer": github_pull_request_analyzer_tool,
            "github_pull_request_diff": github_pull_request_diff_tool,
            "jira_issues_analyzer": jira_issues_analyzer_tool,
            "databricks_query_validator": databricks_query_validator_tool,
            "fhir_graphql_schema_provider": fhir_graphql_schema_provider_tool,
            "jira_issue_retriever": jira_issue_retriever_tool,
            "github_pull_request_retriever": github_pull_request_retriever_tool,
            "confluence_search_tool": confluence_search_tool,
            "confluence_page_retriever": confluence_page_retriever_tool,
            "get_user_profile": get_user_profile_tool,
            "store_user_profile": store_user_profile_tool,
            "memory_writer": memory_writer_tool,
            "memory_reader": memory_reader_tool,
            # "sql_query": QuerySQLDataBaseTool(
            #     db=SQLDatabase(
            #         engine=Engine(
            #             url=environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///:memory:"),
            #             pool=Pool(),
            #             dialect=Dialect()
            #         )
            #     )
            # ),
        }

    def get_tool_by_name(
        self, *, tool: AgentConfig, headers: Dict[str, str]
    ) -> BaseTool:
        tool_names: List[str] = [name for name in self.tools.keys()]
        if tool.name in tool_names:
            return self.tools[tool.name]
        raise ValueError(
            f"Tool with name {tool.name} not found in available tools: {','.join(tool_names)}"
        )

    def has_tool(self, *, tool: AgentConfig) -> bool:
        tool_names: List[str] = [name for name in self.tools.keys()]
        return tool.name in tool_names

    def get_tools(
        self, *, tools: list[AgentConfig], headers: Dict[str, str]
    ) -> list[BaseTool]:
        return [
            self.get_tool_by_name(tool=tool, headers=headers)
            for tool in tools
            if self.has_tool(tool=tool)
        ]
