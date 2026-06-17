import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from languagemodelcommon.configs.config_reader.config_reader import ConfigReader
from languagemodelcommon.configs.schemas.config_schema import (
    ChatModelConfig,
    AgentConfig,
)
from languagemodelcommon.mcp.mcp_tool_provider import MCPToolProvider
from languagemodelcommon.mcp.tool_catalog import ToolCatalog
from languagemodelcommon.models.model_factory import ModelFactory
from language_model_gateway.gateway.tools.tool_provider import ToolProvider
from language_model_gateway.gateway.utilities.logger.log_levels import SRC_LOG_LEVELS

logger = logging.getLogger(__name__)
logger.setLevel(SRC_LOG_LEVELS["LLM"])

_MODEL_CACHE_TTL_SECONDS = 300


@dataclass
class CachedModelResources:
    """Cached per-model resources that don't change between requests."""

    catalog: ToolCatalog
    llm: BaseChatModel
    base_tools: list[BaseTool]
    created_at: float = field(default_factory=time.monotonic)

    def is_expired(self) -> bool:
        return (time.monotonic() - self.created_at) > _MODEL_CACHE_TTL_SECONDS


class ModelResourceCacheManager:
    """Manages lifecycle and caching of per-model resources (LLM, ToolCatalog, base tools).

    Separated from the chat completions provider so that startup/refresh
    orchestration can interact with caching without coupling to provider internals.
    """

    def __init__(
        self,
        *,
        model_factory: ModelFactory,
        tool_provider: ToolProvider,
        mcp_tool_provider: MCPToolProvider,
    ) -> None:
        self._model_factory = model_factory
        self._tool_provider = tool_provider
        self._mcp_tool_provider = mcp_tool_provider
        self._cache: Dict[str, CachedModelResources] = {}
        self._lock = threading.Lock()

    def get_or_create(
        self,
        *,
        model_config: ChatModelConfig,
    ) -> CachedModelResources:
        """Return cached LLM, ToolCatalog, and base tools for a model.

        Creates them on first access or when the cache entry has expired.
        """
        cache_key = model_config.name
        with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None and not cached.is_expired():
                return cached

        llm: BaseChatModel = self._model_factory.get_model(
            chat_model_config=model_config
        )

        agents = model_config.get_agents()
        base_tools: list[BaseTool] = (
            self._tool_provider.get_tools(tools=[t for t in agents], headers={})
            if agents is not None
            else []
        )

        mcp_tool_configs: list[AgentConfig] = (
            [t for t in agents] if agents is not None else []
        )
        catalog = self._mcp_tool_provider.discover_tool_catalog(
            tools=mcp_tool_configs,
        )

        resources = CachedModelResources(
            catalog=catalog,
            llm=llm,
            base_tools=base_tools,
        )
        with self._lock:
            self._cache[cache_key] = resources
        logger.info(
            "Cached model resources for '%s' (llm + catalog with %d servers + %d base tools)",
            cache_key,
            len(mcp_tool_configs),
            len(base_tools),
        )
        return resources

    def invalidate(self) -> None:
        """Clear all cached model resources (called on config refresh)."""
        with self._lock:
            self._cache.clear()
        logger.info("Model resource cache invalidated")

    async def warm_cache(self, *, config_reader: ConfigReader) -> None:
        """Pre-warm the cache for all langchain model configs."""
        configs: list[ChatModelConfig] = await config_reader.read_model_configs_async()
        warmed = 0
        for config in configs:
            if config.type == "langchain":
                try:
                    self.get_or_create(model_config=config)
                    warmed += 1
                except Exception:
                    logger.warning(
                        "Failed to pre-warm model '%s', will retry on first request",
                        config.name,
                        exc_info=True,
                    )
        logger.info(
            "Pre-warmed model resource cache: %d/%d langchain models ready",
            warmed,
            sum(1 for c in configs if c.type == "langchain"),
        )
