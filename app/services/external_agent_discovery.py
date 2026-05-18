from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from app.registry.base import CapabilityMetadata
from app.schemas import ExternalAgentAddRequest


class ExternalAgentDiscoveryService:
    def discover(self, request: ExternalAgentAddRequest) -> CapabilityMetadata:
        normalized_url = request.agent_url.strip().rstrip("/")
        if not normalized_url:
            raise ValueError("agent_url is required")

        parsed_input = urlparse(normalized_url)
        if not parsed_input.scheme or not parsed_input.netloc:
            raise ValueError("agent_url must be a valid absolute URL")

        input_base_url = f"{parsed_input.scheme}://{parsed_input.netloc}"
        card = self._fetch_agent_card(input_base_url)
        transport = self._detect_transport(request, normalized_url, card)
        target_url = self._resolve_target_url(
            input_url=normalized_url,
            card=card,
            transport=transport,
        )
        endpoint, service_path = self._split_endpoint_and_path(
            target_url=target_url,
            transport=transport,
            preferred_service_path=request.service_path,
        )
        capability_name = (
            request.capability_name
            or self._read_card_value(card, "name")
            or parsed_input.netloc
        )
        capability_id = request.capability_id or self._build_capability_id(
            transport=transport,
            capability_name=capability_name,
        )
        description = (
            request.description
            or self._read_card_value(card, "description")
            or f"External {transport.upper()} agent at {target_url}"
        )
        version = request.version or self._read_card_value(card, "version") or "v1"
        skills = request.skills or self._extract_skill_ids(card)
        tags = self._merge_tags(request.tags, transport)
        extras = {
            **request.extras,
            "source": "generic_add",
            "normalized_agent_url": normalized_url,
        }
        if card:
            extras["agent_card_discovered"] = "true"
        if self._read_card_value(card, "url"):
            extras["agent_card_url"] = str(self._read_card_value(card, "url"))
        if self._read_card_value(card, "protocolVersion"):
            extras["protocol_version"] = str(self._read_card_value(card, "protocolVersion"))
        return CapabilityMetadata(
            capability_id=capability_id,
            capability_name=capability_name,
            biz_domain=request.biz_domain,
            description=description,
            priority=request.priority,
            triggers=request.triggers,
            skills=skills,
            version=version,
            risk_level=request.risk_level,
            requires_approval=request.requires_approval,
            tags=tags,
            transport=transport,
            endpoint=endpoint,
            service_path=service_path,
            extras=extras,
        )

    def _fetch_agent_card(self, base_url: str) -> Optional[Dict[str, Any]]:
        for path in ("/.well-known/agent-card.json", "/.well-known/agent.json"):
            url = f"{base_url}{path}"
            try:
                return self._get_json(url)
            except HTTPError as exc:
                if exc.code != 404:
                    continue
            except (URLError, ValueError):
                continue
        return None

    def _get_json(self, url: str) -> Dict[str, Any]:
        request = Request(url, method="GET")
        request.add_header("Accept", "application/json")
        with urlopen(request, timeout=8.0) as response:
            return json.loads(response.read().decode("utf-8"))

    def _detect_transport(
        self,
        request: ExternalAgentAddRequest,
        normalized_url: str,
        card: Optional[Dict[str, Any]],
    ) -> str:
        if request.transport:
            return request.transport
        if card:
            return "a2a"
        if normalized_url.endswith("/a2a"):
            return "a2a"
        return "http"

    def _resolve_target_url(
        self,
        *,
        input_url: str,
        card: Optional[Dict[str, Any]],
        transport: str,
    ) -> str:
        parsed_input = urlparse(input_url)
        if parsed_input.path and parsed_input.path != "/":
            return input_url
        card_url = self._read_card_value(card, "url")
        if isinstance(card_url, str) and card_url.strip():
            return card_url.strip().rstrip("/")
        default_path = "/a2a" if transport == "a2a" else "/api/chat"
        return f"{input_url}{default_path}"

    def _split_endpoint_and_path(
        self,
        *,
        target_url: str,
        transport: str,
        preferred_service_path: Optional[str],
    ) -> tuple[str, str]:
        parsed_target = urlparse(target_url)
        endpoint = f"{parsed_target.scheme}://{parsed_target.netloc}"
        if preferred_service_path:
            service_path = preferred_service_path
        elif parsed_target.path and parsed_target.path != "/":
            service_path = parsed_target.path
        else:
            service_path = "/a2a" if transport == "a2a" else "/api/chat"
        return endpoint, service_path

    @staticmethod
    def _read_card_value(card: Optional[Dict[str, Any]], key: str) -> Any:
        if not card:
            return None
        return card.get(key)

    @staticmethod
    def _extract_skill_ids(card: Optional[Dict[str, Any]]) -> list[str]:
        if not card:
            return []
        skills = card.get("skills") or []
        extracted: list[str] = []
        for item in skills:
            if not isinstance(item, dict):
                continue
            skill_id = item.get("id")
            if isinstance(skill_id, str) and skill_id:
                extracted.append(skill_id)
        return extracted

    @staticmethod
    def _merge_tags(tags: list[str], transport: str) -> list[str]:
        merged = list(tags)
        for item in ("external", transport):
            if item not in merged:
                merged.append(item)
        return merged

    @staticmethod
    def _build_capability_id(*, transport: str, capability_name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", ".", capability_name.lower()).strip(".")
        slug = re.sub(r"\.+", ".", slug) or "agent"
        return f"external.{transport}.{slug}"
