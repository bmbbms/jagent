from __future__ import annotations

from sqlalchemy.orm import Session, sessionmaker

from app.db.session import session_scope
from app.registry.base import CapabilityMetadata
from app.registry.manual_remote_registry import ManualRemoteCapabilityRegistry
from app.repositories.external_capability_repository import ExternalCapabilityRepository


class ExternalCapabilityPersistenceService:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        repository: ExternalCapabilityRepository,
        registry: ManualRemoteCapabilityRegistry,
    ) -> None:
        self._session_factory = session_factory
        self._repository = repository
        self._registry = registry

    def save(self, metadata: CapabilityMetadata) -> CapabilityMetadata:
        with session_scope(self._session_factory) as session:
            return self._repository.upsert(session, metadata)

    def delete(self, capability_id: str) -> bool:
        with session_scope(self._session_factory) as session:
            return self._repository.disable(session, capability_id)

    def restore_into_registry(self) -> int:
        with self._session_factory() as session:
            items = self._repository.list_enabled(session)
        for item in items:
            self._registry.register_remote(item)
        return len(items)
