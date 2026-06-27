#!/usr/bin/env python3
"""Test render_video via MCP server (async job)."""

import json
import subprocess
import sys
import time


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
            "clientInfo": {"name": "render-test", "version": "0.1.0"},
        },
    })
    notify(proc.stdin, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    edit_decisions = {
        "version": "1.0",
        "render_runtime": "remotion",
        "renderer_family": "explainer-data",
        "cuts": [
            {
                "id": "mcp-hook",
                "source": "",
                "type": "hero_title",
                "in_seconds": 0,
                "out_seconds": 3,
                "text": "MCP Server Test",
                "subtitle": "Rendered via OpenMontage MCP",
                "backgroundColor": "#0F172A",
            }
        ],
        "overlays": [],
        "captions": [],
        "audio": {},
    }

    render = send(proc.stdin, proc.stdout, {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "render_video",
            "arguments": {
                "edit_decisions": edit_decisions,
                "asset_manifest": {"assets": []},
                "output_path": "projects/demos/renders/mcp_render_test.mp4",
            },
        },
    })
    print("RENDER JOB:", json.dumps(render, indent=2))
    job_id = json.loads(render["result"]["content"][0]["text"]).get("job_id")

    for _ in range(60):
        time.sleep(2)
        status = send(proc.stdin, proc.stdout, {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "get_job_status", "arguments": {"job_id": job_id}},
        })
        payload = json.loads(status["result"]["content"][0]["text"])
        print("STATUS:", payload["status"])
        if payload["status"] in {"completed", "failed"}:
            print("FINAL:", json.dumps(payload, indent=2))
            break

    proc.stdin.close()
    proc.wait(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
