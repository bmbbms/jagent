from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from app.config import get_settings
from app.schemas import BizDomain


@dataclass(frozen=True)
class ToolSpec:
    tool_id: str
    tool_type: str
    provider: str = "internal"
    description: str = ""
    metadata: dict = field(default_factory=dict)


INTERNAL_TOOLS: Dict[BizDomain, List[ToolSpec]] = {
    BizDomain.merchant: [
        ToolSpec("merchant_profile_query", "internal"),
        ToolSpec("ticket_submit", "internal"),
    ],
    BizDomain.operations: [
        ToolSpec("merchant_profile_query", "internal"),
        ToolSpec("merchant_transaction_summary", "internal"),
        ToolSpec("merchant_risk_tag_query", "internal"),
        ToolSpec("quota_approval_submit", "internal"),
    ],
    BizDomain.data_support: [
        ToolSpec("direct_sales_metrics_query", "internal"),
        ToolSpec("compliance_report_export", "internal"),
    ],
}


def available_tools(biz_domain: BizDomain) -> List[str]:
    return [item.tool_id for item in list_tool_specs(biz_domain)]


def list_tool_specs(biz_domain: BizDomain) -> List[ToolSpec]:
    specs = list(INTERNAL_TOOLS.get(biz_domain, []))
    specs.extend(list_mcp_tool_specs())
    return specs


def get_tool_spec(tool_id: str) -> ToolSpec | None:
    for items in INTERNAL_TOOLS.values():
        for item in items:
            if item.tool_id == tool_id:
                return item
    for item in list_mcp_tool_specs():
        if item.tool_id == tool_id:
            return item
    return None


def list_mcp_tool_specs() -> List[ToolSpec]:
    return _load_mcp_tool_specs()


def _load_mcp_tool_specs() -> List[ToolSpec]:
    settings = get_settings()
    config_path = Path(settings.mcp_config_path)
    if not config_path.exists():
        example_path = Path("config/mcp.example.json")
        if not example_path.exists():
            return []
        config_path = example_path

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    specs: list[ToolSpec] = []
    for server in payload.get("servers", []):
        if not settings.mcp_enabled and config_path.name != "mcp.example.json":
            continue
        if not server.get("enabled", False) and config_path.name != "mcp.example.json":
            continue
        server_name = server["name"]
        specs.append(
            ToolSpec(
                tool_id=f"mcp_{server_name}",
                tool_type="mcp",
                provider=server_name,
                description=f"MCP server: {server_name}",
                metadata={
                    "enabled": bool(server.get("enabled", False)),
                    "transport": server.get("transport", "stdio"),
                    "command": server.get("command"),
                    "args": server.get("args", []),
                    "config_path": str(config_path),
                },
            )
        )
    return specs
