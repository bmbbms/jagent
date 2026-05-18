from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List
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
        payload = request.model_dump(mode="python")
        payload["metadata"] = self._sanitize_metadata(payload.get("metadata") or {})
        url = f"{base_url}{endpoint}"
        if self._metadata.transport in {"a2a", "a2a_jsonrpc"}:
            return self._run_a2a(url, request, payload["metadata"])
        response = self._post_json(url, payload)
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

    def _run_a2a(
        self,
        url: str,
        request: ChatRequest,
        metadata: Dict[str, Any],
    ) -> ChatResponse:
        payload = {
            "jsonrpc": "2.0",
            "id": f"jagent-{uuid.uuid4().hex[:16]}",
            "method": "message/stream",
            "params": {
                "message": {
                    "role": "user",
                    "messageId": str(uuid.uuid4()),
                    "parts": [{"kind": "text", "text": request.message}],
                },
                "configuration": {
                    "acceptedOutputModes": ["text"],
                    "historyLength": 20,
                    "blocking": False,
                },
                "metadata": metadata,
            },
        }
        transport_request = Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
        )
        transport_request.add_header("Content-Type", "application/json")
        transport_request.add_header("Accept", "text/event-stream")

        texts: List[str] = []
        try:
            with urlopen(transport_request, timeout=120.0) as response:
                current_data_lines: List[str] = []
                for raw_line in response:
                    line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
                    if line.startswith("data:"):
                        current_data_lines.append(line.split(":", 1)[1].strip())
                        continue
                    if line:
                        continue
                    if not current_data_lines:
                        continue
                    event_payload = json.loads("\n".join(current_data_lines))
                    current_data_lines = []
                    result = event_payload.get("result") or {}
                    texts.extend(self._extract_a2a_texts(result))
                    if texts and result.get("kind") == "message":
                        break
                    if result.get("final") is True and texts:
                        break
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Remote capability error {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"Remote capability unreachable: {exc.reason}") from exc

        content = "\n".join(item.strip() for item in texts if item.strip()).strip()
        if not content:
            raise RuntimeError("A2A remote capability returned no message content")
        return ChatResponse(
            domain=request.biz_domain,
            capability_id=self._metadata.capability_id,
            capability_name=self._metadata.capability_name,
            summary=content,
            next_action=content,
            selected_skills=list(self._metadata.skills),
            selected_tools=[],
            references=[url],
            requires_approval=self._metadata.requires_approval,
            workflow=None,
            audit_tags=[
                f"transport:{self._metadata.transport}",
                "external_agent",
            ],
        )

    @staticmethod
    def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
        sanitized: Dict[str, Any] = {}
        for key, value in metadata.items():
            if key.startswith("_"):
                continue
            if callable(value):
                continue
            sanitized[key] = value
        return sanitized

    @staticmethod
    def _extract_a2a_texts(node: Any) -> List[str]:
        texts: List[str] = []

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                text = value.get("text")
                if isinstance(text, str):
                    texts.append(text)
                for child in value.values():
                    visit(child)
                return
            if isinstance(value, list):
                for child in value:
                    visit(child)

        visit(node)
        return texts


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
