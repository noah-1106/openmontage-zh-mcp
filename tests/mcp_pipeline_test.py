#!/usr/bin/env python3
"""Test pipeline stage checkpoint via MCP server."""

import json
import subprocess
import sys


def send(stdin, stdout, msg: dict) -> dict:
    payload = json.dumps(msg) + "\n"
    stdin.write(payload.encode())
    stdin.flush()
    line = stdout.readline().decode()
    return json.loads(line)


def notify(stdin, msg: dict) -> None:
    payload = json.dumps(msg) + "\n"
    stdin.write(payload.encode())
    stdin.flush()


def main() -> int:
    proc = subprocess.Popen(
        [sys.executable, "-m", "openmontage_mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        cwd="/Users/tannoah/Project/openmontage/OpenMontage-main",
    )

    send(proc.stdin, proc.stdout, {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pipeline-test", "version": "0.1.0"},
        },
    })
    notify(proc.stdin, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    research_brief = {
        "version": "1.0",
        "topic": "MCP Pipeline Smoke Test",
        "research_date": "2026-06-28",
        "landscape": {
            "existing_content": [
                {"title": "OpenMontage README", "source": "github", "angle": "overview", "what_it_covers": "project intro"},
                {"title": "OpenMontage Docs", "source": "github", "angle": "docs", "what_it_covers": "usage guide"},
                {"title": "OpenMontage Examples", "source": "github", "angle": "examples", "what_it_covers": "demo videos"},
            ],
            "saturated_angles": ["generic AI video"],
            "underserved_gaps": ["agent-driven orchestration"],
        },
        "data_points": [
            {"claim": "OpenMontage has 12 pipelines", "source_url": "https://github.com/calesthio/OpenMontage", "credibility": "primary_source", "usable_as": "stat_card"},
            {"claim": "OpenMontage has 52 tools", "source_url": "https://github.com/calesthio/OpenMontage", "credibility": "primary_source", "usable_as": "stat_card"},
            {"claim": "OpenMontage is AGPL licensed", "source_url": "https://github.com/calesthio/OpenMontage", "credibility": "primary_source", "usable_as": "closing_punch"},
        ],
        "audience_insights": {
            "common_questions": ["How do I use OpenMontage?", "Can I plug it into my agent?", "What pipelines are available?"],
            "misconceptions": [],
            "knowledge_level": "technical, familiar with AI agents",
        },
        "angles_discovered": [
            {"name": "Agent plugin", "hook": "Turn any agent into a video studio", "type": "narrative", "why_now": "MCP is becoming standard"},
            {"name": "Open source video production", "hook": "Full pipeline in code", "type": "evergreen", "why_now": "AI video tools are fragmented"},
            {"name": "Cost transparency", "hook": "Know the cost before rendering", "type": "data_driven", "why_now": "API costs are unpredictable"},
        ],
        "sources": [
            {"url": "https://github.com/calesthio/OpenMontage", "title": "OpenMontage Repository", "used_for": "overview"},
            {"url": "https://github.com/calesthio/OpenMontage/blob/main/README.md", "title": "README", "used_for": "capabilities"},
            {"url": "https://github.com/calesthio/OpenMontage/blob/main/AGENT_GUIDE.md", "title": "Agent Guide", "used_for": "orchestration"},
            {"url": "https://github.com/calesthio/OpenMontage/blob/main/config.yaml", "title": "Config", "used_for": "settings"},
            {"url": "https://github.com/calesthio/OpenMontage/blob/main/Makefile", "title": "Makefile", "used_for": "setup"},
        ],
    }

    write = send(proc.stdin, proc.stdout, {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "run_pipeline_stage",
            "arguments": {
                "project_id": "mcp-pipeline-smoke",
                "pipeline_type": "animated-explainer",
                "stage": "research",
                "status": "completed",
                "artifacts": {"research_brief": research_brief},
            },
        },
    })
    print("WRITE:", json.dumps(write, indent=2))

    status = send(proc.stdin, proc.stdout, {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "get_pipeline_status",
            "arguments": {
                "project_id": "mcp-pipeline-smoke",
                "pipeline_type": "animated-explainer",
            },
        },
    })
    print("STATUS:", json.dumps(status, indent=2))

    proc.stdin.close()
    proc.wait(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
