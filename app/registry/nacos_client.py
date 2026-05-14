from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class NacosInstance:
    service_name: str
    ip: str
    port: int
    healthy: bool = True
    weight: float = 1.0
    cluster_name: str = "DEFAULT"
    metadata: Optional[Dict[str, Any]] = None
    ephemeral: bool = True

    @property
    def endpoint(self) -> str:
        return f"http://{self.ip}:{self.port}"


class NacosHttpClient:
    def __init__(self, base_url: str, timeout: float = 5.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def register_instance(
        self,
        *,
        namespace_id: str,
        group_name: str,
        instance: NacosInstance,
    ) -> bool:
        payload = {
            "namespaceId": namespace_id,
            "groupName": group_name,
            "serviceName": instance.service_name,
            "ip": instance.ip,
            "port": str(instance.port),
            "clusterName": instance.cluster_name,
            "healthy": str(instance.healthy).lower(),
            "weight": str(instance.weight),
            "enabled": "true",
            "ephemeral": str(instance.ephemeral).lower(),
        }
        if instance.metadata:
            payload["metadata"] = json.dumps(instance.metadata, ensure_ascii=False)
        response = self._request("POST", "/nacos/v2/ns/instance", payload)
        return bool(response.get("data", False))

    def deregister_instance(
        self,
        *,
        namespace_id: str,
        group_name: str,
        instance: NacosInstance,
    ) -> bool:
        payload = {
            "namespaceId": namespace_id,
            "groupName": group_name,
            "serviceName": instance.service_name,
            "ip": instance.ip,
            "port": str(instance.port),
            "clusterName": instance.cluster_name,
            "healthy": str(instance.healthy).lower(),
            "weight": str(instance.weight),
            "enabled": "true",
            "ephemeral": str(instance.ephemeral).lower(),
        }
        if instance.metadata:
            payload["metadata"] = json.dumps(instance.metadata, ensure_ascii=False)
        response = self._request("DELETE", "/nacos/v2/ns/instance", payload)
        return bool(response.get("data", False))

    def list_instances(
        self,
        *,
        namespace_id: str,
        group_name: str,
        service_name: str,
        healthy_only: bool = True,
    ) -> List[Dict[str, Any]]:
        params = {
            "namespaceId": namespace_id,
            "groupName": group_name,
            "serviceName": service_name,
            "healthyOnly": str(healthy_only).lower(),
        }
        response = self._request("GET", "/nacos/v2/ns/instance/list", params)
        data = response.get("data") or {}
        if isinstance(data, dict):
            for key in ("hosts", "instances", "list"):
                items = data.get(key)
                if isinstance(items, list):
                    return items
        if isinstance(data, list):
            return data
        return []

    def _request(self, method: str, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        if method == "GET":
            url = f"{url}?{urlencode(params)}"
            request = Request(url, method="GET")
        else:
            encoded = urlencode(params).encode("utf-8")
            request = Request(url, data=encoded, method=method)
            request.add_header("Content-Type", "application/x-www-form-urlencoded")

        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Nacos API error {exc.code}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"Nacos API unreachable: {exc.reason}") from exc

        if not body:
            return {}
        return json.loads(body)
