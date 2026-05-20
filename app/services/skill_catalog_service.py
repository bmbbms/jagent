from __future__ import annotations

from typing import Iterable

from app.schemas import BizDomain, SkillDetailInfo, SkillInfo
from app.services.nacos_registry_service import NacosRegistryService
from app.services.skill_registry import SkillRegistry


class SkillCatalogService:
    def __init__(
        self,
        registry: SkillRegistry,
        nacos_registry_service: NacosRegistryService | None = None,
    ) -> None:
        self._registry = registry
        self._nacos_registry_service = nacos_registry_service

    def list_skills(
        self,
        biz_domain: BizDomain | None = None,
        *,
        allowed_tool: str | None = None,
        has_human_escalation: bool | None = None,
        skill_ids: Iterable[str] | None = None,
    ) -> list[SkillInfo]:
        skill_id_set = set(skill_ids) if skill_ids is not None else None
        local_items = self._registry.describe_skills(
            biz_domain,
            allowed_tool=allowed_tool,
            has_human_escalation=has_human_escalation,
            skill_ids=skill_id_set,
        )
        merged: dict[str, SkillInfo] = {item.skill_id: item for item in local_items}

        if self._nacos_registry_service is not None:
            for item in self._nacos_registry_service.list_remote_skill_infos(
                biz_domain=biz_domain,
                allowed_tool=allowed_tool,
                has_human_escalation=has_human_escalation,
                skill_ids=skill_id_set,
            ):
                merged.setdefault(item.skill_id, item)

        return sorted(merged.values(), key=lambda item: item.skill_id)

    def get_skill(self, skill_id: str) -> SkillDetailInfo | None:
        local_item = self._registry.describe_skill(skill_id)
        if local_item is not None:
            return local_item
        if self._nacos_registry_service is None:
            return None
        return self._nacos_registry_service.get_remote_skill_detail(skill_id)
