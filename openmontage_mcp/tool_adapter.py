"""Adapter between OpenMontage BaseTool instances and MCP tool definitions."""

from __future__ import annotations

import json
import traceback
from typing import Any

from mcp.types import Tool, TextContent

from tools.base_tool import BaseTool, ToolResult


class MCPErrorCode:
    AUTH = "E_AUTH"
    TIMEOUT = "E_TIMEOUT"
    INVALID_INPUT = "E_INVALID_INPUT"
    RATE_LIMIT = "E_RATE_LIMIT"
    RESOURCE_NOT_FOUND = "E_RESOURCE_NOT_FOUND"
    PROJECT_ARTIFACT_MISSING = "E_PROJECT_ARTIFACT_MISSING"
    QUEUE_FULL = "E_QUEUE_FULL"
    PROVIDER_ERROR = "E_PROVIDER_ERROR"
    UNKNOWN = "E_UNKNOWN"


def classify_error(error_text: str | None) -> str:
    """Map a raw error string to a structured error code."""
    if not error_text:
        return MCPErrorCode.UNKNOWN
    err = error_text.lower()
    if any(k in err for k in ("api key", "apikey", "not set", "unauthorized", "authentication", "auth")):
        return MCPErrorCode.AUTH
    if any(k in err for k in ("timed out", "timeout", "operation timed out")):
        return MCPErrorCode.TIMEOUT
    if any(k in err for k in ("rate limit", "rate_limit", "too many requests")):
        return MCPErrorCode.RATE_LIMIT
    if any(k in err for k in ("not found", "404", "resource not found", "invalid url")):
        return MCPErrorCode.RESOURCE_NOT_FOUND
    if any(k in err for k in ("artifact", "edit_decisions", "asset_manifest")):
        return MCPErrorCode.PROJECT_ARTIFACT_MISSING
    if any(k in err for k in ("queue full", "concurrent job limit", "too many concurrent")):
        return MCPErrorCode.QUEUE_FULL
    if any(k in err for k in ("validation failed", "invalid", "required", "schema")):
        return MCPErrorCode.INVALID_INPUT
    if any(k in err for k in ("http 5", "service unavailable", "internal server", "provider error")):
        return MCPErrorCode.PROVIDER_ERROR
    return MCPErrorCode.UNKNOWN


def json_schema_to_mcp_parameters(schema: dict[str, Any]) -> dict[str, Any]:
    """Convert a JSON Schema object into MCP tool inputSchema.

    MCP expects a JSON Schema for the tool's arguments. OpenMontage tools
    already declare ``input_schema`` as JSON Schema, so this is mostly a
    pass-through with minor normalization.
    """
    if not schema:
        return {"type": "object", "properties": {}}

    normalized: dict[str, Any] = dict(schema)
    normalized.setdefault("type", "object")
    normalized.setdefault("properties", {})
    normalized.setdefault("required", [])
    return normalized


def tool_to_capability_schema(tool: BaseTool) -> dict[str, Any]:
    """Build a capability entry for list_capabilities.

    Includes the tool's full input schema so the LLM can generate correct
    parameters before calling run_tool.
    """
    info = tool.get_info()
    return {
        "name": tool.name,
        "provider": info.get("provider") or tool.provider,
        "capability": info.get("capability") or tool.capability,
        "description": tool.best_for[0] if tool.best_for else tool.name,
        "input_schema": tool.input_schema,
        "install_instructions": info.get("install_instructions"),
        "status": str(tool.get_status()),
        "estimated_runtime_seconds": getattr(tool, "estimate_runtime", lambda _: 10)({}),
    }


def validate_inputs(tool: BaseTool, inputs: dict[str, Any]) -> None:
    """Best-effort validation using the tool's declared input schema."""
    import jsonschema

    schema = tool.input_schema or {"type": "object"}
    if schema:
        jsonschema.validate(instance=inputs, schema=schema)


def tool_result_to_mcp_response(result: ToolResult) -> dict[str, Any]:
    """Convert a ToolResult into a normalized MCP response dict.

    Both synchronous and asynchronous results use the same shape so the
    LLM does not have to branch on whether the tool was deferred.
    """
    if not result.success:
        return {
            "status": "error",
            "code": classify_error(result.error),
            "message": result.error or "Tool execution failed",
            "data": result.data,
            "cost_usd": result.cost_usd,
            "duration_seconds": result.duration_seconds,
        }

    payload: dict[str, Any] = {
        "status": "completed",
        "data": result.data,
        "cost_usd": result.cost_usd,
        "duration_seconds": result.duration_seconds,
    }
    if result.artifacts:
        payload["artifacts"] = result.artifacts
    if result.model:
        payload["model"] = result.model
    return payload


def make_error_response(message: str, code: str = MCPErrorCode.UNKNOWN) -> list[TextContent]:
    return [TextContent(
        type="text",
        text=json.dumps({
            "status": "error",
            "code": code,
            "message": message,
        }, ensure_ascii=False, indent=2),
    )]


def make_success_response(payload: dict[str, Any]) -> list[TextContent]:
    return [TextContent(
        type="text",
        text=json.dumps(payload, ensure_ascii=False, indent=2),
    )]
