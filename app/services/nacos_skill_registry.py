from __future__ import annotations

import json
from typing import Any, Iterable

from app.config import Settings
from app.registry.nacos_ai_client import NacosAiHttpClient
from app.schemas import BizDomain, SkillDetailInfo, SkillInfo
from app.services.skill_registry import SkillRuntimeSpec


class NacosSkillRegistry:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = NacosAiHttpClient(
            settings.nacos_ai_server_address or settings.nacos_server_address,
            namespace_id=settings.nacos_ai_namespace or settings.nacos_namespace,
            username=settings.nacos_ai_username or settings.nacos_username,
            password=settings.nacos_ai_password or settings.nacos_password,
        )

    def describe_skills(
        self,
        biz_domain: BizDomain | None = None,
        *,
        allowed_tool: str | None = None,
        has_human_escalation: bool | None = None,
        skill_ids: Iterable[str] | None = None,
    ) -> list[SkillInfo]:
        items = [
            self._map_skill_detail_payload(payload)
            for payload in self._safe_list_skills()
        ]
        if biz_domain is not None:
            items = [item for item in items if item.biz_domain == biz_domain]
        if skill_ids is not None:
            skill_id_set = set(skill_ids)
            items = [item for item in items if item.skill_id in skill_id_set]
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

    def describe_skill(self, skill_id: str) -> SkillDetailInfo | None:
        payload = self._client.get_skill_detail(skill_id)
        if payload:
            return self._map_skill_detail_payload(payload)
        for item in self._safe_list_skills(skill_name=skill_id, page_size=10):
            if self._skill_payload_name(item) == skill_id:
                return self._map_skill_detail_payload(item)
        return None

    def load_runtime_skills(self, skill_ids: Iterable[str]) -> list[SkillRuntimeSpec]:
        items: list[SkillRuntimeSpec] = []
        for skill_id in skill_ids:
            detail = self.describe_skill(skill_id)
            if detail is None:
                continue
            items.append(
                SkillRuntimeSpec(
                    skill_id=detail.skill_id,
                    biz_domain=detail.biz_domain,
                    name=detail.name,
                    path=detail.path,
                    purpose=detail.purpose,
                    when_to_use=list(detail.when_to_use),
                    required_inputs=list(detail.required_inputs),
                    steps=list(detail.steps),
                    output_fields=list(detail.output_fields),
                    allowed_tools=list(detail.allowed_tools),
                    human_escalation=list(detail.human_escalation),
                    content=json.dumps(detail.model_dump(mode="json"), ensure_ascii=False),
                )
            )
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

    @staticmethod
    def _infer_biz_domain(payload: dict[str, Any], metadata: dict[str, Any]) -> BizDomain:
        candidates = [
            metadata.get("biz_domain"),
            metadata.get("bizDomain"),
            metadata.get("domain"),
            payload.get("biz_domain"),
            payload.get("bizDomain"),
            payload.get("domain"),
        ]
        for value in candidates:
            domain = NacosSkillRegistry._match_biz_domain(value)
            if domain is not None:
                return domain

        tags = NacosSkillRegistry._coerce_list(payload.get("tags")) + NacosSkillRegistry._coerce_list(
            metadata.get("tags")
        )
        for value in tags:
            domain = NacosSkillRegistry._match_biz_domain(value)
            if domain is not None:
                return domain

        skill_name = NacosSkillRegistry._skill_payload_name(payload)
        for value in skill_name.split(".") + skill_name.split("-") + skill_name.split("_"):
            domain = NacosSkillRegistry._match_biz_domain(value)
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
