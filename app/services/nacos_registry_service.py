from __future__ import annotations

from app.config import Settings
from app.registry.nacos_ai_client import NacosAiHttpClient
from app.services.skill_registry import SkillRegistry
from app.tools import list_mcp_tool_specs


class NacosRegistryService:
    def __init__(self, settings: Settings, skill_registry: SkillRegistry) -> None:
        self._settings = settings
        self._skill_registry = skill_registry
        self._client = NacosAiHttpClient(
            settings.nacos_ai_server_address or settings.nacos_server_address,
            namespace_id=settings.nacos_ai_namespace or settings.nacos_namespace,
            username=settings.nacos_ai_username or settings.nacos_username,
            password=settings.nacos_ai_password or settings.nacos_password,
        )

    def get_overview(self) -> dict[str, object]:
        skill_count = len(self._skill_registry.describe_skills())
        mcp_count = len(list_mcp_tool_specs())
        agent_count = 0
        if self._settings.nacos_ai_enabled:
            try:
                agent_count = len(
                    self._client.list_agent_cards(page_size=self._settings.nacos_ai_page_size)
                )
            except Exception:
                agent_count = 0
            try:
                skill_count = len(
                    self._client.list_skills(page_size=self._settings.nacos_ai_page_size)
                )
            except Exception:
                skill_count = len(self._skill_registry.describe_skills())
            try:
                mcp_count = len(
                    self._client.list_mcp_servers(page_size=self._settings.nacos_ai_page_size)
                )
            except Exception:
                mcp_count = len(list_mcp_tool_specs())
        return {
            "backend": "nacos" if self._settings.nacos_ai_enabled else "local",
            "enabled": self._settings.nacos_ai_enabled,
            "server_address": self._settings.nacos_ai_server_address
            or self._settings.nacos_server_address,
            "namespace": self._settings.nacos_ai_namespace or self._settings.nacos_namespace,
            "agent_count": agent_count,
            "skill_count": skill_count,
            "mcp_count": mcp_count,
        }

    def list_agent_cards(self):
        return self._client.list_agent_cards(page_size=self._settings.nacos_ai_page_size)

    def list_skills(self):
        return self._client.list_skills(page_size=self._settings.nacos_ai_page_size)

    def list_mcp_servers(self):
        return self._client.list_mcp_servers(page_size=self._settings.nacos_ai_page_size)
