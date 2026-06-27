"""Adapter between OpenMontage BaseTool instances and MCP tool definitions."""

from __future__ import annotations

import json
from typing import Any

from mcp.types import Tool, TextContent

from tools.base_tool import BaseTool, ToolResult


def json_schema_to_mcp_parameters(schema: dict[str, Any]) -> dict[str, Any]:
    """Convert a JSON Schema object into MCP tool inputSchema.

    MCP expects a JSON Schema for the tool's arguments. OpenMontage tools
    already declare ``input_schema`` as JSON Schema, so this is mostly a
    pass-through with minor normalization.
    """
    if not schema:
        return {"type": "object", "properties": {}}

    # Ensure the root is an object schema with a properties dict.
    normalized: dict[str, Any] = dict(schema)
    normalized.setdefault("type", "object")
    normalized.setdefault("properties", {})
    normalized.setdefault("required", [])
    return normalized


def tool_to_mcp(tool: BaseTool) -> Tool:
    """Build an MCP Tool definition from a BaseTool instance."""
    info = tool.get_info()
    description = f"{tool.name} ({info.get('provider') or tool.provider})"
    if tool.best_for:
        description += "\nGood for: " + ", ".join(tool.best_for)
    if info.get("install_instructions"):
        description += f"\nSetup: {info['install_instructions']}"

    return Tool(
        name=tool.name,
        description=description[:1024],
        inputSchema=json_schema_to_mcp_parameters(tool.input_schema),
    )


def tool_result_to_mcp_contents(result: ToolResult) -> list[TextContent]:
    """Convert a ToolResult into MCP TextContent items."""
    payload: dict[str, Any] = {
        "success": result.success,
        "data": result.data,
        "cost_usd": result.cost_usd,
        "duration_seconds": result.duration_seconds,
    }
    if result.error:
        payload["error"] = result.error
    if result.artifacts:
        payload["artifacts"] = result.artifacts

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    return [TextContent(type="text", text=text)]


def validate_inputs(tool: BaseTool, inputs: dict[str, Any]) -> None:
    """Best-effort validation using the tool's declared input schema.

    Raises ValueError if the input does not match the tool schema.
    """
    import jsonschema

    schema = tool.input_schema or {"type": "object"}
    if schema:
        jsonschema.validate(instance=inputs, schema=schema)
