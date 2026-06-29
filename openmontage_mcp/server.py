"""OpenMontage MCP server.

Run with:
    python -m openmontage_mcp.server

Or from another directory:
    python -m openmontage_mcp.server --project-dir /path/to/OpenMontage-main
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# We must chdir to the project root before importing OpenMontage modules so
# that .env discovery and relative paths (pipeline/, styles/, etc.) resolve.
_project_dir: Path = Path.cwd()


def _set_project_dir(path: Path) -> None:
    global _project_dir
    _project_dir = path.resolve()
    os.chdir(_project_dir)


# Threshold below which a tool call is executed synchronously.
# Above this, the call is deferred to the job tracker.
_DEFER_THRESHOLD_SECONDS = 5.0


def _build_server() -> Server:
    from tools.tool_registry import registry
    from tools.base_tool import ToolResult
    from openmontage_mcp.tool_adapter import (
        make_error_response,
        make_success_response,
        tool_result_to_mcp_response,
        validate_inputs,
    )
    from openmontage_mcp.job_tracker import tracker
    from openmontage_mcp.project_manager import (
        create_project,
        get_project_status,
        resolve_project_path,
        read_project_artifact,
        write_checkpoint as _write_checkpoint,
    )

    registry.discover()

    server = Server("openmontage")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="list_capabilities",
                description=(
                    "List available OpenMontage tools, runtimes, setup offers, "
                    "and the full input schema for each tool. Use this before "
                    "calling run_tool so you can generate correct parameters. "
                    "Optional filter: {'category': 'video_generation'}."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": "Optional capability category to filter by (e.g. video_generation, image_generation, tts).",
                        },
                    },
                },
            ),
            Tool(
                name="create_project",
                description="Create a new OpenMontage project workspace.",
                inputSchema={
                    "type": "object",
                    "required": ["title", "pipeline"],
                    "properties": {
                        "title": {"type": "string", "description": "Human-readable project title"},
                        "pipeline": {"type": "string", "description": "Pipeline type, e.g. animated-explainer, cinematic"},
                        "brief": {"type": "string", "description": "Optional brief / user intent"},
                    },
                },
            ),
            Tool(
                name="get_project_status",
                description="Query completed stages, current stage, and pending human approvals for a project.",
                inputSchema={
                    "type": "object",
                    "required": ["project_id"],
                    "properties": {
                        "project_id": {"type": "string"},
                    },
                },
            ),
            Tool(
                name="run_tool",
                description=(
                    "Execute any OpenMontage tool by name. Parameter schema for "
                    "each tool is returned by list_capabilities. Long-running "
                    "calls are automatically deferred; short calls return "
                    "immediately. Always check the returned status field."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["name", "inputs"],
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Tool name as shown in list_capabilities",
                        },
                        "inputs": {
                            "type": "object",
                            "description": "Tool inputs matching the schema from list_capabilities",
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Optional project id; relative paths in inputs are resolved against projects/<project_id>/",
                        },
                        "_wait": {
                            "type": "boolean",
                            "default": False,
                            "description": "If true, block until completion even if the tool is long-running.",
                        },
                    },
                },
            ),
            Tool(
                name="render_video",
                description=(
                    "Render the final video for a project. Reads edit_decisions "
                    "and asset_manifest from the project workspace automatically."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["project_id"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "output_path": {"type": "string", "description": "Optional override for output MP4 path"},
                        "profile": {"type": "string"},
                        "audio_path": {"type": "string"},
                        "subtitle_path": {"type": "string"},
                    },
                },
            ),
            Tool(
                name="get_job_status",
                description="Poll the status of a deferred job returned by run_tool or render_video.",
                inputSchema={
                    "type": "object",
                    "required": ["job_id"],
                    "properties": {
                        "job_id": {"type": "string"},
                    },
                },
            ),
            Tool(
                name="list_jobs",
                description="List deferred jobs, optionally filtered by status or tool name.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "description": "Filter by pending|running|completed|failed|cancelled"},
                        "tool_name": {"type": "string"},
                    },
                },
            ),
            Tool(
                name="cancel_job",
                description="Cancel a running or pending deferred job.",
                inputSchema={
                    "type": "object",
                    "required": ["job_id"],
                    "properties": {
                        "job_id": {"type": "string"},
                    },
                },
            ),
            Tool(
                name="write_checkpoint",
                description="Write a pipeline stage checkpoint for a project.",
                inputSchema={
                    "type": "object",
                    "required": ["project_id", "stage", "status", "artifacts"],
                    "properties": {
                        "project_id": {"type": "string"},
                        "stage": {"type": "string"},
                        "status": {"type": "string", "enum": ["completed", "awaiting_human", "in_progress", "failed"]},
                        "artifacts": {"type": "object"},
                        "human_approval_required": {"type": "boolean", "default": False},
                        "human_approved": {"type": "boolean", "default": False},
                    },
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        arguments = arguments or {}

        if name == "list_capabilities":
            return _handle_list_capabilities(arguments)

        if name == "create_project":
            return _handle_create_project(arguments)

        if name == "get_project_status":
            return _handle_get_project_status(arguments)

        if name == "run_tool":
            return _handle_run_tool(arguments)

        if name == "render_video":
            return _handle_render_video(arguments)

        if name == "get_job_status":
            return _handle_get_job_status(arguments)

        if name == "list_jobs":
            return _handle_list_jobs(arguments)

        if name == "cancel_job":
            return _handle_cancel_job(arguments)

        if name == "write_checkpoint":
            return _handle_write_checkpoint(arguments)

        return make_error_response(f"unknown tool: {name}")

    def _handle_list_capabilities(arguments: dict[str, Any]) -> list[TextContent]:
        summary = registry.provider_menu_summary()
        category = arguments.get("category")

        tools = []
        for tool in registry._tools.values():
            try:
                info = tool.get_info()
                if category and info.get("capability") != category and tool.capability != category:
                    continue
                tools.append({
                    "name": tool.name,
                    "provider": info.get("provider") or tool.provider,
                    "capability": info.get("capability") or tool.capability,
                    "description": tool.best_for[0] if tool.best_for else tool.name,
                    "input_schema": tool.input_schema,
                    "install_instructions": info.get("install_instructions"),
                    "status": str(tool.get_status()),
                })
            except Exception:
                continue

        payload = {
            "summary": summary,
            "tools": tools,
            "note": "Use the input_schema from the tool you want when calling run_tool.",
        }
        return make_success_response(payload)

    def _handle_create_project(arguments: dict[str, Any]) -> list[TextContent]:
        result = create_project(
            title=arguments.get("title", ""),
            pipeline=arguments.get("pipeline", ""),
            brief=arguments.get("brief"),
        )
        return make_success_response(result)

    def _handle_get_project_status(arguments: dict[str, Any]) -> list[TextContent]:
        result = get_project_status(arguments.get("project_id", ""))
        return make_success_response(result)

    def _handle_run_tool(arguments: dict[str, Any]) -> list[TextContent]:
        tool_name = arguments.get("name", "")
        inputs = dict(arguments.get("inputs", {}))
        project_id = arguments.get("project_id")
        wait = arguments.get("_wait", False)

        tool = registry.get(tool_name)
        if tool is None:
            return make_error_response(f"tool {tool_name} not found", "E_RESOURCE_NOT_FOUND")

        for key in ("output_path", "image_path", "audio_path", "subtitle_path", "video_path"):
            if key in inputs:
                inputs[key] = resolve_project_path(project_id, inputs[key])

        try:
            validate_inputs(tool, inputs)
        except Exception as exc:
            return make_error_response(f"input validation failed: {exc}", "E_INVALID_INPUT")

        estimated = tool.estimate_runtime(inputs)

        def _execute() -> Any:
            return tool.execute(inputs)

        if wait or estimated < _DEFER_THRESHOLD_SECONDS:
            try:
                result = _execute()
            except Exception as exc:
                return make_error_response(f"tool execution failed: {exc}", "E_UNKNOWN")
            return make_success_response(tool_result_to_mcp_response(result))

        job_id = tracker.submit(_execute, tool_name=tool_name, estimated_seconds=estimated)
        return make_success_response({
            "status": "queued",
            "job_id": job_id,
            "tool_name": tool_name,
            "estimated_seconds": estimated,
            "next_action": "poll_get_job_status",
        })

    def _handle_render_video(arguments: dict[str, Any]) -> list[TextContent]:
        project_id = arguments.get("project_id", "")
        tool = registry.get("video_compose")
        if tool is None:
            return make_error_response("video_compose tool not found", "E_RESOURCE_NOT_FOUND")

        edit_decisions = arguments.get("edit_decisions") or read_project_artifact(project_id, "edit_decisions")
        asset_manifest = arguments.get("asset_manifest") or read_project_artifact(project_id, "asset_manifest")

        if not edit_decisions:
            return make_error_response(
                f"edit_decisions not found for project {project_id}. Run the edit stage first.",
                "E_RESOURCE_NOT_FOUND",
            )
        if not asset_manifest:
            return make_error_response(
                f"asset_manifest not found for project {project_id}. Run the assets stage first.",
                "E_RESOURCE_NOT_FOUND",
            )

        inputs: dict[str, Any] = {
            "operation": "render",
            "edit_decisions": edit_decisions,
            "asset_manifest": asset_manifest,
        }
        for key in ("output_path", "profile", "audio_path", "subtitle_path"):
            if key in arguments:
                inputs[key] = resolve_project_path(project_id, arguments[key])

        estimated = tool.estimate_runtime(inputs)
        job_id = tracker.submit(lambda: tool.execute(inputs), tool_name="video_compose", estimated_seconds=estimated)
        return make_success_response({
            "status": "queued",
            "job_id": job_id,
            "tool_name": "video_compose",
            "estimated_seconds": estimated,
            "next_action": "poll_get_job_status",
        })

    def _handle_get_job_status(arguments: dict[str, Any]) -> list[TextContent]:
        state = tracker.get(arguments.get("job_id", ""))
        if state is None:
            return make_error_response("job not found", "E_RESOURCE_NOT_FOUND")
        return make_success_response(state)

    def _handle_list_jobs(arguments: dict[str, Any]) -> list[TextContent]:
        jobs = tracker.list_jobs(
            status=arguments.get("status"),
            tool_name=arguments.get("tool_name"),
        )
        return make_success_response({"jobs": jobs})

    def _handle_cancel_job(arguments: dict[str, Any]) -> list[TextContent]:
        result = tracker.cancel(arguments.get("job_id", ""))
        return make_success_response(result)

    def _handle_write_checkpoint(arguments: dict[str, Any]) -> list[TextContent]:
        result = _write_checkpoint(
            project_id=arguments.get("project_id", ""),
            stage=arguments.get("stage", ""),
            status=arguments.get("status", ""),
            artifacts=arguments.get("artifacts", {}),
            human_approval_required=arguments.get("human_approval_required", False),
            human_approved=arguments.get("human_approved", False),
        )
        return make_success_response(result)

    return server


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenMontage MCP Server")
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Path to an OpenMontage project root (default: current directory)",
    )
    args = parser.parse_args()

    if not (args.project_dir / "config.yaml").exists():
        print(
            f"Warning: {args.project_dir} does not look like an OpenMontage project "
            "(config.yaml not found).",
            file=sys.stderr,
        )

    _set_project_dir(args.project_dir)
    server = _build_server()

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
