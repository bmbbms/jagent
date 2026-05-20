from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class NacosApiResult:
    code: int
    message: str
    data: Any


class NacosAiHttpClient:
    def __init__(
        self,
        base_url: str,
        *,
        namespace_id: str = "public",
        timeout: float = 5.0,
        username: str = "",
        password: str = "",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.namespace_id = namespace_id
        self.timeout = timeout
        self.username = username
        self.password = password

    def publish_agent_card(
        self,
        agent_card: Dict[str, Any],
        *,
        registration_type: str = "URL",
    ) -> NacosApiResult:
        payload = {
            "namespaceId": self.namespace_id,
            "agentCard": json.dumps(agent_card, ensure_ascii=False),
            "registrationType": registration_type,
        }
        return self._request_json("POST", "/nacos/v3/admin/ai/a2a", payload)

    def get_agent_card(
        self,
        agent_name: str,
        *,
        version: str | None = None,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {
            "namespaceId": self.namespace_id,
            "agentName": agent_name,
        }
        if version:
            payload["version"] = version
        try:
            return self._request_json("GET", "/nacos/v3/admin/ai/a2a", payload).data
        except RuntimeError:
            return None

    def list_agent_cards(
        self,
        *,
        agent_name: str = "",
        page_no: int = 1,
        page_size: int = 100,
        search: str = "blur",
    ) -> list[dict[str, Any]]:
        payload = {
            "namespaceId": self.namespace_id,
            "agentName": agent_name,
            "pageNo": str(page_no),
            "pageSize": str(page_size),
            "search": search,
        }
        result = self._request_json("GET", "/nacos/v3/admin/ai/a2a/list", payload)
        return self._extract_page_items(result.data)

    def delete_agent_card(self, agent_name: str, *, version: str | None = None) -> bool:
        payload: dict[str, Any] = {
            "namespaceId": self.namespace_id,
            "agentName": agent_name,
        }
        if version:
            payload["version"] = version
        result = self._request_json("DELETE", "/nacos/v3/admin/ai/a2a", payload)
        return bool(result.data)

    def list_skills(
        self,
        *,
        skill_name: str = "",
        search: str = "blur",
        page_no: int = 1,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        payload = {
            "namespaceId": self.namespace_id,
            "skillName": skill_name,
            "search": search,
            "pageNo": str(page_no),
            "pageSize": str(page_size),
        }
        result = self._request_json("GET", "/nacos/v3/admin/ai/skills/list", payload)
        return self._extract_page_items(result.data)

    def get_skill_detail(self, skill_name: str) -> dict[str, Any] | None:
        payload = {
            "namespaceId": self.namespace_id,
            "skillName": skill_name,
        }
        try:
            return self._request_json("GET", "/nacos/v3/admin/ai/skills", payload).data
        except RuntimeError:
            return None

    def download_skill_zip(self, skill_name: str, *, version: str | None = None) -> bytes:
        payload: dict[str, Any] = {
            "namespaceId": self.namespace_id,
            "skillName": skill_name,
        }
        if version:
            payload["version"] = version
        return self._request_bytes("GET", "/nacos/v3/admin/ai/skills/version/download", payload)

    def list_mcp_servers(
        self,
        *,
        mcp_name: str = "",
        search: str = "blur",
        page_no: int = 1,
        page_size: int = 100,
    ) -> list[dict[str, Any]]:
        payload = {
            "namespaceId": self.namespace_id,
            "mcpName": mcp_name,
            "search": search,
            "pageNo": str(page_no),
            "pageSize": str(page_size),
        }
        result = self._request_json("GET", "/nacos/v3/admin/ai/mcp/list", payload)
        return self._extract_page_items(result.data)

    def get_mcp_server_detail(
        self,
        *,
        mcp_name: str | None = None,
        mcp_id: str | None = None,
        version: str | None = None,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {"namespaceId": self.namespace_id}
        if mcp_id:
            payload["mcpId"] = mcp_id
        if mcp_name:
            payload["mcpName"] = mcp_name
        if version:
            payload["version"] = version
        try:
            return self._request_json("GET", "/nacos/v3/admin/ai/mcp", payload).data
        except RuntimeError:
            return None

    def _request_json(
        self,
        method: str,
        path: str,
        params: Dict[str, Any] | None = None,
    ) -> NacosApiResult:
        raw = self._request(method, path, params=params, expect_json=True)
        return NacosApiResult(
            code=int(raw.get("code", 0)),
            message=str(raw.get("message", "")),
            data=raw.get("data"),
        )

    def _request_bytes(
        self,
        method: str,
        path: str,
        params: Dict[str, Any] | None = None,
    ) -> bytes:
        return self._request(method, path, params=params, expect_json=False)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Dict[str, Any] | None = None,
        expect_json: bool,
    ) -> Any:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        params = dict(params or {})
        if method == "GET":
            if params:
                url = f"{url}?{urlencode(params)}"
            request = Request(url, method="GET")
        else:
            encoded = urlencode(params).encode("utf-8")
            request = Request(url, data=encoded, method=method)
            request.add_header(
                "Content-Type", "application/x-www-form-urlencoded; charset=utf-8"
            )

        request.add_header("Accept", "application/json")
        if self.username or self.password:
            token = base64.b64encode(
                f"{self.username}:{self.password}".encode("utf-8")
            ).decode("ascii")
            request.add_header("Authorization", f"Basic {token}")

        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except HTTPError as exc:
            body = exc.read()
            if expect_json:
                raise RuntimeError(
                    f"Nacos API error {exc.code}: {body.decode('utf-8', errors='ignore')}"
                ) from exc
            raise RuntimeError(f"Nacos API error {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(f"Nacos API unreachable: {exc.reason}") from exc

        if expect_json:
            if not body:
                return {}
            text = body.decode("utf-8")
            return json.loads(text)
        return body

    @staticmethod
    def _extract_page_items(data: Any) -> list[dict[str, Any]]:
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        if not isinstance(data, dict):
            return []
        for key in ("pageItems", "items", "list", "hosts"):
            items = data.get(key)
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]
        return []
