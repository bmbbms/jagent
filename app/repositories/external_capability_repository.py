from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.db.models import ExternalCapabilityRegistryModel
from app.registry.base import CapabilityMetadata
from app.schemas import BizDomain


class ExternalCapabilityRepository:
    def list_items(self, session: Session) -> List[ExternalCapabilityRegistryModel]:
        return (
            session.query(ExternalCapabilityRegistryModel)
            .filter(ExternalCapabilityRegistryModel.enabled.is_(True))
            .order_by(
                ExternalCapabilityRegistryModel.priority.asc(),
                ExternalCapabilityRegistryModel.capability_id.asc(),
            )
            .all()
        )

    def list_enabled(self, session: Session) -> List[CapabilityMetadata]:
        items = self.list_items(session)
        return [self._to_metadata(item) for item in items]

    def get_item(
        self,
        session: Session,
        capability_id: str,
    ) -> ExternalCapabilityRegistryModel | None:
        item = session.get(ExternalCapabilityRegistryModel, capability_id)
        if item is None or not item.enabled:
            return None
        return item

    def upsert(self, session: Session, metadata: CapabilityMetadata) -> CapabilityMetadata:
        item = session.get(ExternalCapabilityRegistryModel, metadata.capability_id)
        if item is None:
            item = ExternalCapabilityRegistryModel(capability_id=metadata.capability_id)
            session.add(item)

        item.capability_name = metadata.capability_name
        item.biz_domain = metadata.biz_domain.value
        item.description = metadata.description
        item.priority = metadata.priority
        item.triggers = metadata.triggers
        item.skills = metadata.skills
        item.version = metadata.version
        item.risk_level = metadata.risk_level
        item.requires_approval = metadata.requires_approval
        item.tags = metadata.tags
        item.transport = metadata.transport
        item.endpoint = metadata.endpoint
        item.service_name = metadata.service_name
        item.service_host = metadata.service_host
        item.service_port = metadata.service_port
        item.service_path = metadata.service_path
        item.extras = metadata.extras
        if not item.health_status:
            item.health_status = "unknown"
        if item.consecutive_failures is None:
            item.consecutive_failures = 0
        item.enabled = True
        session.flush()
        return self._to_metadata(item)

    def disable(self, session: Session, capability_id: str) -> bool:
        item = session.get(ExternalCapabilityRegistryModel, capability_id)
        if item is None:
            return False
        item.enabled = False
        session.flush()
        return True

    def update_health(
        self,
        session: Session,
        *,
        capability_id: str,
        health_status: str,
        checked_at: datetime,
        latency_ms: int | None = None,
        error: str | None = None,
    ) -> ExternalCapabilityRegistryModel | None:
        item = session.get(ExternalCapabilityRegistryModel, capability_id)
        if item is None:
            return None

        item.health_status = health_status
        item.last_check_time = checked_at
        item.last_latency_ms = latency_ms

        if health_status == "healthy":
            item.last_success_time = checked_at
            item.last_error = None
            item.consecutive_failures = 0
        else:
            item.last_failure_time = checked_at
            item.last_error = (error or "")[:1024] or None
            item.consecutive_failures = int(item.consecutive_failures or 0) + 1

        session.flush()
        return item

    @staticmethod
    def _to_metadata(item: ExternalCapabilityRegistryModel) -> CapabilityMetadata:
        return CapabilityMetadata(
            capability_id=item.capability_id,
            capability_name=item.capability_name,
            biz_domain=BizDomain(item.biz_domain),
            description=item.description,
            priority=item.priority,
            triggers=list(item.triggers or []),
            skills=list(item.skills or []),
            version=item.version,
            risk_level=item.risk_level,
            requires_approval=item.requires_approval,
            tags=list(item.tags or []),
            transport=item.transport,
            endpoint=item.endpoint,
            service_name=item.service_name,
            service_host=item.service_host,
            service_port=item.service_port,
            service_path=item.service_path,
            extras=dict(item.extras or {}),
            source=str((item.extras or {}).get("source") or "manual_remote"),
        )
