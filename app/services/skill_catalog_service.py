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
        if self._nacos_registry_service is not None:
            return self._nacos_registry_service.list_remote_skill_infos(
                biz_domain=biz_domain,
                allowed_tool=allowed_tool,
                has_human_escalation=has_human_escalation,
                skill_ids=skill_id_set,
            )
        return self._registry.describe_skills(
            biz_domain,
            allowed_tool=allowed_tool,
            has_human_escalation=has_human_escalation,
            skill_ids=skill_id_set,
        )

    def get_skill(self, skill_id: str) -> SkillDetailInfo | None:
        if self._nacos_registry_service is None:
            return self._registry.describe_skill(skill_id)
        return self._nacos_registry_service.get_remote_skill_detail(skill_id)
