from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.tools import ToolSpec, get_tool_spec


@dataclass(frozen=True)
class MCPInvokeResult:
    tool_id: str
    provider: str
    status: str
    output_summary: str
    payload: dict[str, Any]


class MCPService:
    def invoke_tool(self, tool_id: str, request_context: dict[str, Any]) -> MCPInvokeResult:
        spec = get_tool_spec(tool_id)
        if spec is None or spec.tool_type != "mcp":
            raise ValueError(f"Unsupported MCP tool: {tool_id}")

        # Phase 1 minimal MCP bridge:
        # use configured server metadata as executable descriptor and return a
        # standardized invocation result. Real protocol handshakes and tool
        # discovery can be introduced in the next step without changing callers.
        transport = spec.metadata.get("transport", "stdio")
        output_summary = (
            f"MCP tool {tool_id} invoked via {transport}, "
            f"provider={spec.provider}."
        )
        return MCPInvokeResult(
            tool_id=tool_id,
            provider=spec.provider,
            status="success",
            output_summary=output_summary,
            payload={
                "request_context": request_context,
                "transport": transport,
                "command": spec.metadata.get("command"),
                "args": spec.metadata.get("args", []),
            },
        )
