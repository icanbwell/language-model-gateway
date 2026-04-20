from __future__ import annotations

import logging
from typing import Sequence

from langchain_ai_skills_framework.loaders.skill_loader_protocol import (
    SkillLoaderProtocol,
)
from langchain_ai_skills_framework.models.plugin_mcp_config import PluginMcpServerEntry
from languagemodelcommon.configs.schemas.config_schema import AgentConfig

logger = logging.getLogger(__name__)


class SkillLoaderMcpAdapter:
    """Adapts SkillLoaderProtocol.get_plugin_mcp_configs() to AgentConfig list.

    This adapter bridges the skill framework's plugin MCP discovery
    (which refreshes on its own TTL) into the AgentConfig format that
    MCPToolProvider already understands.

    Registered as a singleton in the container, but get_mcp_server_configs()
    reads from the skill loader's TTL-cached snapshot — so configs stay fresh
    without worker restart.
    """

    def __init__(self, *, skill_loader: SkillLoaderProtocol) -> None:
        self._skill_loader = skill_loader

    def get_mcp_server_configs(self) -> Sequence[AgentConfig]:
        """Return AgentConfigs for HTTP-capable plugin MCP servers."""
        entries = self._skill_loader.get_plugin_mcp_configs()
        configs: list[AgentConfig] = []
        for entry in entries:
            agent_config = self._to_agent_config(entry)
            if agent_config is not None:
                configs.append(agent_config)
        return configs

    @staticmethod
    def _to_agent_config(entry: PluginMcpServerEntry) -> AgentConfig | None:
        """Convert a PluginMcpServerEntry to an AgentConfig.

        Returns None for stdio-only servers (no url) since the gateway
        cannot manage subprocess-based MCP servers.
        """
        if not entry.is_http:
            logger.debug(
                "Skipping stdio-only plugin MCP server '%s' from plugin '%s'",
                entry.server_key,
                entry.plugin_name,
            )
            return None

        return AgentConfig(
            name=entry.namespaced_key,
            url=entry.url,
            description=entry.description,
            display_name=entry.display_name,
            headers=entry.headers or None,
            auth=entry.auth,
        )