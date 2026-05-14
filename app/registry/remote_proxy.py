from __future__ import annotations

import json
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.agents.base import CapabilityAgent
from app.registry.base import CapabilityMetadata
from app.schemas import ChatRequest, ChatResponse


class RemoteCapabilityProxy(CapabilityAgent):
    def __init__(self, metadata: CapabilityMetadata) -> None:
        self.definition = _proxy_definition(metadata)
        self._metadata = metadata

    def run(self, request: ChatRequest) -> ChatResponse:
        base_url = self._remote_base_url()
        endpoint = self._metadata.service_path or "/api/chat"
        payload = request.model_dump(mode="json")
        response = self._post_json(f"{base_url}{endpoint}", payload)
        return ChatResponse.model_validate(response)

    def _remote_base_url(self) -> str:
        if self._metadata.endpoint:
            return self._metadata.endpoint.rstrip("/")
        if self._metadata.service_host and self._metadata.service_port:
            return f"http://{self._metadata.service_host}:{self._metadata.service_port}"
        raise RuntimeError("Remote capability metadata does not contain an endpoint")

    def _post_json(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
        )
        request.add_header("Content-Type", "application/json")
        try:
            with urlopen(request, timeout=5.0) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Remote capability error {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"Remote capability unreachable: {exc.reason}") from exc
        return json.loads(body)


def _proxy_definition(metadata: CapabilityMetadata):
    from app.agents.base import CapabilityDefinition

    return CapabilityDefinition(
        capability_id=metadata.capability_id,
        name=metadata.capability_name,
        biz_domain=metadata.biz_domain,
        description=metadata.description,
        triggers=metadata.triggers,
        skills=metadata.skills,
        priority=metadata.priority,
    )
