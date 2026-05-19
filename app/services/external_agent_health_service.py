from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.schemas import ExternalAgentHealthResponse
from app.services.external_capability_persistence_service import (
    ExternalCapabilityPersistenceService,
)


class ExternalAgentHealthService:
    def __init__(
        self,
        persistence_service: ExternalCapabilityPersistenceService,
    ) -> None:
        self._persistence_service = persistence_service

    def get_health(self, capability_id: str) -> ExternalAgentHealthResponse | None:
        item = self._persistence_service.get_item(capability_id)
        if item is None:
            return None
        return self._to_health_response(item)

    def check_health(self, capability_id: str) -> ExternalAgentHealthResponse | None:
        item = self._persistence_service.get_item(capability_id)
        if item is None:
            return None

        checked_at = datetime.utcnow()
        started_at = perf_counter()
        try:
            self._probe(item)
            latency_ms = max(0, int((perf_counter() - started_at) * 1000))
            updated = self._persistence_service.update_health(
                capability_id=capability_id,
                health_status="healthy",
                checked_at=checked_at,
                latency_ms=latency_ms,
            )
        except Exception as exc:  # noqa: BLE001
            latency_ms = max(0, int((perf_counter() - started_at) * 1000))
            updated = self._persistence_service.update_health(
                capability_id=capability_id,
                health_status="unhealthy",
                checked_at=checked_at,
                latency_ms=latency_ms,
                error=str(exc),
            )

        if updated is None:
            return None
        return self._to_health_response(updated)

    @staticmethod
    def _probe(item: Any) -> None:
        endpoint = str(item.endpoint or "").rstrip("/")
        if not endpoint:
            raise RuntimeError("External agent endpoint is missing")
        request = Request(f"{endpoint}/health", method="GET")
        try:
            with urlopen(request, timeout=5.0) as response:
                status_code = getattr(response, "status", 200)
                if status_code >= 400:
                    raise RuntimeError(f"Health probe failed with status {status_code}")
        except HTTPError as exc:
            raise RuntimeError(f"Health probe failed with status {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"Health probe unreachable: {exc.reason}") from exc

    @staticmethod
    def _to_health_response(item: Any) -> ExternalAgentHealthResponse:
        return ExternalAgentHealthResponse(
            capability_id=item.capability_id,
            health_status=item.health_status or "unknown",
            last_check_time=item.last_check_time.isoformat() if item.last_check_time else None,
            last_success_time=item.last_success_time.isoformat()
            if item.last_success_time
            else None,
            last_failure_time=item.last_failure_time.isoformat()
            if item.last_failure_time
            else None,
            last_error=item.last_error,
            consecutive_failures=int(item.consecutive_failures or 0),
            last_latency_ms=item.last_latency_ms,
        )
