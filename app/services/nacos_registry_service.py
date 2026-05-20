from __future__ import annotations

import json
import re
from typing import Any

from app.config import Settings
from app.registry.nacos_ai_client import NacosAiHttpClient
from app.schemas import BizDomain, MCPToolInfo, SkillDetailInfo, SkillInfo
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

    def list_remote_skill_infos(
        self,
        *,
        biz_domain: BizDomain | None = None,
        allowed_tool: str | None = None,
        has_human_escalation: bool | None = None,
        skill_ids: set[str] | None = None,
    ) -> list[SkillInfo]:
        items = [
            self._map_skill_detail_payload(payload)
            for payload in self._safe_list_skills()
        ]
        if biz_domain is not None:
            items = [item for item in items if item.biz_domain == biz_domain]
        if skill_ids is not None:
            items = [item for item in items if item.skill_id in skill_ids]
        if allowed_tool:
            items = [item for item in items if allowed_tool in item.allowed_tools]
        if has_human_escalation is not None:
            items = [
                item
                for item in items
                if bool(item.human_escalation) == has_human_escalation
            ]
        items.sort(key=lambda item: item.skill_id)
        return [
            SkillInfo(
                skill_id=item.skill_id,
                biz_domain=item.biz_domain,
                name=item.name,
                path=item.path,
                purpose=item.purpose,
                when_to_use=item.when_to_use,
            )
            for item in items
        ]

    def get_remote_skill_detail(self, skill_id: str) -> SkillDetailInfo | None:
        if not self._settings.nacos_ai_enabled:
            return None
        payload = self._client.get_skill_detail(skill_id)
        if payload:
            return self._map_skill_detail_payload(payload)
        for item in self._safe_list_skills(skill_name=skill_id, page_size=10):
            if self._skill_payload_name(item) == skill_id:
                return self._map_skill_detail_payload(item)
        return None

    def list_remote_mcp_tools(
        self,
        usage_map: dict[str, dict[str, object]] | None = None,
    ) -> list[MCPToolInfo]:
        usage_map = usage_map or {}
        items = [
            self._map_mcp_tool_payload(payload, usage_map=usage_map)
            for payload in self._safe_list_mcp_servers()
        ]
        items.sort(key=lambda item: item.tool_id)
        return items

    def _safe_list_skills(
        self,
        *,
        skill_name: str = "",
        page_size: int | None = None,
    ) -> list[dict[str, Any]]:
        if not self._settings.nacos_ai_enabled:
            return []
        try:
            return self._client.list_skills(
                skill_name=skill_name,
                page_size=page_size or self._settings.nacos_ai_page_size,
            )
        except Exception:
            return []

    def _safe_list_mcp_servers(self) -> list[dict[str, Any]]:
        if not self._settings.nacos_ai_enabled:
            return []
        try:
            return self._client.list_mcp_servers(
                page_size=self._settings.nacos_ai_page_size
            )
        except Exception:
            return []

    def _map_skill_detail_payload(self, payload: dict[str, Any]) -> SkillDetailInfo:
        metadata = self._coerce_dict(payload.get("metadata"))
        skill_id = self._skill_payload_name(payload)
        version = str(payload.get("version") or payload.get("latestPublishedVersion") or "").strip()
        path = f"nacos://skills/{skill_id}"
        if version:
            path = f"{path}:{version}"

        when_to_use = self._coerce_list(
            metadata.get("when_to_use")
            or metadata.get("whenToUse")
            or payload.get("examples")
            or payload.get("tags")
        )
        return SkillDetailInfo(
            skill_id=skill_id,
            biz_domain=self._infer_biz_domain(payload, metadata),
            name=str(payload.get("displayName") or payload.get("name") or skill_id),
            path=path,
            purpose=str(payload.get("description") or metadata.get("purpose") or ""),
            when_to_use=when_to_use,
            required_inputs=self._coerce_list(
                metadata.get("required_inputs")
                or metadata.get("requiredInputs")
                or payload.get("inputModes")
            ),
            steps=self._coerce_list(metadata.get("steps")),
            output_fields=self._coerce_list(
                metadata.get("output_fields")
                or metadata.get("outputFields")
                or payload.get("outputModes")
            ),
            allowed_tools=self._coerce_list(
                metadata.get("allowed_tools")
                or metadata.get("allowedTools")
                or metadata.get("tools")
            ),
            human_escalation=self._coerce_list(
                metadata.get("human_escalation")
                or metadata.get("humanEscalation")
            ),
        )

    def _map_mcp_tool_payload(
        self,
        payload: dict[str, Any],
        *,
        usage_map: dict[str, dict[str, object]],
    ) -> MCPToolInfo:
        metadata = self._coerce_dict(payload.get("metadata"))
        server_name = self._mcp_payload_name(payload)
        tool_id = f"nacos_mcp_{_slugify(server_name)}"
        usage = usage_map.get(tool_id, {})
        transport = str(
            payload.get("transport")
            or payload.get("transportType")
            or metadata.get("transport")
            or metadata.get("protocol")
            or "http"
        )
        command = (
            payload.get("url")
            or payload.get("endpoint")
            or metadata.get("url")
            or metadata.get("endpoint")
            or payload.get("command")
            or metadata.get("command")
        )
        version = str(payload.get("version") or payload.get("latestPublishedVersion") or "").strip()
        config_path = f"nacos://mcp/{server_name}"
        if version:
            config_path = f"{config_path}:{version}"

        return MCPToolInfo(
            tool_id=tool_id,
            provider=str(payload.get("provider") or server_name or "nacos"),
            description=str(payload.get("description") or metadata.get("description") or ""),
            transport=transport,
            command=str(command) if command else None,
            args=self._coerce_list(payload.get("args") or metadata.get("args")),
            enabled=self._coerce_enabled(payload, metadata),
            config_path=config_path,
            call_count=int(usage.get("call_count", 0)),
            success_count=int(usage.get("success_count", 0)),
            failure_count=int(usage.get("failure_count", 0)),
            last_status=self._coerce_optional_str(usage.get("last_status")),
            last_called_at=self._coerce_optional_str(usage.get("last_called_at")),
            average_duration_ms=self._coerce_optional_int(usage.get("average_duration_ms")),
        )

    def _infer_biz_domain(
        self,
        payload: dict[str, Any],
        metadata: dict[str, Any],
    ) -> BizDomain:
        candidates = [
            metadata.get("biz_domain"),
            metadata.get("bizDomain"),
            metadata.get("domain"),
            payload.get("biz_domain"),
            payload.get("bizDomain"),
            payload.get("domain"),
        ]
        for value in candidates:
            domain = self._match_biz_domain(value)
            if domain is not None:
                return domain

        tags = self._coerce_list(payload.get("tags")) + self._coerce_list(metadata.get("tags"))
        for value in tags:
            domain = self._match_biz_domain(value)
            if domain is not None:
                return domain

        skill_name = self._skill_payload_name(payload)
        for value in skill_name.split(".") + skill_name.split("-") + skill_name.split("_"):
            domain = self._match_biz_domain(value)
            if domain is not None:
                return domain
        return BizDomain.merchant

    @staticmethod
    def _skill_payload_name(payload: dict[str, Any]) -> str:
        return str(
            payload.get("skillName")
            or payload.get("name")
            or payload.get("id")
            or ""
        ).strip()

    @staticmethod
    def _mcp_payload_name(payload: dict[str, Any]) -> str:
        return str(
            payload.get("mcpName")
            or payload.get("name")
            or payload.get("id")
            or "remote_mcp"
        ).strip()

    @staticmethod
    def _coerce_dict(value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return {}
            if isinstance(parsed, dict):
                return parsed
        return {}

    @staticmethod
    def _coerce_list(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, tuple):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return [stripped]
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
            if isinstance(parsed, str) and parsed.strip():
                return [parsed.strip()]
            return []
        return [str(value).strip()] if str(value).strip() else []

    @staticmethod
    def _coerce_enabled(payload: dict[str, Any], metadata: dict[str, Any]) -> bool:
        status = str(payload.get("status") or metadata.get("status") or "").strip().lower()
        if status in {"disabled", "inactive", "down", "offline"}:
            return False
        enabled_value = payload.get("enabled", metadata.get("enabled"))
        if isinstance(enabled_value, bool):
            return enabled_value
        if isinstance(enabled_value, str):
            if enabled_value.lower() in {"false", "0", "no"}:
                return False
            if enabled_value.lower() in {"true", "1", "yes"}:
                return True
        return True

    @staticmethod
    def _coerce_optional_str(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _coerce_optional_int(value: Any) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _match_biz_domain(value: Any) -> BizDomain | None:
        if value is None:
            return None
        normalized = str(value).strip().lower()
        alias_map = {
            "merchant": BizDomain.merchant,
            "operations": BizDomain.operations,
            "operation": BizDomain.operations,
            "ops": BizDomain.operations,
            "data_support": BizDomain.data_support,
            "data-support": BizDomain.data_support,
            "data": BizDomain.data_support,
            "partner": BizDomain.partner,
        }
        return alias_map.get(normalized)


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    return normalized.strip("_") or "remote"
