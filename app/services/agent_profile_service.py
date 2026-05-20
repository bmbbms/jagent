from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db.session import session_scope
from app.registry.nacos_ai_client import NacosAiHttpClient
from app.repositories.agent_profile_repository import AgentProfileRepository


class AgentProfileSyncService:
    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: sessionmaker[Session],
        repository: AgentProfileRepository,
        client: NacosAiHttpClient | None = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory
        self._repository = repository
        self._client = client or NacosAiHttpClient(
            settings.nacos_ai_server_address or settings.nacos_server_address,
            namespace_id=settings.nacos_ai_namespace or settings.nacos_namespace,
            username=settings.nacos_ai_username or settings.nacos_username,
            password=settings.nacos_ai_password or settings.nacos_password,
        )

    def sync_from_nacos(self) -> dict[str, Any]:
        sync_id = f"sync_{uuid4().hex[:24]}"
        namespace = self._settings.nacos_ai_namespace or self._settings.nacos_namespace
        started_at = datetime.utcnow()
        with session_scope(self._session_factory) as session:
            self._repository.create_sync_log(
                session,
                sync_id=sync_id,
                namespace=namespace,
                source="nacos",
                start_time=started_at,
            )

        pulled_count = 0
        upserted_count = 0
        failed_count = 0
        errors: list[str] = []

        try:
            cards = self._client.list_agent_cards(
                page_size=self._settings.nacos_ai_page_size
            )
            pulled_count = len(cards)
            for card in cards:
                try:
                    normalized = self.normalize_agent_card(card)
                    with session_scope(self._session_factory) as session:
                        self._repository.upsert_profile(
                            session,
                            profile=normalized["profile"],
                            skills=normalized["skills"],
                            mcps=normalized["mcps"],
                            workflows=normalized["workflows"],
                            sync_time=datetime.utcnow(),
                        )
                    upserted_count += 1
                except Exception as exc:
                    failed_count += 1
                    name = str(card.get("name") or "<unknown>")
                    errors.append(f"{name}: {exc!r}")
        except Exception as exc:
            failed_count = 1
            errors.append(f"pull_failed: {exc!r}")

        status = "success"
        if failed_count and upserted_count:
            status = "partial_success"
        elif failed_count:
            status = "failed"

        ended_at = datetime.utcnow()
        error_message = "; ".join(errors)[:2048] if errors else None
        with session_scope(self._session_factory) as session:
            self._repository.finish_sync_log(
                session,
                sync_id=sync_id,
                status=status,
                pulled_count=pulled_count,
                upserted_count=upserted_count,
                failed_count=failed_count,
                error_message=error_message,
                end_time=ended_at,
            )

        return {
            "sync_id": sync_id,
            "namespace": namespace,
            "source": "nacos",
            "status": status,
            "pulled_count": pulled_count,
            "upserted_count": upserted_count,
            "failed_count": failed_count,
            "error_message": error_message,
            "start_time": started_at.isoformat(),
            "end_time": ended_at.isoformat(),
        }

    def list_profiles(
        self,
        *,
        biz_domain: str | None = None,
        enabled: bool | None = None,
    ):
        with self._session_factory() as session:
            return self._repository.list_profiles(
                session,
                biz_domain=biz_domain,
                enabled=enabled,
            )

    def get_profile_bundle(self, agent_id: str) -> dict[str, Any] | None:
        with self._session_factory() as session:
            profile = self._repository.get_profile(session, agent_id)
            if profile is None:
                return None
            return {
                "profile": profile,
                "skills": self._repository.list_declared_skills(session, agent_id),
                "mcps": self._repository.list_declared_mcps(session, agent_id),
                "workflows": self._repository.list_declared_workflows(session, agent_id),
            }

    def list_sync_logs(self, *, limit: int = 20):
        with self._session_factory() as session:
            return self._repository.list_sync_logs(session, limit=limit)

    def normalize_agent_card(self, card: dict[str, Any]) -> dict[str, Any]:
        metadata = _coerce_dict(card.get("metadata"))
        source_agent_name = str(card.get("name") or "remote-agent").strip()
        biz_domain = _infer_biz_domain(source_agent_name, metadata)
        agent_id = str(metadata.get("capability_id") or "").strip()
        if not agent_id:
            agent_id = f"nacos.{biz_domain}.{_slugify(source_agent_name, separator='.')}"

        endpoint = _read_supported_interface_url(card) or card.get("url")
        transport = str(
            metadata.get("transport")
            or card.get("preferredTransport")
            or _read_supported_interface_transport(card)
            or "a2a"
        )
        tags = _dedupe(_coerce_list(metadata.get("tags")) + _coerce_list(card.get("tags")))
        version = str(
            card.get("version")
            or card.get("latestPublishedVersion")
            or metadata.get("version")
            or "v1"
        )
        normalized_card = {
            "agent_id": agent_id,
            "source_agent_name": source_agent_name,
            "declared_skill_count": len(card.get("skills") or []),
            "declared_mcp_count": len(_extract_declared_items(metadata, ["mcps", "declared_mcps"])),
            "declared_workflow_count": len(
                _extract_declared_items(metadata, ["workflows", "declared_workflows"])
            ),
        }
        return {
            "profile": {
                "agent_id": agent_id,
                "source_agent_name": source_agent_name,
                "agent_name": source_agent_name,
                "description": str(card.get("description") or ""),
                "endpoint": str(endpoint) if endpoint else None,
                "protocol": str(card.get("protocolVersion") or metadata.get("protocol") or "a2a"),
                "transport": transport,
                "version": version,
                "namespace": self._settings.nacos_ai_namespace
                or self._settings.nacos_namespace,
                "source": "nacos",
                "biz_domain": biz_domain,
                "tags": tags,
                "raw_card": card,
                "normalized_card": normalized_card,
                "health_status": "unknown",
                "governance_status": "healthy",
                "risk_level": str(metadata.get("risk_level") or "low"),
            },
            "skills": [_normalize_skill(item) for item in card.get("skills") or []],
            "mcps": [
                _normalize_mcp(item)
                for item in _extract_declared_items(metadata, ["mcps", "declared_mcps"])
            ],
            "workflows": [
                _normalize_workflow(item)
                for item in _extract_declared_items(
                    metadata,
                    ["workflows", "declared_workflows"],
                )
            ],
        }


def _normalize_skill(item: Any) -> dict[str, Any]:
    payload = item if isinstance(item, dict) else {"id": str(item), "name": str(item)}
    skill_id = str(payload.get("id") or payload.get("skill_id") or payload.get("name") or "").strip()
    skill_name = str(payload.get("name") or skill_id)
    return {
        "skill_id": skill_id or _slugify(skill_name),
        "skill_name": skill_name,
        "description": str(payload.get("description") or ""),
        "tags": _coerce_list(payload.get("tags")),
        "examples": _coerce_list(payload.get("examples")),
        "input_modes": _coerce_list(payload.get("inputModes") or payload.get("input_modes")),
        "output_modes": _coerce_list(payload.get("outputModes") or payload.get("output_modes")),
        "raw_payload": payload,
    }


def _normalize_mcp(item: Any) -> dict[str, Any]:
    payload = item if isinstance(item, dict) else {"id": str(item), "name": str(item)}
    mcp_id = str(payload.get("id") or payload.get("mcp_id") or payload.get("name") or "").strip()
    mcp_name = str(payload.get("name") or mcp_id)
    return {
        "mcp_id": mcp_id or _slugify(mcp_name),
        "mcp_name": mcp_name,
        "description": str(payload.get("description") or ""),
        "transport": payload.get("transport") or payload.get("transportType"),
        "endpoint": payload.get("endpoint") or payload.get("url"),
        "tags": _coerce_list(payload.get("tags")),
        "raw_payload": payload,
    }


def _normalize_workflow(item: Any) -> dict[str, Any]:
    payload = item if isinstance(item, dict) else {"id": str(item), "name": str(item)}
    workflow_id = str(
        payload.get("id") or payload.get("workflow_id") or payload.get("name") or ""
    ).strip()
    workflow_name = str(payload.get("name") or workflow_id)
    return {
        "workflow_id": workflow_id or _slugify(workflow_name),
        "workflow_name": workflow_name,
        "description": str(payload.get("description") or ""),
        "steps": _coerce_list(payload.get("steps")),
        "tags": _coerce_list(payload.get("tags")),
        "raw_payload": payload,
    }


def _extract_declared_items(metadata: dict[str, Any], keys: list[str]) -> list[Any]:
    for key in keys:
        value = metadata.get(key)
        if value is None:
            continue
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                return [item.strip() for item in value.split(",") if item.strip()]
            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                return [parsed]
        if isinstance(value, dict):
            return [value]
    return []


def _infer_biz_domain(source_agent_name: str, metadata: dict[str, Any]) -> str:
    for value in [metadata.get("biz_domain"), metadata.get("bizDomain"), metadata.get("domain")]:
        matched = _match_domain(value)
        if matched:
            return matched
    for value in _coerce_list(metadata.get("tags")) + re.split(r"[-_.\s]+", source_agent_name):
        matched = _match_domain(value)
        if matched:
            return matched
    return "merchant"


def _match_domain(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    aliases = {
        "merchant": "merchant",
        "operations": "operations",
        "operation": "operations",
        "ops": "operations",
        "data": "data_support",
        "data_support": "data_support",
        "data-support": "data_support",
        "partner": "partner",
    }
    return aliases.get(normalized)


def _read_supported_interface_url(card: dict[str, Any]) -> str | None:
    for item in card.get("supportedInterfaces") or []:
        if not isinstance(item, dict):
            continue
        value = item.get("url")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _read_supported_interface_transport(card: dict[str, Any]) -> str | None:
    for item in card.get("supportedInterfaces") or []:
        if not isinstance(item, dict):
            continue
        value = item.get("transport")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


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


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _slugify(value: str, *, separator: str = "_") -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", separator, value.strip().lower())
    normalized = re.sub(rf"{re.escape(separator)}+", separator, normalized)
    return normalized.strip(separator) or "remote_agent"
